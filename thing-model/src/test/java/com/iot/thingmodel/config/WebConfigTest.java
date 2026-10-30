package com.iot.thingmodel.config;

import com.iot.thingmodel.auth.AuthInterceptor;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.web.filter.CorsFilter;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.Mockito.mock;

class WebConfigTest {

    private final ThingModelProperties properties = new ThingModelProperties();

    @Test
    void allowsAnyOriginByDefault() throws Exception {
        MockHttpServletResponse response = preflight(filter(), "https://example.com");

        assertEquals(200, response.getStatus());
        assertNotNull(response.getHeader("Access-Control-Allow-Origin"));
    }

    @Test
    void allowsConfiguredOrigin() throws Exception {
        properties.getCors().setAllowedOrigins(List.of("https://allowed.example.com"));

        MockHttpServletResponse response = preflight(filter(), "https://allowed.example.com");

        assertEquals(200, response.getStatus());
        assertEquals("https://allowed.example.com", response.getHeader("Access-Control-Allow-Origin"));
    }

    @Test
    void rejectsOriginOutsideConfiguredList() throws Exception {
        properties.getCors().setAllowedOrigins(List.of("https://allowed.example.com"));
        MockHttpServletRequest request = preflightRequest("https://blocked.example.com");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter().doFilter(request, response, chain);

        assertEquals(403, response.getStatus());
        assertNull(response.getHeader("Access-Control-Allow-Origin"));
        assertNull(chain.getRequest());
    }

    @Test
    void allowsAuthorizationHeaderOnPreflight() throws Exception {
        MockHttpServletRequest request = preflightRequest("https://example.com");
        request.addHeader("Access-Control-Request-Headers", "x-authorization");
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter().doFilter(request, response, new MockFilterChain());

        assertEquals(200, response.getStatus());
        assertNotNull(response.getHeader("Access-Control-Allow-Headers"));
    }

    private CorsFilter filter() {
        return new WebConfig(mock(AuthInterceptor.class), properties).corsFilter();
    }

    private MockHttpServletResponse preflight(CorsFilter filter, String origin) throws Exception {
        MockHttpServletResponse response = new MockHttpServletResponse();
        filter.doFilter(preflightRequest(origin), response, new MockFilterChain());
        return response;
    }

    private MockHttpServletRequest preflightRequest(String origin) {
        MockHttpServletRequest request = new MockHttpServletRequest("OPTIONS", "/api/products");
        request.setRequestURI("/api/products");
        request.addHeader("Origin", origin);
        request.addHeader("Access-Control-Request-Method", "GET");
        return request;
    }
}
