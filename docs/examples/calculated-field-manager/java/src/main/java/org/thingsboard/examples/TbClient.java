package org.thingsboard.examples;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonParser;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;

final class TbClient {
    final String tbUrl;
    final String thingmodelUrl;
    final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(30)).build();
    String token;

    TbClient(String tbUrl, String thingmodelUrl) {
        this.tbUrl = tbUrl.replaceAll("/+$", "");
        this.thingmodelUrl = thingmodelUrl.replaceAll("/+$", "");
    }

    String productBase() {
        if (thingmodelUrl.endsWith("/api/thing-model") || thingmodelUrl.endsWith("/api")) {
            return thingmodelUrl + "/products";
        }
        return thingmodelUrl + "/api/products";
    }

    void authenticate(String apiKey, String username, String password) throws Exception {
        if (apiKey != null && !apiKey.isBlank()) {
            String auth = "ApiKey " + apiKey.trim();
            HttpResponse<String> userResp = http.send(HttpRequest.newBuilder(URI.create(tbUrl + "/api/auth/user"))
                    .header("X-Authorization", auth).timeout(Duration.ofSeconds(30)).GET().build(),
                    HttpResponse.BodyHandlers.ofString());
            check(userResp);
            String userId = JsonParser.parseString(userResp.body()).getAsJsonObject()
                    .getAsJsonObject("id").get("id").getAsString();
            HttpResponse<String> tokenResp = http.send(HttpRequest.newBuilder(URI.create(tbUrl + "/api/user/" + userId + "/token"))
                    .header("X-Authorization", auth).timeout(Duration.ofSeconds(30)).GET().build(),
                    HttpResponse.BodyHandlers.ofString());
            check(tokenResp);
            token = JsonParser.parseString(tokenResp.body()).getAsJsonObject().get("token").getAsString();
        } else {
            String body = new Gson().toJson(Map.of("username", username, "password", password));
            HttpResponse<String> resp = http.send(HttpRequest.newBuilder(URI.create(tbUrl + "/api/auth/login"))
                    .header("Content-Type", "application/json").timeout(Duration.ofSeconds(30))
                    .POST(HttpRequest.BodyPublishers.ofString(body)).build(),
                    HttpResponse.BodyHandlers.ofString());
            check(resp);
            token = JsonParser.parseString(resp.body()).getAsJsonObject().get("token").getAsString();
        }
    }

    JsonElement findDeviceByName(String name) throws Exception {
        HttpResponse<String> resp = http.send(HttpRequest.newBuilder(URI.create(tbUrl + "/api/tenant/devices?deviceName="
                        + URLEncoder.encode(name, StandardCharsets.UTF_8)))
                .header("X-Authorization", "Bearer " + token).timeout(Duration.ofSeconds(30)).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() == 404) {
            return null;
        }
        check(resp);
        return resp.body().isBlank() ? null : JsonParser.parseString(resp.body());
    }

    JsonElement request(String url, String method, String body) throws Exception {
        HttpRequest.Builder builder = HttpRequest.newBuilder(URI.create(url))
                .header("X-Authorization", "Bearer " + token).timeout(Duration.ofSeconds(30));
        if ("GET".equals(method)) {
            builder.GET();
        } else if ("DELETE".equals(method)) {
            builder.DELETE();
        } else {
            builder.header("Content-Type", "application/json")
                    .method(method, HttpRequest.BodyPublishers.ofString(body == null ? "" : body));
        }
        HttpResponse<String> resp = http.send(builder.build(), HttpResponse.BodyHandlers.ofString());
        check(resp);
        return resp.body().isBlank() ? JsonNull.INSTANCE : JsonParser.parseString(resp.body());
    }

    void check(HttpResponse<String> resp) {
        if (resp.statusCode() >= 400) {
            throw new RuntimeException("HTTP " + resp.statusCode() + " " + resp.uri() + ": " + resp.body());
        }
    }

    static String url(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8).replace("+", "%20");
    }
}
