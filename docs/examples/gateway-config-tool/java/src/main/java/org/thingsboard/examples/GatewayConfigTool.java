package org.thingsboard.examples;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * 网关与子设备配置工具（Java 版）。
 */
public class GatewayConfigTool {

    public static void main(String[] args) throws Exception {
        Args a = new Args(args);
        String action = a.get("action", "");
        TbClient client = new TbClient(
                a.get("tb-url", "http://localhost:8080"),
                a.get("thingmodel-url", "http://localhost:8080/api/thing-model"));
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        boolean dryRun = a.has("dry-run");
        if (dryRun) {
            System.out.println("[dry-run] action=" + action);
        } else {
            client.authenticate(a.get("api-key", ""), a.get("username", "tenant@thingsboard.org"), a.get("password", ""));
        }

        switch (action) {
            case "create-gateway" -> {
                String name = require(a, "gateway-name");
                JsonObject payload = devicePayload(name, a.get("profile-id", ""), true);
                if (dryRun) {
                    System.out.println("[dry-run] POST /api/device " + gson.toJson(payload));
                } else {
                    System.out.println(gson.toJson(client.request(client.tbUrl + "/api/device", "POST", gson.toJson(payload))));
                }
            }
            case "create-sub-device" -> {
                String name = require(a, "sub-device-name");
                JsonObject payload = devicePayload(name, a.get("profile-id", ""), false);
                if (dryRun) {
                    System.out.println("[dry-run] POST /api/device " + gson.toJson(payload));
                } else {
                    System.out.println(gson.toJson(client.request(client.tbUrl + "/api/device", "POST", gson.toJson(payload))));
                }
            }
            case "bind" -> {
                String gatewayName = require(a, "gateway-name");
                String subName = require(a, "sub-device-name");
                if (dryRun) {
                    System.out.println("[dry-run] POST /api/relation gateway=" + gatewayName + " sub=" + subName);
                } else {
                    String gatewayId = deviceId(client, gatewayName);
                    String subId = deviceId(client, subName);
                    JsonObject relation = new JsonObject();
                    relation.add("from", entity("DEVICE", gatewayId));
                    relation.add("to", entity("DEVICE", subId));
                    relation.addProperty("type", a.get("relation-type", "Contains"));
                    relation.addProperty("typeGroup", "COMMON");
                    System.out.println(gson.toJson(client.request(client.tbUrl + "/api/relation", "POST", gson.toJson(relation))));
                }
            }
            case "list" -> {
                if (dryRun) {
                    System.out.println("[dry-run] GET /api/tenant/devices");
                } else {
                    JsonObject page = client.request(client.tbUrl + "/api/tenant/devices?pageSize=100&page=0", "GET", "").getAsJsonObject();
                    JsonArray rows = new JsonArray();
                    if (page.has("data")) {
                        for (JsonElement element : page.getAsJsonArray("data")) {
                            JsonObject device = element.getAsJsonObject();
                            JsonObject additional = device.has("additionalInfo") && device.get("additionalInfo").isJsonObject()
                                    ? device.getAsJsonObject("additionalInfo") : new JsonObject();
                            if (additional.has("gateway") && additional.get("gateway").getAsBoolean()) {
                                JsonObject row = new JsonObject();
                                row.add("id", device.getAsJsonObject("id"));
                                row.addProperty("name", device.has("name") ? device.get("name").getAsString() : "");
                                rows.add(row);
                            }
                        }
                    }
                    System.out.println(gson.toJson(rows));
                }
            }
            case "status" -> withGateway(client, a, gson, dryRun, "/values/attributes?keys=active,lastConnectTime,lastDisconnectTime", "GET", null);
            case "get-config" -> withGateway(client, a, gson, dryRun,
                    "/values/attributes?keys=general_configuration,active_connectors,inactive_connectors", "GET", null);
            case "set-config" -> {
                String configPath = require(a, "config");
                JsonElement config = JsonParser.parseString(Files.readString(Path.of(configPath), StandardCharsets.UTF_8));
                JsonObject body = new JsonObject();
                if (config.isJsonObject() && config.getAsJsonObject().has("general_configuration")) {
                    body.add("general_configuration", config.getAsJsonObject().get("general_configuration"));
                } else {
                    body.add("general_configuration", config);
                }
                withGateway(client, a, gson, dryRun, "/attributes/SHARED_SCOPE", "POST", gson.toJson(body));
            }
            default -> throw new IllegalArgumentException("unsupported action: " + action);
        }
    }

    static void withGateway(TbClient client, Args a, Gson gson, boolean dryRun,
                            String suffix, String method, String body) throws Exception {
        String gatewayName = a.get("gateway-name", "");
        String gatewayId = a.get("gateway-id", "");
        if (gatewayId.isBlank()) {
            require(a, "gateway-name");
        }
        if (dryRun) {
            System.out.println("[dry-run] " + method + " gateway=" + (gatewayId.isBlank() ? gatewayName : gatewayId) + suffix);
            if (body != null) {
                System.out.println("[dry-run] " + body);
            }
            return;
        }
        if (gatewayId.isBlank()) {
            gatewayId = deviceId(client, gatewayName);
        }
        String url = client.tbUrl + "/api/plugins/telemetry/DEVICE/" + TbClient.url(gatewayId) + suffix;
        System.out.println(gson.toJson(client.request(url, method, body)));
    }

    static String deviceId(TbClient client, String name) throws Exception {
        JsonElement device = client.findDeviceByName(name);
        if (device == null) {
            throw new IllegalArgumentException("device not found: " + name);
        }
        return device.getAsJsonObject().getAsJsonObject("id").get("id").getAsString();
    }

    static JsonObject devicePayload(String name, String profileId, boolean gateway) {
        JsonObject payload = new JsonObject();
        payload.addProperty("name", name);
        payload.addProperty("type", "default");
        if (profileId != null && !profileId.isBlank()) {
            payload.add("deviceProfileId", entity("DEVICE_PROFILE", profileId));
        }
        if (gateway) {
            JsonObject additional = new JsonObject();
            additional.addProperty("gateway", true);
            payload.add("additionalInfo", additional);
        }
        return payload;
    }

    static JsonObject entity(String type, String id) {
        JsonObject object = new JsonObject();
        object.addProperty("entityType", type);
        object.addProperty("id", id);
        return object;
    }

    static String require(Args a, String name) {
        String value = a.get(name, "");
        if (value.isBlank()) {
            throw new IllegalArgumentException("--" + name + " is required");
        }
        return value;
    }
}
