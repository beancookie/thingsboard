package org.thingsboard.examples;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.eclipse.californium.core.CoapClient;
import org.eclipse.californium.core.CoapHandler;
import org.eclipse.californium.core.CoapObserveRelation;
import org.eclipse.californium.core.CoapResponse;
import org.eclipse.californium.core.coap.MediaTypeRegistry;

import java.util.HashMap;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.HashSet;

/**
 * DLT645 电表 CoAP 模拟器（Java 版）。
 */
public class Dlt645MeterCoap {

    static final Object LOCK = new Object();
    static final String DEFAULT_COAP_HOST = "129.211.239.15";
    static double ua = 220, ub = 220, uc = 220;
    static double ia = 5, ib = 5, ic = 5;
    static double pf = 0.95, freq = 50;
    static double forward = 0, reverse = 0;
    static boolean relay = true;
    static int reportInterval = 5;
    static volatile boolean running = true;

    static Gson gson = new GsonBuilder().create();
    static String baseUrl;

    public static void main(String[] args) throws Exception {
        Args a = new Args(args);
        String host = a.get("coap-host", DEFAULT_COAP_HOST);
        int port = Integer.parseInt(a.get("coap-port", "5683"));
        String token = a.get("token", "");
        if (token.isBlank()) {
            throw new IllegalArgumentException("--token is required");
        }
        double interval = Double.parseDouble(a.get("interval", "5"));
        double eventInterval = Double.parseDouble(a.get("event-interval", "30"));
        int count = Integer.parseInt(a.get("count", "0"));
        int timeout = Integer.parseInt(a.get("timeout", "30"));
        boolean observe = a.has("observe");
        relay = !a.has("relay-off");
        Random rng = new Random(Long.parseLong(a.get("seed", String.valueOf(System.currentTimeMillis()))));
        baseUrl = "coap://" + host + ":" + port + "/api/v1/" + token;

        System.out.println("protocol=CoAP endpoint=" + baseUrl);
        CoapObserveRelation attributesRelation = null;
        CoapObserveRelation rpcRelation = null;
        if (observe) {
            attributesRelation = observeAttributes(timeout);
            rpcRelation = observeRpc(timeout);
            System.out.println("downlink observe enabled");
        }

        int iterations = 0;
        long lastEvent = System.currentTimeMillis();
        try {
            while (count <= 0 || iterations < count) {
                synchronized (LOCK) {
                    advance(interval, rng);
                }
                publishTelemetry(timeout);
                iterations++;
                if (eventInterval > 0 && System.currentTimeMillis() - lastEvent >= eventInterval * 1000) {
                    publishEvent(timeout, rng);
                    lastEvent = System.currentTimeMillis();
                }
                if (count > 0 && iterations >= count) {
                    break;
                }
                Thread.sleep((long) (interval * 1000));
            }
        } finally {
            running = false;
            if (attributesRelation != null) {
                attributesRelation.proactiveCancel();
            }
            if (rpcRelation != null) {
                rpcRelation.proactiveCancel();
            }
            System.out.println("summary telemetry=" + iterations);
        }
    }

    static CoapObserveRelation observeAttributes(int timeout) {
        CoapClient client = new CoapClient(baseUrl + "/attributes");
        client.setTimeout(timeout * 1000L);
        return client.observe(new CoapHandler() {
            @Override
            public void onLoad(CoapResponse response) {
                if (!response.isSuccess() || response.getResponseText().isBlank()) {
                    return;
                }
                JsonObject payload = JsonParser.parseString(response.getResponseText()).getAsJsonObject();
                if (payload.size() == 0) {
                    return;
                }
                boolean changed;
                synchronized (LOCK) {
                    changed = applyShared(payload);
                }
                System.out.println("shared attributes " + gson.toJson(payload));
                if (changed) {
                    try {
                        publishTelemetry(timeout);
                    } catch (Exception e) {
                        System.err.println("publish telemetry failed: " + e.getMessage());
                    }
                }
            }

            @Override
            public void onError() {
                System.err.println("attributes observe error");
            }
        });
    }

    static CoapObserveRelation observeRpc(int timeout) {
        CoapClient client = new CoapClient(baseUrl + "/rpc");
        client.setTimeout(timeout * 1000L);
        return client.observe(new CoapHandler() {
            @Override
            public void onLoad(CoapResponse response) {
                if (!response.isSuccess() || response.getResponseText().isBlank()) {
                    return;
                }
                JsonObject payload = JsonParser.parseString(response.getResponseText()).getAsJsonObject();
                if (payload.size() == 0) {
                    return;
                }
                JsonObject result;
                synchronized (LOCK) {
                    result = handleRpc(payload);
                }
                if (payload.has("id")) {
                    String requestId = payload.get("id").getAsString();
                    try {
                        post(baseUrl + "/rpc/" + requestId, gson.toJson(result), timeout);
                    } catch (Exception e) {
                        System.err.println("rpc response failed: " + e.getMessage());
                    }
                }
                System.out.println("rpc " + payload.get("method").getAsString() + " -> " + gson.toJson(result));
                if (result.has("success") && result.get("success").getAsBoolean()) {
                    try {
                        publishTelemetry(timeout);
                    } catch (Exception e) {
                        System.err.println("publish telemetry failed: " + e.getMessage());
                    }
                }
            }

            @Override
            public void onError() {
                System.err.println("rpc observe error");
            }
        });
    }

    static void publishTelemetry(int timeout) throws Exception {
        JsonObject values;
        synchronized (LOCK) {
            values = buildTelemetry();
        }
        post(baseUrl + "/telemetry", gson.toJson(values), timeout);
        System.out.println("[telemetry] " + gson.toJson(values));
    }

    static void publishEvent(int timeout, Random rng) throws Exception {
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
        post(baseUrl + "/telemetry", gson.toJson(payload), timeout);
        System.out.println("[event] " + gson.toJson(event));
    }

    static void post(String uri, String body, int timeout) throws Exception {
        CoapClient client = new CoapClient(uri);
        client.setTimeout(timeout * 1000L);
        CoapResponse response = client.post(body, MediaTypeRegistry.APPLICATION_JSON);
        if (response == null) {
            throw new RuntimeException("CoAP timeout: " + uri);
        }
        if (!response.isSuccess()) {
            throw new RuntimeException("CoAP " + response.getCode() + " " + uri);
        }
    }

    static JsonObject buildTelemetry() {
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
        return values;
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

    static boolean applyShared(JsonObject attributes) {
        boolean changed = false;
        if (attributes.has("reportInterval")) {
            int value = attributes.get("reportInterval").getAsInt();
            reportInterval = Math.max(5, Math.min(3600, value));
            changed = true;
        }
        if (attributes.has("relay")) {
            relay = attributes.get("relay").getAsBoolean();
            changed = true;
        }
        if (attributes.has("relayState")) {
            relay = attributes.get("relayState").getAsBoolean();
            changed = true;
        }
        return changed;
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
                int value = params.has("reportInterval") ? params.get("reportInterval").getAsInt() : -1;
                if (value < 5 || value > 3600) {
                    response.addProperty("success", false);
                    response.addProperty("error", "invalid reportInterval");
                } else {
                    reportInterval = value;
                    response.addProperty("success", true);
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
