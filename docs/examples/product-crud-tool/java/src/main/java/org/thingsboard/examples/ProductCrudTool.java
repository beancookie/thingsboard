package org.thingsboard.examples;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.HashSet;

/**
 * 产品增删改查工具（Java 版）。
 */
public class ProductCrudTool {

    public static void main(String[] args) throws Exception {
        Args a = new Args(args);
        String action = a.get("action", "");
        if (action.isEmpty()) {
            throw new IllegalArgumentException("--action is required");
        }
        TbClient client = new TbClient(
                a.get("tb-url", "http://localhost:8080"),
                a.get("thingmodel-url", "http://localhost:8080/api/thing-model"));
        client.authenticate(a.get("api-key", ""), a.get("username", "tenant@thingsboard.org"), a.get("password", ""));
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        String productId = a.get("product-id", "");
        String encoded = TbClient.url(productId);
        JsonElement result;

        switch (action) {
            case "list" -> {
                String params = "?pageSize=" + a.get("page-size", "100") + "&page=" + a.get("page", "0");
                String keyword = a.get("keyword", "");
                if (!keyword.isBlank()) {
                    params += "&keyword=" + URLEncoder.encode(keyword, StandardCharsets.UTF_8);
                }
                result = client.request(client.productBase() + params, "GET", "");
            }
            case "get" -> {
                require(productId, "product-id");
                result = client.request(client.productBase() + "/" + encoded, "GET", "");
            }
            case "catalog" -> {
                require(productId, "product-id");
                result = client.request(client.productBase() + "/" + encoded + "/catalog", "GET", "");
            }
            case "delete" -> {
                require(productId, "product-id");
                client.request(client.productBase() + "/" + encoded, "DELETE", "");
                result = JsonParser.parseString("{\"deleted\":\"" + productId + "\"}");
            }
            case "create", "update" -> {
                JsonObject payload = buildCreatePayload(a, gson);
                result = client.request(client.productBase(), "POST", gson.toJson(payload));
            }
            case "update-tsl", "validate" -> {
                require(productId, "product-id");
                JsonObject payload = new JsonObject();
                payload.add("tsl", readJson(a.get("tsl", "")));
                if (!a.get("tsl-version", "").isBlank()) {
                    payload.addProperty("tslVersion", a.get("tsl-version", ""));
                }
                if (a.has("strict-unknown")) {
                    payload.addProperty("strictUnknown", true);
                }
                String suffix = "update-tsl".equals(action) ? "/thing-model" : "/thing-model/validate";
                result = client.request(client.productBase() + "/" + encoded + suffix, action.equals("update-tsl") ? "PUT" : "POST",
                        gson.toJson(payload));
            }
            default -> throw new IllegalArgumentException("unsupported action: " + action);
        }
        System.out.println(gson.toJson(result));
    }

    static JsonObject buildCreatePayload(Args a, Gson gson) throws Exception {
        JsonObject payload = new JsonObject();
        String config = a.get("config", "");
        if (!config.isBlank()) {
            JsonElement element = readJson(config);
            if (element.isJsonObject()) {
                payload = element.getAsJsonObject().deepCopy();
            }
        }
        putIfPresent(payload, "productId", a.get("product-id", ""));
        putIfPresent(payload, "name", a.get("name", ""));
        putIfPresent(payload, "model", a.get("model", ""));
        putIfPresent(payload, "categoryId", a.get("category-id", ""));
        putIfPresent(payload, "tslVersion", a.get("tsl-version", ""));
        if (a.has("strict-unknown")) {
            payload.addProperty("strictUnknown", true);
        }
        String tsl = a.get("tsl", "");
        if (!tsl.isBlank()) {
            payload.add("tsl", readJson(tsl));
        }
        return payload;
    }

    static void putIfPresent(JsonObject object, String key, String value) {
        if (value != null && !value.isBlank()) {
            object.addProperty(key, value);
        }
    }

    static JsonElement readJson(String path) throws Exception {
        if (path == null || path.isBlank()) {
            return JsonNull.INSTANCE;
        }
        return JsonParser.parseString(Files.readString(Path.of(path), StandardCharsets.UTF_8));
    }

    static void require(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("--" + name + " is required");
        }
    }

    static final class TbClient {
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

    static final class Args {
        final Map<String, String> values = new HashMap<>();
        final Set<String> flags = new HashSet<>();

        Args(String[] args) {
            for (int i = 0; i < args.length; i++) {
                String arg = args[i];
                if (!arg.startsWith("--")) {
                    continue;
                }
                String key = arg.substring(2);
                if (key.contains("=")) {
                    String[] parts = key.split("=", 2);
                    values.put(parts[0], parts[1]);
                } else if (i + 1 < args.length && !args[i + 1].startsWith("--")) {
                    values.put(key, args[++i]);
                } else {
                    flags.add(key);
                }
            }
        }

        String get(String key, String def) {
            return values.getOrDefault(key, def);
        }

        boolean has(String key) {
            return values.containsKey(key) || flags.contains(key);
        }
    }
}
