package com.iot.thingmodel.config;

import com.iot.thingmodel.auth.AuthInterceptor;
import com.iot.thingmodel.common.Constants;
import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    private final AuthInterceptor authInterceptor;
    private final ThingModelProperties properties;

    public WebConfig(AuthInterceptor authInterceptor, ThingModelProperties properties) {
        this.authInterceptor = authInterceptor;
        this.properties = properties;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(authInterceptor)
                .addPathPatterns(Constants.Api.API_PATTERN)
                .excludePathPatterns(Constants.Api.ERROR_PATH);
    }

    @Bean
    public CorsFilter corsFilter() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOriginPatterns(properties.getCors().getAllowedOrigins());
        configuration.setAllowedMethods(Constants.Api.CORS_METHODS);
        configuration.setAllowedHeaders(List.of(Constants.Api.CORS_ALL_HEADERS));
        configuration.setAllowCredentials(properties.getCors().isAllowCredentials());
        configuration.setMaxAge(properties.getCors().getMaxAge());

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration(Constants.Api.API_PATTERN, configuration);
        return new CorsFilter(source);
    }
}
