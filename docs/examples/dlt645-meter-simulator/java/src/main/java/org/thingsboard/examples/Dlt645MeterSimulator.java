package org.thingsboard.examples;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken;
import org.eclipse.paho.client.mqttv3.MqttCallback;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;

import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.HashSet;

/**
 * DLT645 电表 MQTT 模拟器（Java 版）。
 */
public class Dlt645MeterSimulator {

    static final String TELEMETRY_TOPIC = "v1/devices/me/telemetry";
    static final String ATTRIBUTES_TOPIC = "v1/devices/me/attributes";
    static final String RPC_REQUEST_PREFIX = "v1/devices/me/rpc/request/";
    static final String RPC_RESPONSE_PREFIX = "v1/devices/me/rpc/response/";

    static double ua = 220, ub = 220, uc = 220;
    static double ia = 5, ib = 5, ic = 5;
    static double pf = 0.95, freq = 50;
    static double forward = 0, reverse = 0;
    static boolean relay = true;
    static int reportInterval = 5;

    public static void main(String[] args) throws Exception {
        Args a = new Args(args);
        String host = a.get("mqtt-host", "127.0.0.1");
        int port = Integer.parseInt(a.get("mqtt-port", "1883"));
        String token = a.get("token", "");
        if (token.isBlank()) {
            throw new IllegalArgumentException("--token is required");
        }
        String clientId = a.get("client-id", "meter-java");
        int qos = Integer.parseInt(a.get("qos", "1"));
        int keepalive = Integer.parseInt(a.get("keepalive", "60"));
        double interval = Double.parseDouble(a.get("interval", "5"));
        double eventInterval = Double.parseDouble(a.get("event-interval", "30"));
        int count = Integer.parseInt(a.get("count", "0"));
        relay = !a.has("relay-off");
        Random rng = new Random(Long.parseLong(a.get("seed", String.valueOf(System.currentTimeMillis()))));
        Gson gson = new GsonBuilder().create();

        MqttClient client = new MqttClient("tcp://" + host + ":" + port, clientId, new MemoryPersistence());
        MqttConnectOptions options = new MqttConnectOptions();
        options.setUserName(token);
        options.setPassword("".toCharArray());
        options.setCleanSession(true);
        options.setKeepAliveInterval(keepalive);
        options.setAutomaticReconnect(true);
        client.setCallback(new MqttCallback() {
            @Override
            public void connectionLost(Throwable cause) {
                System.err.println("MQTT disconnected: " + cause);
            }

            @Override
            public void messageArrived(String topic, MqttMessage message) throws Exception {
                JsonObject payload = JsonParser.parseString(
                        new String(message.getPayload(), StandardCharsets.UTF_8)).getAsJsonObject();
                if (ATTRIBUTES_TOPIC.equals(topic)) {
                    applyShared(payload);
                    System.out.println("shared attributes: " + gson.toJson(payload));
                    publishTelemetry(client, gson, qos);
                    return;
                }
                if (topic.startsWith(RPC_REQUEST_PREFIX)) {
                    String requestId = topic.substring(RPC_REQUEST_PREFIX.length());
                    JsonObject response = handleRpc(payload);
                    publish(client, RPC_RESPONSE_PREFIX + requestId, gson.toJson(response), qos);
                    System.out.println("rpc " + payload.get("method").getAsString() + " -> " + gson.toJson(response));
                    if (response.has("success") && response.get("success").getAsBoolean()) {
                        publishTelemetry(client, gson, qos);
                    }
                }
            }

            @Override
            public void deliveryComplete(IMqttDeliveryToken token) {
            }
        });

        client.connect(options);
        client.subscribe(ATTRIBUTES_TOPIC, qos);
        client.subscribe(RPC_REQUEST_PREFIX + "+", qos);
        System.out.println("connected host=" + host + ":" + port + " clientId=" + clientId);
        System.out.println("subscribed " + ATTRIBUTES_TOPIC + ", " + RPC_REQUEST_PREFIX + "+");

        int iterations = 0;
        long lastEvent = System.currentTimeMillis();
        try {
            while (count <= 0 || iterations < count) {
                advance(interval, rng);
                publishTelemetry(client, gson, qos);
                iterations++;
                if (eventInterval > 0 && System.currentTimeMillis() - lastEvent >= eventInterval * 1000) {
                    publishEvent(client, gson, qos, rng);
                    lastEvent = System.currentTimeMillis();
                }
                if (count > 0 && iterations >= count) {
                    break;
                }
                Thread.sleep((long) (interval * 1000));
            }
        } finally {
            client.disconnect();
            client.close();
            System.out.println("summary telemetry=" + iterations);
        }
    }

    static void advance(double seconds, Random rng) {
        ua = clamp(ua + rng.nextDouble() * 3 - 1.5, 0, 300);
        ub = clamp(ub + rng.nextDouble() * 3 - 1.5, 0, 300);
        uc = clamp(uc + rng.nextDouble() * 3 - 1.5, 0, 300);
        double target = relay ? 5.0 : 0.0;
        ia = clamp(ia + (target - ia) * 0.35 + rng.nextDouble() * 0.4 - 0.2, 0, 100);
        ib = clamp(ib + (target - ib) * 0.35 + rng.nextDouble() * 0.4 - 0.2, 0, 100);
        ic = clamp(ic + (target - ic) * 0.35 + rng.nextDouble() * 0.4 - 0.2, 0, 100);
        pf = clamp(pf + rng.nextDouble() * 0.02 - 0.01, 0, 1);
        freq = clamp(freq + rng.nextDouble() * 0.1 - 0.05, 45, 65);
        double s = Math.sqrt(3) * ((ua + ub + uc) / 3) * ((ia + ib + ic) / 3) / 1000;
        double hours = Math.max(0, seconds) / 3600;
        forward = clamp(forward + s * pf * hours, 0, 99999999);
        reverse = clamp(reverse + s * pf * 0.01 * hours, 0, 99999999);
    }

    static void publishTelemetry(MqttClient client, Gson gson, int qos) throws Exception {
        JsonObject values = new JsonObject();
        JsonObject info = new JsonObject();
        info.addProperty("model", "DTZ341");
        info.addProperty("meterNo", "000000000001");
        info.addProperty("protocolVersion", "DL/T 645-2007");
        values.add("meterInfo", info);
        values.addProperty("UA_V", round(ua, 2));
        values.addProperty("UB_V", round(ub, 2));
        values.addProperty("UC_V", round(uc, 2));
        values.addProperty("IA_A", round(ia, 2));
        values.addProperty("IB_A", round(ib, 2));
        values.addProperty("IC_A", round(ic, 2));
        values.addProperty("PF", round(pf, 3));
        values.addProperty("F_Hz", round(freq, 2));
        values.addProperty("forwardActiveEnergy_kWh", round(forward, 3));
        values.addProperty("reverseActiveEnergy_kWh", round(reverse, 3));
        values.addProperty("relayState", relay);
        values.addProperty("reportInterval", reportInterval);
        values.addProperty("lastReadTime", System.currentTimeMillis());
        publish(client, TELEMETRY_TOPIC, gson.toJson(values), qos);
        System.out.println("[telemetry] " + gson.toJson(values));
    }

    static void publishEvent(MqttClient client, Gson gson, int qos, Random rng) throws Exception {
        JsonObject event = new JsonObject();
        event.addProperty("event_id", "overVoltage");
        event.addProperty("event_type", "alert");
        event.addProperty("event_ts", System.currentTimeMillis());
        event.addProperty("phase", "A");
        event.addProperty("voltage", round(230 + rng.nextDouble() * 20, 2));
        event.addProperty("threshold", 230.0);
        JsonArray events = new JsonArray();
        events.add(event);
        JsonObject payload = new JsonObject();
        payload.add("events", events);
        publish(client, TELEMETRY_TOPIC, gson.toJson(payload), qos);
        System.out.println("[event] " + gson.toJson(event));
    }

    static void applyShared(JsonObject attributes) {
        if (attributes.has("reportInterval")) {
            int value = attributes.get("reportInterval").getAsInt();
            reportInterval = Math.max(5, Math.min(3600, value));
        }
        if (attributes.has("relay")) {
            relay = attributes.get("relay").getAsBoolean();
        }
        if (attributes.has("relayState")) {
            relay = attributes.get("relayState").getAsBoolean();
        }
    }

    static JsonObject handleRpc(JsonObject payload) {
        JsonObject response = new JsonObject();
        String method = payload.has("method") ? payload.get("method").getAsString() : "";
        JsonObject params = payload.has("params") && payload.get("params").isJsonObject()
                ? payload.getAsJsonObject("params") : new JsonObject();
        switch (method) {
            case "set" -> {
                applyShared(params);
                response.addProperty("success", true);
            }
            case "setRelay" -> {
                if (!params.has("on")) {
                    response.addProperty("success", false);
                    response.addProperty("error", "invalid relay state");
                } else {
                    relay = params.get("on").getAsBoolean();
                    response.addProperty("success", true);
                }
            }
            case "applyConfig" -> {
                if (!params.has("reportInterval")) {
                    response.addProperty("success", false);
                    response.addProperty("error", "invalid reportInterval");
                } else {
                    int value = params.get("reportInterval").getAsInt();
                    if (value < 5 || value > 3600) {
                        response.addProperty("success", false);
                        response.addProperty("error", "invalid reportInterval");
                    } else {
                        reportInterval = value;
                        response.addProperty("success", true);
                    }
                }
            }
            case "syncTime" -> response.addProperty("success", true);
            default -> {
                response.addProperty("success", false);
                response.addProperty("error", "unsupported method: " + method);
            }
        }
        return response;
    }

    static void publish(MqttClient client, String topic, String payload, int qos) throws Exception {
        MqttMessage message = new MqttMessage(payload.getBytes(StandardCharsets.UTF_8));
        message.setQos(qos);
        client.publish(topic, message);
    }

    static double clamp(double value, double min, double max) {
        return Math.max(min, Math.min(max, value));
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
