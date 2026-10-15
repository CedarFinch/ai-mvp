package com.bear.mcp.single.core.log;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/** 火山引擎日志服务（TLS）只读查询配置。 */
@Data
@Component
@ConfigurationProperties(prefix = "volcengine.tls")
public class VolcengineTlsProperties {
    private String endpoint;
    private String region;
    private String accessKeyId;
    private String accessKeySecret;
    private String securityToken;
    private String topicId;
}
