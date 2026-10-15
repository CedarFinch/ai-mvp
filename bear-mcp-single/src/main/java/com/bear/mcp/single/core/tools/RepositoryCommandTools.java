package com.bear.mcp.single.core.tools;

import com.bear.mcp.single.core.repository.RepositoryCommandService;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/** Bear MCP 源码只读检索 Tool。 */
@Component
public class RepositoryCommandTools {
    private final RepositoryCommandService commandService;

    public RepositoryCommandTools(RepositoryCommandService commandService) {
        this.commandService = commandService;
    }

    @Tool(
            name = "run_repository_command",
            description = "在 Bear MCP 白名单源码仓库中执行受限只读命令。命令工作目录自动设置为仓库根目录，文件路径使用仓库内相对路径。支持 rg、sed、nl、head、tail、wc；禁止修改文件、持续监听和任意 Shell。"
    )
    public Map<String, Object> runRepositoryCommand(
            @ToolParam(
                    description = "仓库标识，当前支持 yanque-admin。所有环境均使用此固定标识，不要传本机或服务器绝对路径。",
                    required = true
            )
            String repository,
            @ToolParam(description = "只读命令：rg、sed、nl、head、tail 或 wc", required = true)
            String command,
            @ToolParam(
                    description = """
                            按命令行顺序传入参数，每个参数是一个独立数组元素，不要包含命令本身。路径必须是仓库内相对路径，可用 . 表示仓库根目录，禁止绝对路径和 ..。支持格式：rg 支持 -n、-F、-i、-l、--files、-A、-B、-C、-m、-g、--glob，例如 [\"-n\", \"-i\", \"UserService\", \"src\"] 或 [\"--files\", \"-g\", \"*.java\"]；sed 仅支持只读输出，例如 [\"-n\", \"10,30p\", \"src/App.java\"]；nl 例如 [\"-ba\", \"src/App.java\"]；head/tail 例如 [\"-n\", \"50\", \"README.md\"]，tail 不支持 -f；wc 支持 -l、-w、-c，例如 [\"-l\", \"README.md\"]。禁止 Shell 引号、管道、重定向、命令替换、&&、||、分号以及 sh、bash 等 Shell 命令。
                            """,
                    required = true
            )
            List<String> args) {
        return commandService.execute(repository, command, args);
    }
}
