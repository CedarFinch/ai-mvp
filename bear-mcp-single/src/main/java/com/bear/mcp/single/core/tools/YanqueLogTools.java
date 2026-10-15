package com.bear.mcp.single.core.tools;

import com.bear.mcp.single.core.log.VolcengineLogService;
import com.volcengine.model.tls.response.SearchLogsResponseV2;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** yanque-admin 日志查询 MCP Tool。 */
@Component
public class YanqueLogTools {
    private static final long DEFAULT_RANGE_SECONDS = 30 * 60;
    private static final long MILLIS_THRESHOLD = 100_000_000_000L;

    private final VolcengineLogService logService;

    public YanqueLogTools(VolcengineLogService logService) {
        this.logService = logService;
    }

    @Tool(
            name = "search_yanque_admin_logs",
            description = "只读查询 yanque-admin 在火山引擎中的日志，支持按关键词、ERROR、异常名或 guid 检索"
    )
    public Map<String, Object> searchLogs(
            @ToolParam(description = "日志查询语句，例如 ERROR、异常名、guid 或 *", required = true)
            String query,
            @ToolParam(description = "开始时间，Unix 秒或毫秒时间戳；不传时默认查询结束时间前 30 分钟", required = false)
            Long startTime,
            @ToolParam(description = "结束时间，Unix 秒或毫秒时间戳；不传时默认为当前时间", required = false)
            Long endTime,
            @ToolParam(description = "返回数量，默认 20，最大 100", required = false)
            Integer limit) {
        long normalizedEndTime = endTime == null ? Instant.now().getEpochSecond() : toEpochSeconds(endTime);
        long normalizedStartTime = startTime == null
                ? normalizedEndTime - DEFAULT_RANGE_SECONDS
                : toEpochSeconds(startTime);
        int normalizedLimit = limit == null ? 20 : Math.min(limit, 100);

        SearchLogsResponseV2 response = logService.search(
                query,
                normalizedStartTime,
                normalizedEndTime,
                normalizedLimit
        );

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("query", query.trim());
        result.put("startTime", normalizedStartTime);
        result.put("endTime", normalizedEndTime);
        result.put("resultStatus", response.getResultStatus());
        result.put("count", response.getCount());
        result.put("hitCount", response.getHitCount());
        result.put("listOver", response.isListOver());
        result.put("analysis", response.isAnalysis());
        result.put("context", response.getContext());
        result.put("elapsedMillisecond", response.getElapsedMillisecond());
        result.put("logs", response.getLogs() == null ? List.of() : response.getLogs());
        return result;
    }

    private long toEpochSeconds(long timestamp) {
        if (timestamp <= 0) {
            throw new IllegalArgumentException("时间戳必须大于 0");
        }
        return timestamp >= MILLIS_THRESHOLD ? timestamp / 1000 : timestamp;
    }
}
