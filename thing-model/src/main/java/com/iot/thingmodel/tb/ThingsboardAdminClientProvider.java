package com.iot.thingmodel.tb;

import com.iot.thingmodel.config.ThingModelProperties;
import org.springframework.stereotype.Component;
import org.thingsboard.client.ThingsboardClient;

@Component
public class ThingsboardAdminClientProvider {

    private final ThingModelProperties properties;

    public ThingsboardAdminClientProvider(ThingModelProperties properties) {
        this.properties = properties;
    }

    public ThingsboardClient get(String token) {
        ThingsboardClient client = ThingsboardClient.builder()
                .url(properties.getTb().getBaseUrl())
                .retryOnRateLimit(false)
                .build();
        client.setToken(token);
        return client;
    }
}
