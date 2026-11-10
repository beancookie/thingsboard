package org.thingsboard.examples;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
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
 * 设备增删改查工具（Java 版）。
 */
public class DeviceCrudTool {

    public static void main(String[] args) throws Exception {
        Args a = new Args(args);
        String action = a.get("action", "");
        if (action.isEmpty()) {
            throw new IllegalArgumentException("--action is required");
        }
        TbClient client = new TbClient(a.get("tb-url", "http://localhost:8080"));
        client.authenticate(a.get("api-key", ""), a.get("username", "tenant@thingsboard.org"), a.get("password", ""));
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        JsonElement result;

        switch (action) {
            case "list" -> result = client.request(
                    "/api/tenant/devices?pageSize=" + a.get("page-size", "100") + "&page=" + a.get("page", "0"), "GET", "");
            case "create" -> {
                JsonObject payload = buildCreatePayload(a);
                result = client.request("/api/device", "POST", gson.toJson(payload));
            }
            case "get", "delete", "credentials", "update" -> {
                JsonObject device = resolve(client, a);
                String id = device.getAsJsonObject("id").get("id").getAsString();
                String encoded = TbClient.url(id);
                if ("get".equals(action)) {
                    result = client.request("/api/device/" + encoded, "GET", "");
                } else if ("credentials".equals(action)) {
                    result = client.request("/api/device/" + encoded + "/credentials", "GET", "");
                } else if ("delete".equals(action)) {
                    client.request("/api/device/" + encoded, "DELETE", "");
                    result = JsonParser.parseString("{\"deleted\":\"" + id + "\"}");
                } else {
                    JsonObject updated = device.deepCopy();
                    String config = a.get("config", "");
                    if (!config.isBlank()) {
                        JsonElement overrides = JsonParser.parseString(Files.readString(Path.of(config), StandardCharsets.UTF_8));
                        if (overrides.isJsonObject()) {
                            updated = overrides.getAsJsonObject().deepCopy();
                        }
                    }
                    putIfPresent(updated, "name", a.get("name", ""));
                    putIfPresent(updated, "label", a.get("label", ""));
                    if (!a.get("description", "").isBlank()) {
                        JsonObject additional = updated.has("additionalInfo") && updated.get("additionalInfo").isJsonObject()
                                ? updated.getAsJsonObject("additionalInfo") : new JsonObject();
                        additional.addProperty("description", a.get("description", ""));
                        updated.add("additionalInfo", additional);
                    }
                    result = client.request("/api/device", "POST", gson.toJson(updated));
                }
            }
            default -> throw new IllegalArgumentException("unsupported action: " + action);
        }
        System.out.println(gson.toJson(result));
    }

    static JsonObject resolve(TbClient client, Args a) throws Exception {
        String deviceId = a.get("device-id", "");
        if (!deviceId.isBlank()) {
            return client.request("/api/device/" + TbClient.url(deviceId), "GET", "").getAsJsonObject();
        }
        String name = a.get("device-name", "");
        if (name.isBlank()) {
            throw new IllegalArgumentException("--device-id or --device-name is required");
        }
        JsonElement found = client.findByName(name);
        if (found == null || found.isJsonNull()) {
            throw new IllegalArgumentException("device not found: " + name);
        }
        return found.getAsJsonObject();
    }

    static JsonObject buildCreatePayload(Args a) throws Exception {
        JsonObject payload = new JsonObject();
        String config = a.get("config", "");
        if (!config.isBlank()) {
            JsonElement element = JsonParser.parseString(Files.readString(Path.of(config), StandardCharsets.UTF_8));
            if (element.isJsonObject()) {
                payload = element.getAsJsonObject().deepCopy();
            }
        }
        putIfPresent(payload, "name", a.get("name", ""));
        if (!a.get("profile-id", "").isBlank()) {
            JsonObject profile = new JsonObject();
            profile.addProperty("entityType", "DEVICE_PROFILE");
            profile.addProperty("id", a.get("profile-id", ""));
            payload.add("deviceProfileId", profile);
        }
        putIfPresent(payload, "label", a.get("label", ""));
        if (a.has("gateway") || !a.get("description", "").isBlank()) {
            JsonObject additional = payload.has("additionalInfo") && payload.get("additionalInfo").isJsonObject()
                    ? payload.getAsJsonObject("additionalInfo") : new JsonObject();
            if (a.has("gateway")) {
                additional.addProperty("gateway", true);
            }
            if (!a.get("description", "").isBlank()) {
                additional.addProperty("description", a.get("description", ""));
            }
            payload.add("additionalInfo", additional);
        }
        return payload;
    }

    static void putIfPresent(JsonObject object, String key, String value) {
        if (value != null && !value.isBlank()) {
            object.addProperty(key, value);
        }
    }

    static final class TbClient {
        final String tbUrl;
        final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(30)).build();
        String token;

        TbClient(String tbUrl) {
            this.tbUrl = tbUrl.replaceAll("/+$", "");
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

        JsonElement findByName(String name) throws Exception {
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

        JsonElement request(String path, String method, String body) throws Exception {
            HttpRequest.Builder builder = HttpRequest.newBuilder(URI.create(tbUrl + path))
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
