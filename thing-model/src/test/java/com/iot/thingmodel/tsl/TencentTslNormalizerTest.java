package com.iot.thingmodel.tsl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TencentTslNormalizerTest {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final TencentTslNormalizer normalizer = new TencentTslNormalizer(objectMapper);

    @Test
    void normalizesTencentSampleToCanonicalTsl() throws Exception {
        JsonNode source = load("4DZDCQUA2D.json");
        JsonNode expected = load("4DZDCQUA2D.tsl.json");

        assertTrue(normalizer.isTencentFormat(source));
        assertFalse(normalizer.isTencentFormat(expected));
        assertEquals(expected, normalizer.normalize(source));
    }

    @Test
    void leavesCanonicalTslUnchanged() throws Exception {
        JsonNode expected = load("4DZDCQUA2D.tsl.json");

        assertEquals(expected, normalizer.normalize(expected));
    }

    @Test
    void normalizesLegacyStructAndStringEnum() throws Exception {
        JsonNode source = objectMapper.readTree("""
                {
                  "version": "1.0",
                  "profile": {"ProductId": "P1", "CategoryId": "1"},
                  "properties": [{
                    "id": "info",
                    "name": "Info",
                    "mode": "r",
                    "define": {
                      "type": "struct",
                      "specs": [{
                        "id": "state",
                        "name": "State",
                        "dataType": {
                          "type": "stringenum",
                          "mapping": {"on": "On", "off": "Off"}
                        }
                      }]
                    }
                  }],
                  "events": [],
                  "actions": []
                }
                """);

        JsonNode normalized = normalizer.normalize(source);
        JsonNode state = normalized.path("properties").get(0)
                .path("define").path("specs").path("state");

        assertEquals("enum_string", state.path("type").asText());
        assertEquals("State", state.path("name").asText());
        assertEquals("On", state.path("mapping").path("on").asText());
    }

    @Test
    void normalizesTextRanges() throws Exception {
        JsonNode source = objectMapper.readTree("""
                {
                  "version": "1.0",
                  "profile": {"ProductId": "P1"},
                  "properties": [{
                    "id": "speed",
                    "name": "Speed",
                    "mode": "r",
                    "define": {
                      "type": "float",
                      "min": "0",
                      "max": "100.5",
                      "start": "0",
                      "step": "0.01"
                    }
                  }]
                }
                """);

        JsonNode define = normalizer.normalize(source)
                .path("properties").get(0).path("define");

        assertEquals(0, define.path("min").asInt());
        assertEquals(100.5, define.path("max").asDouble());
        assertEquals(0.01, define.path("step").asDouble());
    }

    private JsonNode load(String name) throws Exception {
        Path path = Path.of("migrate", name);
        if (!Files.exists(path)) {
            path = Path.of("thing-model", "migrate", name);
        }
        return objectMapper.readTree(path.toFile());
    }
}
