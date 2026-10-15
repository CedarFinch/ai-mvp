package com.bear.mcp.single.core.log;

import com.volcengine.model.tls.ClientBuilder;
import com.volcengine.model.tls.ClientConfig;
import com.volcengine.model.tls.exception.LogException;
import com.volcengine.model.tls.request.SearchLogsRequest;
import com.volcengine.model.tls.response.SearchLogsResponseV2;
import com.volcengine.service.tls.TLSLogClient;
import jakarta.annotation.PreDestroy;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

/** 通过火山引擎 Java SDK 查询 yanque-admin 日志。 */
@Service
public class VolcengineLogService {
    private final VolcengineTlsProperties properties;
    private volatile TLSLogClient client;

    public VolcengineLogService(VolcengineTlsProperties properties) {
        this.properties = properties;
    }

    public SearchLogsResponseV2 search(String query, long startTime, long endTime, int limit) {
        validateSearch(query, startTime, endTime, limit);

        SearchLogsRequest request = new SearchLogsRequest();
        request.setTopicId(properties.getTopicId());
        request.setQuery(query.trim());
        request.setStartTime(startTime);
        request.setEndTime(endTime);
        request.setLimit(Math.min(limit, 100));

        try {
            return client().searchLogsV2(request);
        } catch (LogException e) {
            throw new IllegalStateException(
                    "火山日志查询失败: code=" + e.getErrorCode()
                            + ", requestId=" + e.getRequestId()
                            + ", message=" + e.getErrorMessage(),
                    e
            );
        }
    }

    private TLSLogClient client() {
        validateConfig();
        TLSLogClient current = client;
        if (current == null) {
            synchronized (this) {
                current = client;
                if (current == null) {
                    ClientConfig config = new ClientConfig(
                            properties.getEndpoint().trim(),
                            properties.getRegion().trim(),
                            properties.getAccessKeyId().trim(),
                            properties.getAccessKeySecret().trim(),
                            valueOrEmpty(properties.getSecurityToken())
                    );
                    try {
                        current = ClientBuilder.newClient(config);
                    } catch (LogException e) {
                        throw new IllegalStateException("火山日志客户端初始化失败: " + e.getErrorMessage(), e);
                    }
                    client = current;
                }
            }
        }
        return current;
    }

    private void validateConfig() {
        if (!StringUtils.hasText(properties.getEndpoint())
                || !StringUtils.hasText(properties.getRegion())
                || !StringUtils.hasText(properties.getAccessKeyId())
                || !StringUtils.hasText(properties.getAccessKeySecret())
                || !StringUtils.hasText(properties.getTopicId())) {
            throw new IllegalStateException(
                    "火山日志配置不完整，请配置 VOLCENGINE_ENDPOINT、VOLCENGINE_REGION、"
                            + "VOLCENGINE_ACCESS_KEY_ID、VOLCENGINE_ACCESS_KEY_SECRET、VOLCENGINE_TLS_TOPIC_ID"
            );
        }
    }

    private void validateSearch(String query, long startTime, long endTime, int limit) {
        if (!StringUtils.hasText(query)) {
            throw new IllegalArgumentException("query 不能为空");
        }
        if (startTime <= 0 || endTime <= 0 || startTime >= endTime) {
            throw new IllegalArgumentException("日志查询时间范围不合法，startTime 必须早于 endTime");
        }
        if (limit < 1) {
            throw new IllegalArgumentException("limit 必须大于 0");
        }
    }

    private String valueOrEmpty(String value) {
        return StringUtils.hasText(value) ? value.trim() : "";
    }

    @PreDestroy
    public void close() {
        TLSLogClient current = client;
        if (current != null) {
            current.close();
        }
    }
}
