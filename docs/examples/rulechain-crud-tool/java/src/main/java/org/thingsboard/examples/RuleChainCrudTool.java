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
 * 规则链增删改查与导入导出工具（Java 版）。
 */
public class RuleChainCrudTool {

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
            case "list" -> {
                String url = client.tbUrl + "/api/ruleChains?pageSize=" + a.get("page-size", "100")
                        + "&page=" + a.get("page", "0") + "&type=" + a.get("rule-chain-type", "CORE");
                print(client, gson, dryRun, url, "GET", null);
            }
            case "create" -> {
                String name = require(a, "name");
                JsonObject payload = new JsonObject();
                payload.addProperty("name", name);
                payload.addProperty("type", a.get("rule-chain-type", "CORE"));
                payload.addProperty("debugMode", a.has("debug-mode"));
                if (!a.get("description", "").isBlank()) {
                    JsonObject additional = new JsonObject();
                    additional.addProperty("description", a.get("description", ""));
                    payload.add("additionalInfo", additional);
                }
                print(client, gson, dryRun, client.tbUrl + "/api/ruleChain", "POST", gson.toJson(payload));
            }
            case "get", "delete", "set-root", "metadata", "update" -> {
                String id = require(a, "rule-chain-id");
                String encoded = TbClient.url(id);
                switch (action) {
                    case "get" -> print(client, gson, dryRun, client.tbUrl + "/api/ruleChain/" + encoded, "GET", null);
                    case "delete" -> print(client, gson, dryRun, client.tbUrl + "/api/ruleChain/" + encoded, "DELETE", null);
                    case "set-root" -> print(client, gson, dryRun, client.tbUrl + "/api/ruleChain/" + encoded + "/root", "POST", null);
                    case "metadata" -> {
                        String input = a.get("input", "");
                        if (input.isBlank()) {
                            print(client, gson, dryRun, client.tbUrl + "/api/ruleChain/" + encoded + "/metadata", "GET", null);
                        } else {
                            JsonObject metadata = JsonParser.parseString(
                                    Files.readString(Path.of(input), StandardCharsets.UTF_8)).getAsJsonObject();
                            if (!metadata.has("ruleChainId")) {
                                JsonObject chainId = new JsonObject();
                                chainId.addProperty("entityType", "RULE_CHAIN");
                                chainId.addProperty("id", id);
                                metadata.add("ruleChainId", chainId);
                            }
                            print(client, gson, dryRun, client.tbUrl + "/api/ruleChain/metadata", "POST", gson.toJson(metadata));
                        }
                    }
                    case "update" -> {
                        JsonObject current = dryRun ? new JsonObject()
                                : client.request(client.tbUrl + "/api/ruleChain/" + encoded, "GET", "").getAsJsonObject();
                        if (!a.get("name", "").isBlank()) {
                            current.addProperty("name", a.get("name", ""));
                        }
                        if (!a.get("description", "").isBlank()) {
                            JsonObject additional = current.has("additionalInfo") && current.get("additionalInfo").isJsonObject()
                                    ? current.getAsJsonObject("additionalInfo") : new JsonObject();
                            additional.addProperty("description", a.get("description", ""));
                            current.add("additionalInfo", additional);
                        }
                        if (a.has("debug-mode")) {
                            current.addProperty("debugMode", true);
                        }
                        print(client, gson, dryRun, client.tbUrl + "/api/ruleChain", "POST", gson.toJson(current));
                    }
                    default -> throw new IllegalArgumentException("unsupported action: " + action);
                }
            }
            case "export" -> export(client, a, gson, dryRun);
            case "import" -> importChain(client, a, gson, dryRun);
            default -> throw new IllegalArgumentException("unsupported action: " + action);
        }
    }

    static void export(TbClient client, Args a, Gson gson, boolean dryRun) throws Exception {
        String id = require(a, "rule-chain-id");
        if (dryRun) {
            System.out.println("[dry-run] export " + id);
            return;
        }
        String encoded = TbClient.url(id);
        JsonObject bundle = new JsonObject();
        bundle.add("ruleChain", client.request(client.tbUrl + "/api/ruleChain/" + encoded, "GET", ""));
        bundle.add("metadata", client.request(client.tbUrl + "/api/ruleChain/" + encoded + "/metadata", "GET", ""));
        Path output = Path.of(a.get("output", id + ".rule-chain.json"));
        Files.writeString(output, gson.toJson(bundle), StandardCharsets.UTF_8);
        System.out.println("exported " + output);
    }

    static void importChain(TbClient client, Args a, Gson gson, boolean dryRun) throws Exception {
        String input = require(a, "input");
        JsonObject bundle = JsonParser.parseString(Files.readString(Path.of(input), StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject chain = bundle.getAsJsonObject("ruleChain").deepCopy();
        for (String key : new String[]{"id", "createdTime", "tenantId", "version"}) {
            chain.remove(key);
        }
        if (!a.get("name", "").isBlank()) {
            chain.addProperty("name", a.get("name", ""));
        }
        if (dryRun) {
            System.out.println("[dry-run] import " + gson.toJson(chain));
            return;
        }
        JsonObject saved = client.request(client.tbUrl + "/api/ruleChain", "POST", gson.toJson(chain)).getAsJsonObject();
        JsonObject savedId = saved.getAsJsonObject("id");
        JsonObject metadata = bundle.has("metadata") && bundle.get("metadata").isJsonObject()
                ? bundle.getAsJsonObject("metadata").deepCopy() : new JsonObject();
        metadata.remove("ruleChainId");
        metadata.add("ruleChainId", savedId);
        client.request(client.tbUrl + "/api/ruleChain/metadata", "POST", gson.toJson(metadata));
        System.out.println("imported " + savedId.get("id").getAsString() + " (" + saved.get("name").getAsString() + ")");
    }

    static void print(TbClient client, Gson gson, boolean dryRun, String url, String method, String body) throws Exception {
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
