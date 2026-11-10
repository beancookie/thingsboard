package org.thingsboard.examples;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;

/**
 * 客户与用户初始化工具（Java 版）。
 */
public class CustomerUserProvisioner {

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
            case "list-customers" -> print(client, gson, dryRun,
                    client.tbUrl + "/api/customers?pageSize=" + pageSize + "&page=" + page,
                    "GET", null);
            case "create-customer" -> {
                String name = require(a, "customer-name");
                JsonObject payload = new JsonObject();
                payload.addProperty("title", name);
                putIfPresent(payload, "email", a.get("email", ""));
                putIfPresent(payload, "country", a.get("country", ""));
                putIfPresent(payload, "city", a.get("city", ""));
                putIfPresent(payload, "phone", a.get("phone", ""));
                putIfPresent(payload, "description", a.get("description", ""));
                print(client, gson, dryRun,
                        client.tbUrl + "/api/customer", "POST", gson.toJson(payload));
            }
            case "create-user" -> {
                String customerId = require(a, "customer-id");
                String email = require(a, "email");
                JsonObject payload = new JsonObject();
                JsonObject customer = new JsonObject();
                customer.addProperty("entityType", "CUSTOMER");
                customer.addProperty("id", customerId);
                payload.add("customerId", customer);
                payload.addProperty("email", email);
                payload.addProperty("firstName", a.get("first-name", "Customer"));
                payload.addProperty("lastName", a.get("last-name", "User"));
                payload.addProperty("authority", "CUSTOMER_USER");
                String url = client.tbUrl + "/api/user?sendActivationMail="
                        + a.has("send-activation-mail");
                print(client, gson, dryRun, url, "POST", gson.toJson(payload));
            }
            case "list-users" -> {
                String customerId = require(a, "customer-id");
                print(client, gson, dryRun,
                        client.tbUrl + "/api/customer/" + TbClient.url(customerId)
                                + "/users?pageSize=" + pageSize + "&page=" + page,
                        "GET", null);
            }
            case "assign-device" -> {
                String customerId = require(a, "customer-id");
                String deviceId = require(a, "device-id");
                print(client, gson, dryRun,
                        client.tbUrl + "/api/customer/" + TbClient.url(customerId)
                                + "/device/" + TbClient.url(deviceId),
                        "POST", null);
            }
            case "assign-asset" -> {
                String customerId = require(a, "customer-id");
                String assetId = require(a, "asset-id");
                print(client, gson, dryRun,
                        client.tbUrl + "/api/customer/" + TbClient.url(customerId)
                                + "/asset/" + TbClient.url(assetId),
                        "POST", null);
            }
            case "delete-customer" -> {
                String customerId = require(a, "customer-id");
                print(client, gson, dryRun,
                        client.tbUrl + "/api/customer/" + TbClient.url(customerId),
                        "DELETE", null);
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

    static void putIfPresent(JsonObject object, String key, String value) {
        if (value != null && !value.isBlank()) {
            object.addProperty(key, value);
        }
    }

    static String require(Args a, String name) {
        String value = a.get(name, "");
        if (value.isBlank()) {
            throw new IllegalArgumentException("--" + name + " is required");
        }
        return value;
    }
}
