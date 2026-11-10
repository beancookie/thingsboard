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
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 物模型产品导出工具（Java 版）。
 *
 * 从 ThingsBoard / thing-model 平台导出产品列表与 TSL 物模型。
 */
public class ThingModelProductExporter {

    public static void main(String[] args) throws Exception {
        Args a = new Args(args);
        String tbUrl = a.get("tb-url", "http://localhost:8080");
        String tmUrl = a.get("thingmodel-url", "http://localhost:8080/api/thing-model");
        String apiKey = a.get("api-key", "");
        String username = a.get("username", "tenant@thingsboard.org");
        String password = a.get("password", "");
        String outputDir = a.get("output-dir", "product-export");
        boolean noDetail = a.has("no-detail");

        TbClient client = new TbClient(tbUrl, tmUrl);
        client.authenticate(apiKey, username, password);

        JsonArray products = client.productList();
        Path out = Path.of(outputDir);
        Path tslDir = out.resolve("tsl");
        Files.createDirectories(tslDir);

        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        JsonArray exported = new JsonArray();
        int exportedCount = 0;
        for (JsonElement element : products) {
            JsonObject item = element.getAsJsonObject();
            String productId = getString(item, "productId");
            if (productId.isEmpty()) {
                continue;
            }
            JsonObject row = new JsonObject();
            row.addProperty("productId", productId);
            row.addProperty("name", getString(item, "name"));
            row.addProperty("model", getString(item, "model"));
            row.addProperty("tslVersion", getString(item, "tslVersion"));
            row.addProperty("status", getString(item, "status"));
            try {
                JsonElement thingModel = client.getThingModel(productId);
                JsonElement tsl = thingModel;
                if (thingModel.isJsonObject() && thingModel.getAsJsonObject().has("tsl")) {
                    tsl = thingModel.getAsJsonObject().get("tsl");
                }
                Path tslFile = tslDir.resolve(productId + ".tsl.json");
                Files.writeString(tslFile, gson.toJson(tsl), StandardCharsets.UTF_8);
                row.addProperty("tslFile", "tsl/" + tslFile.getFileName());
                if (!noDetail) {
                    row.add("detail", client.getProductDetail(productId));
                }
                exportedCount++;
                System.out.println("exported " + productId + " -> " + row.get("tslFile").getAsString());
            } catch (Exception e) {
                row.addProperty("error", e.getMessage());
                System.err.println("failed " + productId + ": " + e.getMessage());
            }
            exported.add(row);
        }

        JsonObject summary = new JsonObject();
        summary.addProperty("tbUrl", client.tbUrl);
        summary.addProperty("thingmodelUrl", client.thingmodelUrl);
        summary.addProperty("count", exportedCount);
        summary.add("products", exported);
        Files.writeString(out.resolve("products.json"), gson.toJson(summary), StandardCharsets.UTF_8);
        System.out.println("summary exported=" + exportedCount + " output=" + out);
    }

    static String getString(JsonObject o, String key) {
        return o.has(key) && !o.get(key).isJsonNull() ? o.get(key).getAsString() : "";
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
                JsonObject user = JsonParser.parseString(userResp.body()).getAsJsonObject();
                String userId = user.getAsJsonObject("id").get("id").getAsString();
                HttpResponse<String> tokenResp = http.send(HttpRequest.newBuilder(URI.create(tbUrl + "/api/user/" + userId + "/token"))
                        .header("X-Authorization", auth).timeout(Duration.ofSeconds(30)).GET().build(),
                        HttpResponse.BodyHandlers.ofString());
                check(tokenResp);
                token = JsonParser.parseString(tokenResp.body()).getAsJsonObject().get("token").getAsString();
            } else {
                if (password == null || password.isBlank()) {
                    throw new IllegalArgumentException("需要 --password 或 --api-key");
                }
                String body = new Gson().toJson(Map.of("username", username, "password", password));
                HttpResponse<String> resp = http.send(HttpRequest.newBuilder(URI.create(tbUrl + "/api/auth/login"))
                        .header("Content-Type", "application/json").timeout(Duration.ofSeconds(30))
                        .POST(HttpRequest.BodyPublishers.ofString(body)).build(),
                        HttpResponse.BodyHandlers.ofString());
                check(resp);
                token = JsonParser.parseString(resp.body()).getAsJsonObject().get("token").getAsString();
            }
        }

        JsonArray productList() throws Exception {
            return request(productBase(), "GET", "").getAsJsonArray();
        }

        JsonElement getProductDetail(String productId) throws Exception {
            return request(productBase() + "/" + url(productId), "GET", "");
        }

        JsonElement getThingModel(String productId) throws Exception {
            return request(productBase() + "/" + url(productId) + "/thing-model", "GET", "");
        }

        JsonElement request(String url, String method, String body) throws Exception {
            HttpRequest.Builder builder = HttpRequest.newBuilder(URI.create(url))
                    .header("X-Authorization", "Bearer " + token)
                    .timeout(Duration.ofSeconds(30));
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
