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
import java.util.ArrayList;
import java.util.List;

/**
 * 设备批量注册工具（Java 版）。
 */
public class DeviceBulkRegistrar {

    public static void main(String[] args) throws Exception {
        Args a = new Args(args);
        String productId = a.get("product-id", "");
        if (productId.isBlank()) {
            throw new IllegalArgumentException("--product-id is required");
        }
        TbClient client = new TbClient(
                a.get("tb-url", "http://localhost:8080"),
                a.get("thingmodel-url", "http://localhost:8080/api/thing-model"));
        boolean dryRun = a.has("dry-run");
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        List<String> names = buildNames(a);
        if (dryRun) {
            for (String name : names) {
                JsonObject payload = devicePayload(name, a.get("profile-id", ""), a.has("gateway"));
                System.out.println("[dry-run] POST /api/device " + gson.toJson(payload));
            }
            return;
        }

        client.authenticate(a.get("api-key", ""), a.get("username", "tenant@thingsboard.org"), a.get("password", ""));
        JsonObject product = client.request(client.productBase() + "/" + TbClient.url(productId), "GET", "").getAsJsonObject();
        JsonObject info = product.has("product") && product.get("product").isJsonObject()
                ? product.getAsJsonObject("product") : product;
        String profileId = a.get("profile-id", "");
        if (profileId.isBlank() && info.has("tbProfileId")) {
            profileId = info.get("tbProfileId").getAsString();
        }
        if (profileId.isBlank()) {
            throw new IllegalStateException("product is not synced: missing tbProfileId");
        }
        String tenantId = info.has("tenantId") ? info.get("tenantId").getAsString() : "";
        String tslVersion = info.has("tslVersion") ? info.get("tslVersion").getAsString() : "1.0";

        String gatewayId = "";
        String gatewayName = a.get("gateway-device", "");
        if (!gatewayName.isBlank()) {
            JsonElement gateway = client.findDeviceByName(gatewayName);
            if (gateway == null) {
                throw new IllegalArgumentException("gateway not found: " + gatewayName);
            }
            gatewayId = gateway.getAsJsonObject().getAsJsonObject("id").get("id").getAsString();
        }

        Path outputDir = Path.of(a.get("output-dir", "."));
        Files.createDirectories(outputDir);
        StringBuilder csv = new StringBuilder();
        csv.append("product_id,device_name,device_id,access_token,tsl_version,profile_id,site_code,gateway,status,error\n");
        int created = 0;
        int skipped = 0;
        int failed = 0;
        for (String name : names) {
            String deviceId = "";
            String accessToken = "";
            String status;
            String error = "";
            try {
                JsonElement existing = client.findDeviceByName(name);
                if (existing != null) {
                    deviceId = existing.getAsJsonObject().getAsJsonObject("id").get("id").getAsString();
                    status = "skipped";
                    skipped++;
                } else {
                    JsonObject payload = devicePayload(name, profileId, a.has("gateway"));
                    JsonObject device = client.request(client.tbUrl + "/api/device", "POST", gson.toJson(payload)).getAsJsonObject();
                    deviceId = device.getAsJsonObject("id").get("id").getAsString();
                    JsonObject credentials = client.request(client.tbUrl + "/api/device/" + TbClient.url(deviceId) + "/credentials",
                            "GET", "").getAsJsonObject();
                    accessToken = credentials.has("credentialsId") ? credentials.get("credentialsId").getAsString() : "";
                    JsonObject attributes = new JsonObject();
                    attributes.addProperty("product_id", productId);
                    attributes.addProperty("device_uuid", deviceId);
                    attributes.addProperty("tsl_version", tslVersion);
                    if (!tenantId.isBlank()) {
                        attributes.addProperty("tenant_id", tenantId);
                    }
                    if (!a.get("site-code", "").isBlank()) {
                        attributes.addProperty("site_code", a.get("site-code", ""));
                    }
                    client.request(client.tbUrl + "/api/plugins/telemetry/DEVICE/" + TbClient.url(deviceId)
                            + "/attributes/SERVER_SCOPE", "POST", gson.toJson(attributes));
                    if (!gatewayId.isBlank()) {
                        JsonObject relation = new JsonObject();
                        relation.add("from", entity("DEVICE", gatewayId));
                        relation.add("to", entity("DEVICE", deviceId));
                        relation.addProperty("type", a.get("relation-type", "Contains"));
                        relation.addProperty("typeGroup", "COMMON");
                        client.request(client.tbUrl + "/api/relation", "POST", gson.toJson(relation));
                    }
                    status = "created";
                    created++;
                }
            } catch (Exception e) {
                status = "failed";
                error = e.getMessage() == null ? e.toString() : e.getMessage();
                failed++;
            }
            csv.append(productId).append(',').append(name).append(',').append(deviceId).append(',')
                    .append(accessToken).append(',').append(tslVersion).append(',').append(profileId).append(',')
                    .append(a.get("site-code", "")).append(',').append(a.has("gateway")).append(',')
                    .append(status).append(',').append(error.replace(",", ";")).append('\n');
        }
        Files.writeString(outputDir.resolve("device-credentials.csv"), csv.toString(), StandardCharsets.UTF_8);
        System.out.println("summary created=" + created + " skipped=" + skipped + " failed=" + failed);
        System.out.println("warning: CSV contains device access tokens; keep it secure");
    }

    static List<String> buildNames(Args a) {
        List<String> names = new ArrayList<>();
        String single = a.get("name", "");
        if (!single.isBlank()) {
            for (String value : single.split(",")) {
                if (!value.isBlank()) {
                    names.add(value.trim());
                }
            }
            return names;
        }
        String prefix = a.get("prefix", "");
        int count = Integer.parseInt(a.get("count", "0"));
        int start = Integer.parseInt(a.get("start-index", "1"));
        if (prefix.isBlank() || count <= 0) {
            throw new IllegalArgumentException("use --name or --prefix with --count");
        }
        for (int i = 0; i < count; i++) {
            names.add(String.format("%s-%04d", prefix.replaceAll("-+$", ""), start + i));
        }
        return names;
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
}
