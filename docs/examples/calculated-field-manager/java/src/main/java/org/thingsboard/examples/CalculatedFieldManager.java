package org.thingsboard.examples;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * 计算字段管理工具（Java 版）。
 */
public class CalculatedFieldManager {

    public static void main(String[] args) throws Exception {
        Args a = new Args(args);
        String action = a.get("action", "");
        TbClient client = new TbClient(
                a.get("tb-url", "http://localhost:8080"),
                a.get("thingmodel-url", "http://localhost:8080/api/thing-model"));
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        boolean dryRun = a.has("dry-run");
        if (!dryRun) {
            client.authenticate(a.get("api-key", ""), a.get("username", "tenant@thingsboard.org"), a.get("password", ""));
        }
        String pageSize = a.get("page-size", "100");
        String page = a.get("page", "0");

        switch (action) {
            case "list" -> print(client, gson, dryRun,
                    client.tbUrl + "/api/calculatedFields?pageSize=" + pageSize + "&page=" + page,
                    "GET", null);
            case "create", "update", "test-script" -> {
                String configPath = require(a, "config");
                JsonObject payload = JsonParser.parseString(
                        Files.readString(Path.of(configPath), StandardCharsets.UTF_8)).getAsJsonObject();
                String suffix = "test-script".equals(action) ? "/testScript" : "";
                print(client, gson, dryRun,
                        client.tbUrl + "/api/calculatedField" + suffix,
                        "POST", gson.toJson(payload));
            }
            case "get", "delete", "debug" -> {
                String id = require(a, "calculated-field-id");
                String encoded = TbClient.url(id);
                switch (action) {
                    case "get" -> print(client, gson, dryRun,
                            client.tbUrl + "/api/calculatedField/" + encoded, "GET", null);
                    case "delete" -> print(client, gson, dryRun,
                            client.tbUrl + "/api/calculatedField/" + encoded, "DELETE", null);
                    case "debug" -> print(client, gson, dryRun,
                            client.tbUrl + "/api/calculatedField/" + encoded + "/debug", "GET", null);
                    default -> throw new IllegalArgumentException("unsupported action: " + action);
                }
            }
            default -> throw new IllegalArgumentException("unsupported action: " + action);
        }
    }

    static void print(TbClient client, Gson gson, boolean dryRun,
                      String url, String method, String body) throws Exception {
        if (dryRun) {
            System.out.println("[dry-run] " + method + " " + url);
            if (body != null) {
                System.out.println("[dry-run] " + body);
            }
            return;
        }
        JsonElement result = client.request(url, method, body);
        System.out.println(gson.toJson(result == null ? JsonNull.INSTANCE : result));
    }

    static String require(Args a, String name) {
        String value = a.get(name, "");
        if (value.isBlank()) {
            throw new IllegalArgumentException("--" + name + " is required");
        }
        return value;
    }
}
