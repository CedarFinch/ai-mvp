package com.bear.mcp.single.core.storage;

import org.junit.jupiter.api.Test;

import java.net.URI;

import static org.assertj.core.api.Assertions.assertThat;

class TosStorageServiceTest {

    @Test
    void presignedUrlShouldUsePublicEndpoint() {
        TosStorageProperties properties = properties(
                "tos-cn-shanghai.ivolces.com",
                "https://tos-cn-shanghai.volces.com"
        );
        TosStorageService service = new TosStorageService(properties);

        TosStorageService.PresignResult result = service.presignGet("resources/test/document.md");

        assertThat(URI.create(result.uploadUrl()).getHost())
                .isEqualTo("test-bucket.tos-cn-shanghai.volces.com");
    }

    @Test
    void presignedUrlShouldFallBackToServiceEndpoint() {
        TosStorageProperties properties = properties("tos-cn-shanghai.volces.com", "");
        TosStorageService service = new TosStorageService(properties);

        TosStorageService.PresignResult result = service.presignPut("resources/test/document.md");

        assertThat(URI.create(result.uploadUrl()).getHost())
                .isEqualTo("test-bucket.tos-cn-shanghai.volces.com");
    }

    private TosStorageProperties properties(String endpoint, String publicEndpoint) {
        TosStorageProperties properties = new TosStorageProperties();
        properties.setEndpoint(endpoint);
        properties.setPublicEndpoint(publicEndpoint);
        properties.setRegion("cn-shanghai");
        properties.setBucket("test-bucket");
        properties.setAccessKey("test-access-key");
        properties.setSecretKey("test-secret-key");
        properties.setUploadExpireSeconds(600L);
        return properties;
    }
}
