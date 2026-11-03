package com.iot.thingmodel.tsl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.DoubleNode;
import com.fasterxml.jackson.databind.node.IntNode;
import com.fasterxml.jackson.databind.node.LongNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Component;

@Component
public class TencentTslNormalizer {

    private static final Set<String> NUMERIC_TYPES =
            Set.of("int", "float", "timestamp", "enum");
    private static final Map<String, String> TYPE_MAP =
            Map.of("stringenum", "enum_string");
    private static final Set<String> KNOWN_DEFINE_KEYS = Set.of(
            "type", "min", "max", "start", "step", "unit", "mapping");
    private static final Set<String> FIELD_METADATA_KEYS = Set.of(
            "id", "name", "desc", "required", "specs", "fields", "dataType");
    private static final Set<String> RANGE_KEYS = Set.of("min", "max", "start", "step");

    private final ObjectMapper objectMapper;

    public TencentTslNormalizer(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public boolean isTencentFormat(JsonNode root) {
        if (root == null || !root.isObject()) {
            return false;
        }
        for (JsonNode property : array(root.get("properties"))) {
            if (isTencentDefine(property.get("define"))) {
                return true;
            }
        }
        for (JsonNode event : array(root.get("events"))) {
            for (JsonNode param : array(event.get("params"))) {
                if (isTencentDefine(param.get("define"))) {
                    return true;
                }
            }
        }
        for (JsonNode action : array(root.get("actions"))) {
            for (JsonNode param : array(action.get("input"))) {
                if (isTencentDefine(param.get("define"))) {
                    return true;
                }
            }
            for (JsonNode param : array(action.get("output"))) {
                if (isTencentDefine(param.get("define"))) {
                    return true;
                }
            }
        }
        return false;
    }

    public JsonNode normalize(JsonNode root) {
        if (root == null || !root.isObject()) {
            return root;
        }
        if (!isTencentFormat(root)) {
            return root.deepCopy();
        }
        ObjectNode copy = root.deepCopy();
        normalizeProperties(array(copy.get("properties")));
        normalizeEvents(array(copy.get("events")));
        normalizeActions(array(copy.get("actions")));
        return copy;
    }

    private void normalizeProperties(Iterable<JsonNode> properties) {
        for (JsonNode property : properties) {
            normalizeDefineField(property, "define");
        }
    }

    private void normalizeEvents(Iterable<JsonNode> events) {
        for (JsonNode event : events) {
            for (JsonNode param : array(event.get("params"))) {
                normalizeDefineField(param, "define");
            }
        }
    }

    private void normalizeActions(Iterable<JsonNode> actions) {
        for (JsonNode action : actions) {
            for (JsonNode param : array(action.get("input"))) {
                normalizeDefineField(param, "define");
            }
            for (JsonNode param : array(action.get("output"))) {
                normalizeDefineField(param, "define");
            }
        }
    }

    private void normalizeDefineField(JsonNode owner, String field) {
        if (!(owner instanceof ObjectNode objectNode)) {
            return;
        }
        JsonNode define = objectNode.get(field);
        if (define instanceof ObjectNode defineNode) {
            objectNode.set(field, normalizeDefine(defineNode));
        }
    }

    private ObjectNode normalizeDefine(ObjectNode source) {
        JsonNode actualSource = source;
        if (!source.has("type") && source.get("dataType") instanceof ObjectNode dataType) {
            actualSource = dataType;
        }
        ObjectNode result = objectMapper.createObjectNode();
        copyUnknownFields(actualSource, result);

        String typeName = actualSource.path("type").asText("");
        if (!typeName.isBlank()) {
            result.put("type", TYPE_MAP.getOrDefault(typeName, typeName));
        }

        for (String key : RANGE_KEYS) {
            if (actualSource.has(key)) {
                result.set(key, number(actualSource.get(key)));
            }
        }
        String unit = actualSource.path("unit").asText("");
        if (!unit.isBlank()) {
            result.put("unit", unit);
        }
        if (actualSource.has("mapping")) {
            result.set("mapping", actualSource.get("mapping").deepCopy());
        }

        JsonNode specs = actualSource.has("specs")
                ? actualSource.get("specs") : actualSource.get("fields");
        if (specs != null && !specs.isNull()) {
            result.set("specs", normalizeSpecs(specs));
        }
        return result;
    }

    private JsonNode normalizeSpecs(JsonNode specs) {
        if (specs.isArray()) {
            ObjectNode result = objectMapper.createObjectNode();
            for (JsonNode item : specs) {
                if (!(item instanceof ObjectNode fieldNode)) {
                    continue;
                }
                String id = fieldNode.path("id").asText("");
                if (id.isBlank()) {
                    continue;
                }
                result.set(id, normalizeSpecField(fieldNode));
            }
            return result;
        }
        if (specs.isObject()) {
            ObjectNode result = objectMapper.createObjectNode();
            Iterator<Map.Entry<String, JsonNode>> fields = specs.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> entry = fields.next();
                if (entry.getValue() instanceof ObjectNode fieldNode) {
                    result.set(entry.getKey(), normalizeSpecField(fieldNode));
                } else {
                    result.set(entry.getKey(), entry.getValue().deepCopy());
                }
            }
            return result;
        }
        return specs.deepCopy();
    }

    private ObjectNode normalizeSpecField(ObjectNode field) {
        JsonNode define = field;
        if (!field.has("type") && field.get("dataType") instanceof ObjectNode dataType) {
            define = dataType;
        }
        ObjectNode normalized = normalizeDefine((ObjectNode) define);
        copyFieldMetadata(field, normalized);
        return normalized;
    }

    private void copyFieldMetadata(ObjectNode source, ObjectNode target) {
        for (String key : Set.of("name", "desc", "required")) {
            if (source.has(key) && !source.get(key).asText("").isBlank()) {
                target.set(key, source.get(key).deepCopy());
            }
        }
    }

    private boolean isTencentDefine(JsonNode define) {
        if (define == null || !define.isObject()) {
            return false;
        }
        if ("stringenum".equals(define.path("type").asText())) {
            return true;
        }
        if (define.has("dataType")) {
            return true;
        }
        for (String key : RANGE_KEYS) {
            if (define.has(key) && define.get(key).isTextual()) {
                return true;
            }
        }
        JsonNode specs = define.has("specs") ? define.get("specs") : define.get("fields");
        if (specs == null || specs.isNull()) {
            return false;
        }
        if (specs.isArray()) {
            return true;
        }
        if (specs.isObject()) {
            Iterator<JsonNode> fields = specs.elements();
            while (fields.hasNext()) {
                JsonNode field = fields.next();
                if (field.isObject() && isTencentDefine(field)) {
                    return true;
                }
            }
        }
        return false;
    }

    private void copyUnknownFields(JsonNode source, ObjectNode target) {
        Iterator<Map.Entry<String, JsonNode>> fields = source.fields();
        while (fields.hasNext()) {
            Map.Entry<String, JsonNode> entry = fields.next();
            String key = entry.getKey();
            if (!KNOWN_DEFINE_KEYS.contains(key) && !FIELD_METADATA_KEYS.contains(key)) {
                target.set(key, entry.getValue().deepCopy());
            }
        }
    }

    private JsonNode number(JsonNode value) {
        if (!value.isTextual()) {
            return value.deepCopy();
        }
        String text = value.asText().trim();
        try {
            if (text.contains(".") || text.contains("e") || text.contains("E")) {
                return DoubleNode.valueOf(Double.parseDouble(text));
            }
            long parsed = Long.parseLong(text);
            if (parsed >= Integer.MIN_VALUE && parsed <= Integer.MAX_VALUE) {
                return IntNode.valueOf((int) parsed);
            }
            return LongNode.valueOf(parsed);
        } catch (NumberFormatException ex) {
            return value.deepCopy();
        }
    }

    private Iterable<JsonNode> array(JsonNode node) {
        if (node instanceof ArrayNode arrayNode) {
            return arrayNode;
        }
        return java.util.List.of();
    }
}
