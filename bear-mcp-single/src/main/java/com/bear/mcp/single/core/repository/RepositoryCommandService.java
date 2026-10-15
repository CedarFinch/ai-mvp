package com.bear.mcp.single.core.repository;

import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** 在白名单仓库中执行受限的只读源码检索命令。 */
@Service
public class RepositoryCommandService {
    private static final Set<String> ALLOWED_COMMANDS = Set.of("rg", "sed", "nl", "head", "tail", "wc");
    private static final Set<String> RG_FLAGS = Set.of(
            "-n", "--line-number", "-F", "--fixed-strings", "-i", "--ignore-case",
            "-l", "--files-with-matches", "--files"
    );
    private static final Set<String> RG_VALUE_FLAGS = Set.of("-A", "-B", "-C", "-m", "-g", "--glob");
    private static final Pattern COMPACT_RG_NUMBER_FLAG = Pattern.compile("-[ABCMm](\\d+)");
    private static final Pattern SED_PRINT_EXPRESSION = Pattern.compile("(\\d+)(?:,(\\d+))?p");
    private static final Pattern PATH_TRAVERSAL = Pattern.compile("(^|[/\\\\])\\.\\.([/\\\\]|$)");
    private static final Pattern SENSITIVE_FILE = Pattern.compile(
            "(?i)(^|[/\\\\])(?:\\.env(?:\\..*)?|id_(?:rsa|dsa|ecdsa|ed25519)|[^/\\\\]+\\.(?:pem|key|p12|pfx|jks))$"
    );

    private final RepositoryCommandProperties properties;

    public RepositoryCommandService(RepositoryCommandProperties properties) {
        this.properties = properties;
    }

    public Map<String, Object> execute(String repository, String command, List<String> args) {
        long startedAt = System.nanoTime();
        String normalizedCommand = normalizeCommand(command);
        Path repositoryRoot = resolveRepository(repository);
        List<String> normalizedArgs = args == null ? List.of() : List.copyOf(args);
        validateArguments(normalizedCommand, normalizedArgs, repositoryRoot);

        List<String> commandLine = new ArrayList<>(normalizedArgs.size() + 1);
        commandLine.add(normalizedCommand);
        commandLine.addAll(normalizedArgs);

        ProcessBuilder builder = new ProcessBuilder(commandLine);
        builder.directory(repositoryRoot.toFile());
        builder.redirectErrorStream(true);

        Process process;
        try {
            process = builder.start();
        } catch (IOException e) {
            throw new IllegalStateException("源码检索命令启动失败，请确认容器内已安装 " + normalizedCommand, e);
        }

        ExecutorService readerExecutor = Executors.newSingleThreadExecutor(runnable -> {
            Thread thread = new Thread(runnable, "repository-command-output-reader");
            thread.setDaemon(true);
            return thread;
        });
        Future<OutputCapture> outputFuture = readerExecutor.submit(
                () -> readOutput(process.getInputStream(), maxOutputBytes())
        );

        boolean timedOut = false;
        int exitCode = -1;
        OutputCapture capture;
        try {
            boolean finished = process.waitFor(timeoutSeconds(), TimeUnit.SECONDS);
            if (!finished) {
                timedOut = true;
                process.destroyForcibly();
                process.waitFor(2, TimeUnit.SECONDS);
            } else {
                exitCode = process.exitValue();
            }
            capture = outputFuture.get(2, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            process.destroyForcibly();
            throw new IllegalStateException("源码检索命令被中断", e);
        } catch (Exception e) {
            process.destroyForcibly();
            throw new IllegalStateException("读取源码检索结果失败", e);
        } finally {
            readerExecutor.shutdownNow();
        }

        LimitedText limitedText = limitLines(capture.text(), maxOutputLines());
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("repository", repository);
        result.put("command", normalizedCommand);
        result.put("exitCode", exitCode);
        result.put("timedOut", timedOut);
        result.put("truncated", capture.truncated() || limitedText.truncated());
        result.put("durationMs", Duration.ofNanos(System.nanoTime() - startedAt).toMillis());
        result.put("output", limitedText.text());
        return result;
    }

    private String normalizeCommand(String command) {
        if (!StringUtils.hasText(command)) {
            throw new IllegalArgumentException("command 不能为空");
        }
        String value = command.trim();
        if (!ALLOWED_COMMANDS.contains(value)) {
            throw new IllegalArgumentException("不允许执行该命令，可用命令: " + ALLOWED_COMMANDS);
        }
        return value;
    }

    private Path resolveRepository(String repository) {
        if (!StringUtils.hasText(repository) || !repository.matches("[a-zA-Z0-9][a-zA-Z0-9_-]*")) {
            throw new IllegalArgumentException("repository 名称不合法");
        }
        String directory = properties.getRepositories() == null
                ? null
                : properties.getRepositories().get(repository);
        if (!StringUtils.hasText(directory)) {
            throw new IllegalArgumentException("仓库不在白名单中: " + repository);
        }
        if (isAbsolutePath(directory) || PATH_TRAVERSAL.matcher(directory).find()) {
            throw new IllegalStateException("仓库目录映射不合法: " + repository);
        }
        if (!StringUtils.hasText(properties.getRoot())) {
            throw new IllegalStateException("源码仓库根目录未配置");
        }
        try {
            Path baseRoot = Path.of(properties.getRoot()).toRealPath();
            Path repositoryRoot = baseRoot.resolve(directory).toRealPath();
            if (!repositoryRoot.startsWith(baseRoot) || !Files.isDirectory(repositoryRoot)) {
                throw new IllegalArgumentException("仓库目录不合法: " + repository);
            }
            return repositoryRoot;
        } catch (IOException e) {
            throw new IllegalStateException("仓库目录不存在或不可读: " + repository, e);
        }
    }

    private void validateArguments(String command, List<String> args, Path repositoryRoot) {
        if (args.size() > 32) {
            throw new IllegalArgumentException("命令参数不能超过 32 个");
        }
        for (String arg : args) {
            if (arg == null || arg.length() > 1000 || arg.indexOf('\0') >= 0) {
                throw new IllegalArgumentException("命令参数不合法");
            }
            if (isAbsolutePath(arg) || PATH_TRAVERSAL.matcher(arg).find()) {
                throw new IllegalArgumentException("禁止使用绝对路径或 ../ 路径");
            }
        }
        switch (command) {
            case "rg" -> validateRg(args, repositoryRoot);
            case "sed" -> validateSed(args, repositoryRoot);
            case "nl" -> validateNl(args, repositoryRoot);
            case "head", "tail" -> validateHeadOrTail(args, repositoryRoot);
            case "wc" -> validateWc(args, repositoryRoot);
            default -> throw new IllegalArgumentException("不允许执行该命令");
        }
    }

    private void validateRg(List<String> args, Path repositoryRoot) {
        boolean filesMode = args.contains("--files");
        boolean patternSeen = false;
        for (int index = 0; index < args.size(); index++) {
            String arg = args.get(index);
            if (RG_FLAGS.contains(arg)) {
                continue;
            }
            if (RG_VALUE_FLAGS.contains(arg)) {
                if (++index >= args.size()) {
                    throw new IllegalArgumentException(arg + " 缺少参数值");
                }
                validateRgOptionValue(arg, args.get(index));
                continue;
            }
            Matcher compactMatcher = COMPACT_RG_NUMBER_FLAG.matcher(arg);
            if (compactMatcher.matches()) {
                validateBoundedNumber(compactMatcher.group(1), 1000, "rg 数量参数");
                continue;
            }
            if (arg.startsWith("-")) {
                throw new IllegalArgumentException("rg 参数不在白名单中: " + arg);
            }
            if (!filesMode && !patternSeen) {
                patternSeen = true;
            } else {
                validatePath(arg, repositoryRoot, true);
            }
        }
        if (!filesMode && !patternSeen) {
            throw new IllegalArgumentException("rg 缺少搜索内容");
        }
    }

    private void validateRgOptionValue(String option, String value) {
        if (Set.of("-A", "-B", "-C", "-m").contains(option)) {
            validateBoundedNumber(value, 1000, "rg 数量参数");
            return;
        }
        if (!StringUtils.hasText(value) || PATH_TRAVERSAL.matcher(value).find()
                || SENSITIVE_FILE.matcher(value.replace("*", "x")).find()) {
            throw new IllegalArgumentException("rg glob 参数不合法");
        }
    }

    private void validateSed(List<String> args, Path repositoryRoot) {
        if (args.size() != 3 || !"-n".equals(args.get(0))) {
            throw new IllegalArgumentException("sed 只允许格式: sed -n '开始行,结束行p' 文件");
        }
        Matcher matcher = SED_PRINT_EXPRESSION.matcher(args.get(1));
        if (!matcher.matches()) {
            throw new IllegalArgumentException("sed 只允许读取指定行范围，不允许 -i 或其他脚本");
        }
        int start = Integer.parseInt(matcher.group(1));
        int end = matcher.group(2) == null ? start : Integer.parseInt(matcher.group(2));
        if (start < 1 || end < start || end - start > 500) {
            throw new IllegalArgumentException("sed 单次最多读取连续 501 行");
        }
        validatePath(args.get(2), repositoryRoot, false);
    }

    private void validateNl(List<String> args, Path repositoryRoot) {
        String path;
        if (args.size() == 1) {
            path = args.get(0);
        } else if (args.size() == 2 && "-ba".equals(args.get(0))) {
            path = args.get(1);
        } else {
            throw new IllegalArgumentException("nl 只允许格式: nl [-ba] 文件");
        }
        validatePath(path, repositoryRoot, false);
    }

    private void validateHeadOrTail(List<String> args, Path repositoryRoot) {
        String path;
        if (args.size() == 1) {
            path = args.get(0);
        } else if (args.size() == 3 && "-n".equals(args.get(0))) {
            validateBoundedNumber(args.get(1), 1000, "读取行数");
            path = args.get(2);
        } else {
            throw new IllegalArgumentException("head/tail 只允许格式: command [-n 行数] 文件，禁止 tail -f");
        }
        validatePath(path, repositoryRoot, false);
    }

    private void validateWc(List<String> args, Path repositoryRoot) {
        String path;
        if (args.size() == 1) {
            path = args.get(0);
        } else if (args.size() == 2 && Set.of("-l", "-w", "-c").contains(args.get(0))) {
            path = args.get(1);
        } else {
            throw new IllegalArgumentException("wc 只允许 -l、-w 或 -c 参数和一个文件");
        }
        validatePath(path, repositoryRoot, false);
    }

    private void validatePath(String pathText, Path repositoryRoot, boolean allowDirectory) {
        if (!StringUtils.hasText(pathText) || SENSITIVE_FILE.matcher(pathText).find()) {
            throw new IllegalArgumentException("禁止读取敏感文件或空路径");
        }
        Path candidate = repositoryRoot.resolve(pathText).normalize();
        if (!candidate.startsWith(repositoryRoot)) {
            throw new IllegalArgumentException("路径超出仓库目录");
        }
        try {
            Path realPath = candidate.toRealPath();
            if (!realPath.startsWith(repositoryRoot)
                    || (!allowDirectory && !Files.isRegularFile(realPath))) {
                throw new IllegalArgumentException("路径不是仓库内允许读取的文件");
            }
        } catch (IOException e) {
            throw new IllegalArgumentException("源码路径不存在或不可读: " + pathText, e);
        }
    }

    private void validateBoundedNumber(String value, int max, String name) {
        try {
            int number = Integer.parseInt(value);
            if (number < 0 || number > max) {
                throw new IllegalArgumentException(name + "必须在 0-" + max + " 之间");
            }
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException(name + "必须是整数", e);
        }
    }

    private boolean isAbsolutePath(String value) {
        try {
            return Path.of(value).isAbsolute();
        } catch (RuntimeException e) {
            throw new IllegalArgumentException("命令参数不是合法路径文本", e);
        }
    }

    private OutputCapture readOutput(InputStream inputStream, int maxBytes) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream(Math.min(maxBytes, 8192));
        byte[] buffer = new byte[4096];
        int stored = 0;
        boolean truncated = false;
        int read;
        while ((read = inputStream.read(buffer)) != -1) {
            int writable = Math.min(read, Math.max(0, maxBytes - stored));
            if (writable > 0) {
                output.write(buffer, 0, writable);
                stored += writable;
            }
            if (writable < read) {
                truncated = true;
            }
        }
        return new OutputCapture(output.toString(StandardCharsets.UTF_8), truncated);
    }

    private LimitedText limitLines(String text, int maxLines) {
        String[] lines = text.split("\\R", -1);
        if (lines.length <= maxLines) {
            return new LimitedText(text, false);
        }
        return new LimitedText(String.join("\n", Arrays.asList(lines).subList(0, maxLines)), true);
    }

    private int timeoutSeconds() {
        return Math.max(1, Math.min(properties.getTimeoutSeconds(), 30));
    }

    private int maxOutputLines() {
        return Math.max(1, Math.min(properties.getMaxOutputLines(), 2000));
    }

    private int maxOutputBytes() {
        return Math.max(1024, Math.min(properties.getMaxOutputBytes(), 200_000));
    }

    private record OutputCapture(String text, boolean truncated) {
    }

    private record LimitedText(String text, boolean truncated) {
    }
}
