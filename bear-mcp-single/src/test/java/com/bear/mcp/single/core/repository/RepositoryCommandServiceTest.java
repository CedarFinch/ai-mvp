package com.bear.mcp.single.core.repository;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RepositoryCommandServiceTest {
    @TempDir
    Path tempDir;

    private RepositoryCommandService service;

    @BeforeEach
    void setUp() throws Exception {
        Path repository = Files.createDirectories(tempDir.resolve("local-checkout/src/main/java"));
        Files.writeString(repository.resolve("Sample.java"), "class Sample {\n}\n");

        RepositoryCommandProperties properties = new RepositoryCommandProperties();
        properties.setRoot(tempDir.toString());
        properties.setRepositories(Map.of("yanque-admin", "local-checkout"));
        properties.setTimeoutSeconds(2);
        properties.setMaxOutputLines(20);
        properties.setMaxOutputBytes(4096);
        service = new RepositoryCommandService(properties);
    }

    @Test
    void shouldExecuteAllowedReadOnlyCommand() {
        Map<String, Object> result = service.execute(
                "yanque-admin",
                "wc",
                List.of("-l", "src/main/java/Sample.java")
        );

        assertThat(result)
                .containsEntry("exitCode", 0)
                .containsEntry("timedOut", false)
                .containsEntry("truncated", false);
        assertThat((String) result.get("output")).contains("2");
    }

    @Test
    void shouldRejectCommandOutsideAllowlist() {
        assertThatThrownBy(() -> service.execute("yanque-admin", "sh", List.of("-c", "id")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("不允许执行");
    }

    @Test
    void shouldRejectUnknownRepositoryAlias() {
        assertThatThrownBy(() -> service.execute("local-checkout", "wc", List.of("README.md")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("仓库不在白名单");
    }

    @Test
    void shouldRejectDangerousRgOption() {
        assertThatThrownBy(() -> service.execute(
                "yanque-admin", "rg", List.of("--pre", "sh", "Sample", "src/main/java")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("rg 参数不在白名单");
    }

    @Test
    void shouldRejectSedWriteMode() {
        assertThatThrownBy(() -> service.execute(
                "yanque-admin", "sed", List.of("-i", "1d", "src/main/java/Sample.java")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("sed 只允许");
    }

    @Test
    void shouldRejectTailFollowMode() {
        assertThatThrownBy(() -> service.execute(
                "yanque-admin", "tail", List.of("-f", "src/main/java/Sample.java")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("禁止 tail -f");
    }

    @Test
    void shouldRejectPathTraversal() {
        assertThatThrownBy(() -> service.execute("yanque-admin", "head", List.of("../secret.txt")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("绝对路径或 ../");
    }
}
