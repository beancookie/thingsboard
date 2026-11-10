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
 * 租户初始化工具（Java 版）。
 */
public class TenantProvisioner {

    public static void main(String[] args) throws Exception {
        Args a = new Args(args);
        String action = a.get("action", "");
        TbClient client = new TbClient(
                a.get("tb-url", "http://localhost:8080"),
                a.get("thingmodel-url", "http://localhost:8080/api/thing-model"));
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        boolean dryRun = a.has("dry-run");
        if (!dryRun) {
            client.authenticate(a.get("api-key", ""), a.get("username", "sysadmin@thingsboard.org"), a.get("password", ""));
        }

        switch (action) {
            case "list" -> print(client, gson, dryRun,
                    client.tbUrl + "/api/tenants?pageSize=100&page=0", "GET", null);
            case "get" -> {
                String id = require(a, "tenant-id");
                print(client, gson, dryRun,
                        client.tbUrl + "/api/tenant/" + TbClient.url(id), "GET", null);
            }
            case "create" -> {
                String name = require(a, "tenant-name");
                String profileId = a.get("profile-id", "");
                if (profileId.isBlank()) {
                    profileId = dryRun ? "<TENANT_PROFILE_ID>" : defaultProfileId(client, gson);
                }
                JsonObject payload = new JsonObject();
                payload.addProperty("title", name);
                JsonObject profile = new JsonObject();
                profile.addProperty("entityType", "TENANT_PROFILE");
                profile.addProperty("id", profileId);
                payload.add("tenantProfileId", profile);
                putIfPresent(payload, "email", a.get("email", ""));
                putIfPresent(payload, "country", a.get("country", ""));
                putIfPresent(payload, "city", a.get("city", ""));
                putIfPresent(payload, "phone", a.get("phone", ""));
                putIfPresent(payload, "description", a.get("description", ""));
                print(client, gson, dryRun,
                        client.tbUrl + "/api/tenant", "POST", gson.toJson(payload));
            }
            case "create-admin" -> {
                String tenantId = require(a, "tenant-id");
                String email = require(a, "email");
                JsonObject payload = new JsonObject();
                JsonObject tenant = new JsonObject();
                tenant.addProperty("entityType", "TENANT");
                tenant.addProperty("id", tenantId);
                payload.add("tenantId", tenant);
                payload.addProperty("email", email);
                payload.addProperty("firstName", a.get("first-name", "Tenant"));
                payload.addProperty("lastName", a.get("last-name", "Admin"));
                payload.addProperty("authority", "TENANT_ADMIN");
                String url = client.tbUrl + "/api/user?sendActivationMail="
                        + a.has("send-activation-mail");
                print(client, gson, dryRun, url, "POST", gson.toJson(payload));
            }
            case "provision" -> {
                String tenantId = require(a, "tenant-id");
                String base = client.thingmodelUrl.endsWith("/api/thing-model")
                        ? client.thingmodelUrl : client.thingmodelUrl + "/api/thing-model";
                String url = base + "/admin/tenants/" + TbClient.url(tenantId)
                        + "/provision-auto?force=" + a.has("force");
                print(client, gson, dryRun, url, "POST", null);
            }
            case "delete" -> {
                String id = require(a, "tenant-id");
                print(client, gson, dryRun,
                        client.tbUrl + "/api/tenant/" + TbClient.url(id), "DELETE", null);
            }
            default -> throw new IllegalArgumentException("unsupported action: " + action);
        }
    }

    static String defaultProfileId(TbClient client, Gson gson) throws Exception {
        JsonElement data = client.request(
                client.tbUrl + "/api/tenantProfileInfo/default", "GET", "");
        JsonObject profile = data.getAsJsonObject().getAsJsonObject("id");
        if (profile == null || !profile.has("id")) {
            throw new IllegalStateException("default tenant profile not found");
        }
        return profile.get("id").getAsString();
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
