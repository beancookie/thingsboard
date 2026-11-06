package com.iot.thingmodel.auth;

import com.iot.thingmodel.common.ApiException;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TbUserVerifierTest {

    @Test
    void normalizesBearerToken() {
        assertEquals("jwt-value", TbUserVerifier.normalize("Bearer jwt-value"));
        assertEquals("jwt-value", TbUserVerifier.normalize("bearer jwt-value"));
    }

    @Test
    void normalizesApiKeyToken() {
        assertEquals("tb_key", TbUserVerifier.normalize("ApiKey tb_key"));
        assertEquals("tb_key", TbUserVerifier.normalize("apikey tb_key"));
        assertEquals("tb_key", TbUserVerifier.normalize("tb_key"));
    }

    @Test
    void rejectsBlankToken() {
        assertThrows(ApiException.class, () -> TbUserVerifier.normalize(null));
        assertThrows(ApiException.class, () -> TbUserVerifier.normalize("   "));
        assertThrows(ApiException.class, () -> TbUserVerifier.normalize("Bearer "));
        assertThrows(ApiException.class, () -> TbUserVerifier.normalize("ApiKey "));
    }

    @Test
    void detectsApiKeyForms() {
        assertTrue(TbUserVerifier.isApiKey("ApiKey tb_key"));
        assertTrue(TbUserVerifier.isApiKey("apikey tb_key"));
        assertTrue(TbUserVerifier.isApiKey("tb_key"));
        assertFalse(TbUserVerifier.isApiKey("Bearer tb_key"));
        assertFalse(TbUserVerifier.isApiKey("eyJhbGciOiJIUzI1NiJ9.payload.signature"));
        assertFalse(TbUserVerifier.isApiKey(null));
    }
}
