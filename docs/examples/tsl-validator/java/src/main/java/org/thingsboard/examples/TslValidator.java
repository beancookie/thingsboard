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
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * 物模型 TSL 校验工具（Java 版）。
 */
public class TslValidator {

    static final Pattern ID_PATTERN = Pattern.compile("^[A-Za-z_][A-Za-z0-9_]{0,49}$");
    static final Set<String> TYPES = Set.of("int", "float", "bool", "string", "enum", "enum_string", "timestamp", "struct");
    static final Set<String> EVENT_TYPES = Set.of("info", "alert", "fault");
    static final Set<String> RESERVED = Set.of("ts", "event_id", "event_type", "event_ts");
    static final int MAX_FEATURES = 100;

    static final class Issue {
        final String level;
        final String path;
        final String message;

        Issue(String level, String path, String message) {
            this.level = level;
            this.path = path;
            this.message = message;
        }
    }

    public static void main(String[] args) throws Exception {
        Args a = new Args(args);
        List<Path> files = new ArrayList<>();
        String tsl = a.get("tsl", "");
        for (String value : tsl.split(",")) {
            if (!value.isBlank()) {
                files.add(Path.of(value.trim()));
            }
        }
        String dir = a.get("dir", "");
        if (!dir.isBlank()) {
            Path directory = Path.of(dir);
            if (!Files.isDirectory(directory)) {
                throw new IllegalArgumentException("directory not found: " + dir);
            }
            try (var stream = Files.list(directory)) {
                stream.filter(p -> p.getFileName().toString().endsWith(".json")).sorted().forEach(files::add);
            }
        }
        if (files.isEmpty()) {
            throw new IllegalArgumentException("use --tsl or --dir");
        }
        boolean strict = a.has("strict");
        JsonArray report = new JsonArray();
        int failed = 0;
        for (Path file : files) {
            List<Issue> issues = validate(file);
            boolean valid = issues.stream().noneMatch(i -> "error".equals(i.level))
                    && !(strict && issues.stream().anyMatch(i -> "warning".equals(i.level)));
            System.out.println((valid ? "[OK] " : "[FAIL] ") + file
                    + " errors=" + issues.stream().filter(i -> "error".equals(i.level)).count()
                    + " warnings=" + issues.stream().filter(i -> "warning".equals(i.level)).count());
            JsonObject fileReport = new JsonObject();
            fileReport.addProperty("path", file.toString());
            fileReport.addProperty("valid", valid);
            JsonArray errors = new JsonArray();
            JsonArray warnings = new JsonArray();
            for (Issue issue : issues) {
                JsonObject item = new JsonObject();
                item.addProperty("path", issue.path);
                item.addProperty("message", issue.message);
                if ("error".equals(issue.level)) {
                    errors.add(item);
                    System.out.println("  error " + issue.path + ": " + issue.message);
                } else {
                    warnings.add(item);
                    System.out.println("  warning " + issue.path + ": " + issue.message);
                }
            }
            fileReport.add("errors", errors);
            fileReport.add("warnings", warnings);
            report.add(fileReport);
            if (!valid) {
                failed++;
            }
        }
        if (!a.get("report", "").isBlank()) {
            Path reportPath = Path.of(a.get("report", ""));
            if (reportPath.getParent() != null) {
                Files.createDirectories(reportPath.getParent());
            }
            Files.writeString(reportPath, new GsonBuilder().setPrettyPrinting().create().toJson(report), StandardCharsets.UTF_8);
            System.out.println("report: " + reportPath);
        }
        System.out.println("summary files=" + files.size() + " passed=" + (files.size() - failed) + " failed=" + failed);
        if (failed > 0) {
            System.exit(1);
        }
    }

    static List<Issue> validate(Path file) throws Exception {
        List<Issue> issues = new ArrayList<>();
        JsonElement root;
        try {
            root = JsonParser.parseString(Files.readString(file, StandardCharsets.UTF_8));
        } catch (Exception e) {
            issues.add(new Issue("error", "$", "JSON parse failed: " + e.getMessage()));
            return issues;
        }
        if (!root.isJsonObject()) {
            issues.add(new Issue("error", "$", "TSL root must be an object"));
            return issues;
        }
        JsonObject tsl = root.getAsJsonObject();
        if (!tsl.has("version") || tsl.get("version").getAsString().isBlank()) {
            issues.add(new Issue("error", "$.version", "version is required"));
        }
        JsonObject profile = tsl.has("profile") && tsl.get("profile").isJsonObject()
                ? tsl.getAsJsonObject("profile") : null;
        if (profile == null || (!profile.has("ProductId") && !profile.has("productId"))) {
            issues.add(new Issue("error", "$.profile", "profile.ProductId is required"));
        }
        JsonArray properties = array(tsl, "properties", issues, true);
        JsonArray events = array(tsl, "events", issues, false);
        JsonArray actions = array(tsl, "actions", issues, false);
        validateFeatures(properties, "properties", "property", issues, true);
        validateFeatures(events, "events", "event", issues, false);
        validateFeatures(actions, "actions", "action", issues, false);
        if (properties.size() + events.size() + actions.size() > MAX_FEATURES) {
            issues.add(new Issue("error", "$", "total features exceed " + MAX_FEATURES));
        }
        return issues;
    }

    static JsonArray array(JsonObject object, String key, List<Issue> issues, boolean required) {
        if (!object.has(key)) {
            if (required) {
                issues.add(new Issue("error", "$", key + " is required"));
            }
            return new JsonArray();
        }
        if (!object.get(key).isJsonArray()) {
            issues.add(new Issue("error", "$." + key, key + " must be an array"));
            return new JsonArray();
        }
        return object.getAsJsonArray(key);
    }

    static void validateFeatures(JsonArray features, String key, String label, List<Issue> issues, boolean property) {
        Set<String> ids = new HashSet<>();
        for (int i = 0; i < features.size(); i++) {
            JsonObject feature = features.get(i).getAsJsonObject();
            String path = "$." + key + "[" + i + "]";
            String id = string(feature, "id");
            if (id.isBlank()) {
                issues.add(new Issue("error", path, label + " id is required"));
            } else {
                if (!ID_PATTERN.matcher(id).matches()) {
                    issues.add(new Issue("error", path, "invalid id: " + id));
                }
                if (!ids.add(id)) {
                    issues.add(new Issue("error", path, "duplicate id: " + id));
                }
                if (property && RESERVED.contains(id)) {
                    issues.add(new Issue("warning", path, "reserved id: " + id));
                }
            }
            if (property) {
                if (!"r".equals(string(feature, "mode")) && !"rw".equals(string(feature, "mode"))) {
                    issues.add(new Issue("error", path, "mode must be r or rw"));
                }
                validateDefine(feature.getAsJsonObject("define"), path + ".define", issues, true);
            } else if ("events".equals(key)) {
                if (!EVENT_TYPES.contains(string(feature, "type"))) {
                    issues.add(new Issue("error", path, "event type must be info/alert/fault"));
                }
                validateParams(feature, "params", path + ".params", issues, false);
            } else {
                validateParams(feature, "input", path + ".input", issues, true);
                validateParams(feature, "output", path + ".output", issues, true);
            }
        }
    }

    static void validateParams(JsonObject feature, String key, String path, List<Issue> issues, boolean allowStruct) {
        if (!feature.has(key)) {
            return;
        }
        if (!feature.get(key).isJsonArray()) {
            issues.add(new Issue("error", path, "must be an array"));
            return;
        }
        JsonArray params = feature.getAsJsonArray(key);
        Set<String> ids = new HashSet<>();
        for (int i = 0; i < params.size(); i++) {
            JsonObject param = params.get(i).getAsJsonObject();
            String id = string(param, "id");
            if (id.isBlank() || !ID_PATTERN.matcher(id).matches()) {
                issues.add(new Issue("error", path + "[" + i + "]", "invalid param id"));
            } else if (!ids.add(id)) {
                issues.add(new Issue("error", path + "[" + i + "]", "duplicate param id: " + id));
            }
            validateDefine(param.getAsJsonObject("define"), path + "[" + i + "].define", issues, allowStruct);
        }
    }

    static void validateDefine(JsonObject define, String path, List<Issue> issues, boolean allowStruct) {
        if (define == null) {
            issues.add(new Issue("error", path, "define is required"));
            return;
        }
        String type = string(define, "type");
        if (!TYPES.contains(type)) {
            issues.add(new Issue("error", path, "unsupported type: " + type));
            return;
        }
        if ("struct".equals(type)) {
            if (!allowStruct) {
                issues.add(new Issue("error", path, "struct is not allowed here"));
                return;
            }
            if (!define.has("specs") || !define.get("specs").isJsonObject() || define.getAsJsonObject("specs").size() == 0) {
                issues.add(new Issue("error", path, "specs is required"));
            }
            return;
        }
        if ("int".equals(type) || "float".equals(type)) {
            double min = number(define, "min");
            double max = number(define, "max");
            double start = number(define, "start");
            double step = number(define, "step");
            if (min > max) {
                issues.add(new Issue("error", path, "min is greater than max"));
            }
            if (start < min || start > max) {
                issues.add(new Issue("error", path, "start is out of range"));
            }
            if (step < 0) {
                issues.add(new Issue("error", path, "step must be >= 0"));
            }
            if ("int".equals(type) && (min < Integer.MIN_VALUE || max > Integer.MAX_VALUE)) {
                issues.add(new Issue("error", path, "int range exceeds int32"));
            }
        }
        if ("enum".equals(type) || "enum_string".equals(type)) {
            JsonObject mapping = define.has("mapping") && define.get("mapping").isJsonObject()
                    ? define.getAsJsonObject("mapping") : null;
            if (mapping == null || mapping.size() < 2) {
                issues.add(new Issue("error", path, "mapping must contain at least 2 entries"));
            }
        }
    }

    static String string(JsonObject object, String key) {
        return object.has(key) && object.get(key).isJsonPrimitive() ? object.get(key).getAsString() : "";
    }

    static double number(JsonObject object, String key) {
        return object.has(key) && object.get(key).isJsonPrimitive() ? object.get(key).getAsDouble() : 0;
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
