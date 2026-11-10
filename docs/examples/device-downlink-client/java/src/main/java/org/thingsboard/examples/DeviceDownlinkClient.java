package org.thingsboard.examples;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
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
import java.util.Set;
import java.util.HashSet;

/**
 * 设备下行接收示例（Java 版）。
 */
public class DeviceDownlinkClient {

    static final String ATTRIBUTES_TOPIC = "v1/devices/me/attributes";
    static final String RPC_REQUEST_PREFIX = "v1/devices/me/rpc/request/";
    static final String RPC_RESPONSE_TEMPLATE = "v1/devices/me/rpc/response/";

    public static void main(String[] args) throws Exception {
        Args a = new Args(args);
        String host = a.get("mqtt-host", "127.0.0.1");
        int port = Integer.parseInt(a.get("mqtt-port", "1883"));
        String token = a.get("token", "");
        if (token.isBlank()) {
            throw new IllegalArgumentException("--token is required");
        }
        String clientId = a.get("client-id", "device-downlink-client");
        int qos = Integer.parseInt(a.get("qos", "1"));
        int keepalive = Integer.parseInt(a.get("keepalive", "60"));
        Gson gson = new GsonBuilder().create();
        JsonObject config = new JsonObject();
        config.addProperty("reportInterval", 60);
        config.addProperty("alarmThreshold", 80);
        config.addProperty("mode", 0);
        config.addProperty("relay", false);

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
                    merge(config, payload);
                    System.out.println("shared attributes: " + gson.toJson(config));
                    return;
                }
                if (topic.startsWith(RPC_REQUEST_PREFIX)) {
                    String requestId = topic.substring(RPC_REQUEST_PREFIX.length());
                    JsonObject response = handleRpc(config, payload);
                    publish(client, RPC_RESPONSE_TEMPLATE + requestId, gson.toJson(response), qos);
                    System.out.println("rpc " + payload.get("method").getAsString() + " -> " + gson.toJson(response));
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
        System.out.println("waiting for shared attributes or RPC, press Ctrl+C to exit");
        Thread.currentThread().join();
    }

    static JsonObject handleRpc(JsonObject config, JsonObject payload) {
        JsonObject response = new JsonObject();
        String method = payload.has("method") ? payload.get("method").getAsString() : "";
        JsonObject params = payload.has("params") && payload.get("params").isJsonObject()
                ? payload.getAsJsonObject("params") : new JsonObject();
        switch (method) {
            case "set" -> {
                merge(config, params);
                response.addProperty("result", "ok");
                response.add("config", config);
            }
            case "setMode" -> {
                int mode = params.has("mode") ? params.get("mode").getAsInt() : -1;
                if (mode < 0 || mode > 2) {
                    response.addProperty("error", "invalid mode");
                } else {
                    config.addProperty("mode", mode);
                    response.addProperty("result", "ok");
                    response.addProperty("mode", mode);
                }
            }
            case "setRelay" -> {
                if (!params.has("on")) {
                    response.addProperty("error", "invalid relay state");
                } else {
                    boolean on = params.get("on").getAsBoolean();
                    config.addProperty("relay", on);
                    response.addProperty("result", "ok");
                    response.addProperty("relay", on);
                }
            }
            case "applyConfig" -> {
                int interval = params.has("reportInterval") ? params.get("reportInterval").getAsInt() : -1;
                if (interval < 5 || interval > 3600) {
                    response.addProperty("error", "invalid reportInterval");
                } else {
                    config.addProperty("reportInterval", interval);
                    response.addProperty("result", "ok");
                    response.addProperty("reportInterval", interval);
                }
            }
            default -> response.addProperty("error", "unsupported method: " + method);
        }
        return response;
    }

    static void merge(JsonObject target, JsonObject source) {
        for (String key : source.keySet()) {
            target.add(key, source.get(key));
        }
    }

    static void publish(MqttClient client, String topic, String payload, int qos) throws Exception {
        MqttMessage message = new MqttMessage(payload.getBytes(StandardCharsets.UTF_8));
        message.setQos(qos);
        client.publish(topic, message);
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
