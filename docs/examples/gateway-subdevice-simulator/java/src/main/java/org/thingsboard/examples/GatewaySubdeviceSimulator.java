package org.thingsboard.examples;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.HashSet;

/**
 * 网关子设备 MQTT 模拟器（Java 版）。
 */
public class GatewaySubdeviceSimulator {

    static final String CONNECT_TOPIC = "v1/gateway/connect";
    static final String DISCONNECT_TOPIC = "v1/gateway/disconnect";
    static final String TELEMETRY_TOPIC = "v1/gateway/telemetry";
    static final String ATTRIBUTES_TOPIC = "v1/gateway/attributes";

    public static void main(String[] args) throws Exception {
        Args a = new Args(args);
        String host = a.get("mqtt-host", "127.0.0.1");
        int port = Integer.parseInt(a.get("mqtt-port", "1883"));
        String token = a.get("gateway-token", "");
        if (token.isBlank()) {
            throw new IllegalArgumentException("--gateway-token is required");
        }
        String gatewayName = a.get("gateway-name", "gateway-01");
        String deviceType = a.get("device-type", "default");
        int qos = Integer.parseInt(a.get("qos", "1"));
        int keepalive = Integer.parseInt(a.get("keepalive", "60"));
        int count = Integer.parseInt(a.get("count", "0"));
        double interval = Double.parseDouble(a.get("interval", "5"));
        boolean publishAttributes = a.has("publish-attributes");
        List<String> names = new ArrayList<>();
        String subDevices = a.get("sub-device", "");
        for (String name : subDevices.split(",")) {
            if (!name.isBlank()) {
                names.add(name.trim());
            }
        }
        if (names.isEmpty()) {
            throw new IllegalArgumentException("--sub-device is required (comma separated)");
        }
        Random rng = new Random();
        Gson gson = new GsonBuilder().create();

        MqttClient client = new MqttClient("tcp://" + host + ":" + port, gatewayName, new MemoryPersistence());
        MqttConnectOptions options = new MqttConnectOptions();
        options.setUserName(token);
        options.setPassword("".toCharArray());
        options.setCleanSession(true);
        options.setKeepAliveInterval(keepalive);
        options.setAutomaticReconnect(true);
        client.connect(options);
        System.out.println("connected gateway=" + gatewayName + " host=" + host + ":" + port);

        for (String name : names) {
            JsonObject connect = new JsonObject();
            connect.addProperty("device", name);
            connect.addProperty("type", deviceType);
            publish(client, CONNECT_TOPIC, gson.toJson(connect), qos);
            System.out.println("connected sub-device " + name);
            if (publishAttributes) {
                JsonObject attrs = new JsonObject();
                JsonObject values = new JsonObject();
                values.addProperty("device_type", deviceType);
                values.addProperty("gateway", true);
                values.addProperty("status", "online");
                attrs.add(name, values);
                publish(client, ATTRIBUTES_TOPIC, gson.toJson(attrs), qos);
            }
        }

        int iterations = 0;
        try {
            while (count <= 0 || iterations < count) {
                JsonObject telemetry = new JsonObject();
                long ts = System.currentTimeMillis();
                for (String name : names) {
                    JsonObject values = new JsonObject();
                    values.addProperty("temperature", round(20 + rng.nextDouble() * 10, 1));
                    values.addProperty("humidity", round(40 + rng.nextDouble() * 30, 1));
                    values.addProperty("voltage", round(215 + rng.nextDouble() * 10, 1));
                    values.addProperty("current", round(1 + rng.nextDouble() * 9, 2));
                    values.addProperty("status", "online");
                    JsonObject point = new JsonObject();
                    point.addProperty("ts", ts);
                    point.add("values", values);
                    com.google.gson.JsonArray points = new com.google.gson.JsonArray();
                    points.add(point);
                    telemetry.add(name, points);
                }
                publish(client, TELEMETRY_TOPIC, gson.toJson(telemetry), qos);
                System.out.println("telemetry " + gson.toJson(telemetry));
                iterations++;
                if (count > 0 && iterations >= count) {
                    break;
                }
                Thread.sleep((long) (interval * 1000));
            }
        } finally {
            for (String name : names) {
                JsonObject disconnect = new JsonObject();
                disconnect.addProperty("device", name);
                publish(client, DISCONNECT_TOPIC, gson.toJson(disconnect), qos);
                System.out.println("disconnected sub-device " + name);
            }
            client.disconnect();
            client.close();
            System.out.println("summary devices=" + names.size() + " packets=" + iterations);
        }
    }

    static void publish(MqttClient client, String topic, String payload, int qos) throws Exception {
        MqttMessage message = new MqttMessage(payload.getBytes(StandardCharsets.UTF_8));
        message.setQos(qos);
        client.publish(topic, message);
    }

    static double round(double value, int digits) {
        double scale = Math.pow(10, digits);
        return Math.round(value * scale) / scale;
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
