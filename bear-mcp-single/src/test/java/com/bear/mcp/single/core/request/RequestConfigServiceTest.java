package com.bear.mcp.single.core.request;

import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.Request;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class RequestConfigServiceTest {

    @Test
    void injectsServiceHeadersForYanqueAdminRequests() {
        RequestConfigService service = service("http://yanque-admin:8080/", "shared-secret");
        Request.Builder builder = new Request.Builder().url("http://yanque-admin:8080/yq-admin/api/classes");

        service.applyYanqueAdminAuth(builder, "http://yanque-admin:8080/yq-admin/api/classes");

        Request request = builder.build();
        assertEquals("true", request.header("X-Bear-Mcp-Request"));
        assertEquals("shared-secret", request.header("X-Bear-Mcp-Secret"));
    }

    @Test
    void doesNotLeakServiceSecretToOtherHosts() {
        RequestConfigService service = service("http://yanque-admin:8080", "shared-secret");
        Request.Builder builder = new Request.Builder().url("https://example.com/yq-admin/api/classes");

        service.applyYanqueAdminAuth(builder, "https://example.com/yq-admin/api/classes");

        Request request = builder.build();
        assertNull(request.header("X-Bear-Mcp-Request"));
        assertNull(request.header("X-Bear-Mcp-Secret"));
    }

    @Test
    void doesNotInjectHeadersWhenSecretIsMissing() {
        RequestConfigService service = service("http://yanque-admin:8080", "");
        Request.Builder builder = new Request.Builder().url("http://yanque-admin:8080/yq-admin/api/classes");

        service.applyYanqueAdminAuth(builder, "http://yanque-admin:8080/yq-admin/api/classes");

        Request request = builder.build();
        assertNull(request.header("X-Bear-Mcp-Request"));
        assertNull(request.header("X-Bear-Mcp-Secret"));
    }

    private RequestConfigService service(String baseUrl, String secret) {
        return new RequestConfigService(null, new ObjectMapper(), baseUrl, secret);
    }
}
