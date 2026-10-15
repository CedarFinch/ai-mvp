package com.bear.mcp.single.core.repository;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;

/** Bear MCP 源码只读检索配置。仓库对外使用稳定别名，内部映射到各环境的真实目录名。 */
@Data
@Component
@ConfigurationProperties(prefix = "bear.repository-command")
public class RepositoryCommandProperties {
    private String root = "/data/repositories";
    private Map<String, String> repositories = new LinkedHashMap<>(Map.of("yanque-admin", "yanque-admin"));
    private int timeoutSeconds = 5;
    private int maxOutputLines = 300;
    private int maxOutputBytes = 20_000;
}
