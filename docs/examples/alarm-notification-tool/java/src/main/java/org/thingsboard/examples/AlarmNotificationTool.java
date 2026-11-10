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
 * 告警与通知工具（Java 版）。
 */
public class AlarmNotificationTool {

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
            case "list-alarms" -> print(client, gson, dryRun,
                    client.tbUrl + "/api/alarms?pageSize=" + pageSize + "&page=" + page,
                    "GET", null);
            case "list-targets" -> print(client, gson, dryRun,
                    client.tbUrl + "/api/notification/targets?pageSize=" + pageSize + "&page=" + page,
                    "GET", null);
            case "list-templates" -> print(client, gson, dryRun,
                    client.tbUrl + "/api/notification/templates?pageSize=" + pageSize + "&page=" + page,
                    "GET", null);
            case "preview-notification", "send-notification" -> {
                String payloadPath = require(a, "payload");
                JsonObject payload = JsonParser.parseString(
                        Files.readString(Path.of(payloadPath), StandardCharsets.UTF_8)).getAsJsonObject();
                String suffix = "preview-notification".equals(action) ? "/preview" : "";
                print(client, gson, dryRun,
                        client.tbUrl + "/api/notification/request" + suffix,
                        "POST", gson.toJson(payload));
            }
            case "get-alarm", "ack", "clear", "assign", "comment" -> {
                String alarmId = require(a, "alarm-id");
                String encoded = TbClient.url(alarmId);
                switch (action) {
                    case "get-alarm" -> print(client, gson, dryRun,
                            client.tbUrl + "/api/alarm/" + encoded, "GET", null);
                    case "ack" -> print(client, gson, dryRun,
                            client.tbUrl + "/api/alarm/" + encoded + "/ack", "POST", null);
                    case "clear" -> print(client, gson, dryRun,
                            client.tbUrl + "/api/alarm/" + encoded + "/clear", "POST", null);
                    case "assign" -> {
                        String assigneeId = require(a, "assignee-id");
                        print(client, gson, dryRun,
                                client.tbUrl + "/api/alarm/" + encoded + "/assign/"
                                        + TbClient.url(assigneeId),
                                "POST", null);
                    }
                    case "comment" -> {
                        String text = require(a, "comment");
                        JsonObject payload = new JsonObject();
                        JsonObject comment = new JsonObject();
                        comment.addProperty("text", text);
                        payload.add("comment", comment);
                        print(client, gson, dryRun,
                                client.tbUrl + "/api/alarm/" + encoded + "/comment",
                                "POST", gson.toJson(payload));
                    }
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
