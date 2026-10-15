package com.bear.mcp.single.core.tools;

import com.bear.mcp.single.core.log.VolcengineLogService;
import com.volcengine.model.tls.response.SearchLogsResponseV2;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class YanqueLogToolsTest {
    @Mock
    private VolcengineLogService logService;

    @Mock
    private SearchLogsResponseV2 response;

    @InjectMocks
    private YanqueLogTools tools;

    @Test
    void shouldNormalizeMillisecondTimestampsAndClampLimit() {
        when(logService.search("ERROR", 1_700_000_000L, 1_700_001_800L, 100)).thenReturn(response);
        when(response.getLogs()).thenReturn(List.of(Map.of("__content__", "test error")));

        Map<String, Object> result = tools.searchLogs(
                "ERROR",
                1_700_000_000_000L,
                1_700_001_800_000L,
                500
        );

        verify(logService).search("ERROR", 1_700_000_000L, 1_700_001_800L, 100);
        assertThat(result)
                .containsEntry("query", "ERROR")
                .containsEntry("startTime", 1_700_000_000L)
                .containsEntry("endTime", 1_700_001_800L);
        assertThat(result.get("logs")).isEqualTo(List.of(Map.of("__content__", "test error")));
    }

    @Test
    void shouldUseThirtyMinuteRangeAndDefaultLimit() {
        when(logService.search(org.mockito.ArgumentMatchers.eq("guid-1"),
                org.mockito.ArgumentMatchers.anyLong(),
                org.mockito.ArgumentMatchers.anyLong(),
                org.mockito.ArgumentMatchers.eq(20))).thenReturn(response);

        Map<String, Object> result = tools.searchLogs("guid-1", null, null, null);

        long startTime = (Long) result.get("startTime");
        long endTime = (Long) result.get("endTime");
        assertThat(endTime - startTime).isEqualTo(30 * 60);
        verify(logService).search("guid-1", startTime, endTime, 20);
    }
}
