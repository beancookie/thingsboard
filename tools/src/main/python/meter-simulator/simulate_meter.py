#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt


DEFAULT_MQTT_HOST = "129.211.241.31"
DEFAULT_MQTT_PORT = 1883
DEFAULT_TOKEN = ""
DEFAULT_CLIENT_ID = "meter-YUMRMRPOGPA"
DEFAULT_TSL = Path(__file__).with_name("meter-thing-model.tsl.json")

TELEMETRY_TOPIC = "v1/devices/me/telemetry"
ATTRIBUTES_TOPIC = "v1/devices/me/attributes"
RPC_REQUEST_PREFIX = "v1/devices/me/rpc/request/"
RPC_RESPONSE_TEMPLATE = "v1/devices/me/rpc/response/{request_id}"

METER_INFO = {
    "model": "DTZ341",
    "assetNo": "ASSET-YUMRMRPOGPA-0001",
    "meterNo": "000000000001",
    "manufacturer": "中国中铁物联网平台",
    "hardwareVersion": "HW-1.0",
    "protocolVersion": "DL/T 645-2007",
    "softwareVersion": "SW-1.0",
}


def now_ms() -> int:
    return int(time.time() * 1000)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def load_tsl(path: str) -> Dict[str, Any]:
    tsl_path = Path(path)
    if not tsl_path.is_file():
        raise RuntimeError(f"TSL file not found: {tsl_path}")
    with tsl_path.open(encoding="utf-8") as stream:
        tsl = json.load(stream)
    if not isinstance(tsl, dict):
        raise RuntimeError(f"TSL file must be a JSON object: {tsl_path}")
    return tsl


def parse_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "1", "on", "yes"):
            return True
        if text in ("false", "0", "off", "no"):
            return False
    return None


def parse_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


class MeterState:
    def __init__(
            self,
            tsl: Dict[str, Any],
            interval: float,
            rng: random.Random,
            relay: bool = True) -> None:
        starts = {
            prop.get("id"): prop.get("define", {}).get("start", 0)
            for prop in tsl.get("properties") or []
        }
        self.rng = rng
        self.ua = float(starts.get("UA_V", 220))
        self.ub = float(starts.get("UB_V", 220))
        self.uc = float(starts.get("UC_V", 220))
        self.ia = float(starts.get("IA_A", 5))
        self.ib = float(starts.get("IB_A", 5))
        self.ic = float(starts.get("IC_A", 5))
        self.p = float(starts.get("P_kW", 3))
        self.q = float(starts.get("Q_kvar", 1))
        self.s = float(starts.get("S_kVA", 3))
        self.pf = float(starts.get("PF", 0.95))
        self.f = float(starts.get("F_Hz", 50))
        self.forward_active = float(starts.get("forwardActiveEnergy_kWh", 0))
        self.reverse_active = float(starts.get("reverseActiveEnergy_kWh", 0))
        self.combined_active = float(
            starts.get("combinedActiveEnergy_kWh", 0))
        self.forward_reactive = float(
            starts.get("forwardReactiveEnergy_kvarh", 0))
        self.reverse_reactive = float(
            starts.get("reverseReactiveEnergy_kvarh", 0))
        self.meter_status = 0
        self.relay = relay
        self.report_interval = max(5, min(3600, int(interval)))
        self.last_read_time = now_ms()
        self.meter_info = dict(METER_INFO)

    def advance(self, seconds: float) -> None:
        self.ua = clamp(self.ua + self.rng.uniform(-1.5, 1.5), 0, 300)
        self.ub = clamp(self.ub + self.rng.uniform(-1.5, 1.5), 0, 300)
        self.uc = clamp(self.uc + self.rng.uniform(-1.5, 1.5), 0, 300)

        target_current = 5.0 if self.relay else 0.0
        self.ia = clamp(
            self.ia + (target_current - self.ia) * 0.35
            + self.rng.uniform(-0.2, 0.2), 0, 100)
        self.ib = clamp(
            self.ib + (target_current - self.ib) * 0.35
            + self.rng.uniform(-0.2, 0.2), 0, 100)
        self.ic = clamp(
            self.ic + (target_current - self.ic) * 0.35
            + self.rng.uniform(-0.2, 0.2), 0, 100)

        self.pf = clamp(self.pf + self.rng.uniform(-0.01, 0.01), 0, 1)
        self.f = clamp(self.f + self.rng.uniform(-0.05, 0.05), 45, 65)

        average_voltage = (self.ua + self.ub + self.uc) / 3
        average_current = (self.ia + self.ib + self.ic) / 3
        self.s = clamp(
            math.sqrt(3) * average_voltage * average_current / 1000, 0, 1000)
        self.p = clamp(self.s * self.pf, 0, 1000)
        self.q = clamp(
            self.s * math.sqrt(max(0.0, 1 - self.pf * self.pf)), 0, 1000)

        hours = max(0.0, seconds) / 3600
        self.forward_active = clamp(
            self.forward_active + self.p * hours, 0, 99999999)
        self.reverse_active = clamp(
            self.reverse_active + self.p * 0.01 * hours, 0, 99999999)
        self.combined_active = clamp(
            self.forward_active + self.reverse_active, 0, 99999999)
        self.forward_reactive = clamp(
            self.forward_reactive + self.q * hours, 0, 99999999)
        self.reverse_reactive = clamp(
            self.reverse_reactive + self.q * 0.01 * hours, 0, 99999999)

        self.meter_status = 1 if self.rng.random() < 0.01 else 0
        self.last_read_time = now_ms()


def build_telemetry(state: MeterState) -> Dict[str, Any]:
    return {
        "meterInfo": dict(state.meter_info),
        "UA_V": round(state.ua, 2),
        "UB_V": round(state.ub, 2),
        "UC_V": round(state.uc, 2),
        "IA_A": round(state.ia, 2),
        "IB_A": round(state.ib, 2),
        "IC_A": round(state.ic, 2),
        "P_kW": round(state.p, 3),
        "Q_kvar": round(state.q, 3),
        "S_kVA": round(state.s, 3),
        "PF": round(state.pf, 3),
        "F_Hz": round(state.f, 2),
        "forwardActiveEnergy_kWh": round(state.forward_active, 3),
        "reverseActiveEnergy_kWh": round(state.reverse_active, 3),
        "combinedActiveEnergy_kWh": round(state.combined_active, 3),
        "forwardReactiveEnergy_kvarh": round(state.forward_reactive, 3),
        "reverseReactiveEnergy_kvarh": round(state.reverse_reactive, 3),
        "meterStatus": int(state.meter_status),
        "relayState": bool(state.relay),
        "reportInterval": int(state.report_interval),
        "lastReadTime": int(state.last_read_time),
    }


def event_param_value(
        event_id: str,
        param: Dict[str, Any],
        state: MeterState,
        rng: random.Random,
        event_ts: int) -> Any:
    param_id = str(param.get("id") or "")
    define = param.get("define") or {}
    data_type = str(define.get("type") or "string").lower()

    if data_type == "timestamp":
        return event_ts
    if data_type in ("enum", "enum_string"):
        mapping = define.get("mapping")
        if isinstance(mapping, dict) and mapping:
            return rng.choice(list(mapping.keys()))
        return "" if data_type == "enum_string" else 0
    if data_type == "bool":
        return rng.choice([True, False])

    if param_id == "voltage":
        if event_id == "overVoltage":
            value = max(
                state.ua + rng.uniform(10, 25),
                230 + rng.uniform(0.1, 20),
            )
            return round(clamp(value, 0, 300), 2)
        if event_id == "underVoltage":
            value = min(
                state.ua - rng.uniform(20, 40),
                180 - rng.uniform(0.1, 20),
            )
            return round(clamp(value, 0, 300), 2)
        return round(state.ua, 2)
    if param_id == "current":
        value = max(
            max(state.ia, state.ib, state.ic) + rng.uniform(1, 5),
            10 + rng.uniform(0.1, 5),
        )
        return round(clamp(value, 0, 100), 2)
    if param_id == "threshold":
        if event_id == "overVoltage":
            return 230.0
        if event_id == "underVoltage":
            return 180.0
        if event_id == "overCurrent":
            return 10.0
        return 0.0
    if param_id == "code":
        return f"E{rng.randint(1, 999):04d}"
    if param_id == "message":
        return rng.choice([
            "计量芯片异常",
            "采样回路异常",
            "存储器异常",
            "通信异常",
        ])

    if data_type == "int":
        minimum = int(define.get("min", 0))
        maximum = int(define.get("max", minimum + 100))
        return rng.randint(minimum, maximum)
    if data_type == "float":
        minimum = float(define.get("min", 0))
        maximum = float(define.get("max", minimum + 100))
        return round(rng.uniform(minimum, maximum), 2)
    return f"sim-{rng.randint(0, 999999):06d}"


def build_event(
        tsl: Dict[str, Any],
        state: MeterState,
        rng: random.Random,
        event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    events = tsl.get("events") or []
    selected = event
    if selected is None and events:
        selected = rng.choice(events)
    event_ts = now_ms()
    if not selected:
        return {
            "event_id": f"evt-{rng.randint(0, 0xFFFFFF):06x}",
            "event_type": "info",
            "event_ts": event_ts,
        }

    event_id = str(selected.get("id") or "event")
    values: Dict[str, Any] = {
        "event_id": event_id,
        "event_type": selected.get("type") or "info",
        "event_ts": event_ts,
    }
    for param in selected.get("params") or []:
        param_id = param.get("id")
        if param_id:
            values[param_id] = event_param_value(
                event_id, param, state, rng, event_ts)
    return values


def apply_shared(state: MeterState, attributes: Dict[str, Any]) -> bool:
    if not isinstance(attributes, dict):
        return False
    changed = False
    for key, value in attributes.items():
        if key == "reportInterval":
            interval = parse_int(value)
            if interval is not None and 5 <= interval <= 3600:
                state.report_interval = interval
                changed = True
        elif key in ("relay", "relayState"):
            relay = parse_bool(value)
            if relay is not None:
                state.relay = relay
                changed = True
    return changed


def handle_rpc(state: MeterState, payload: Dict[str, Any]) -> Dict[str, Any]:
    method = payload.get("method")
    params = payload.get("params")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return {"success": False, "error": "params must be an object"}

    if method == "set":
        apply_shared(state, params)
        return {"success": True}

    if method == "setRelay":
        relay = parse_bool(params.get("on"))
        if relay is None:
            return {"success": False, "error": "invalid relay state"}
        state.relay = relay
        return {"success": True}

    if method == "applyConfig":
        interval = parse_int(params.get("reportInterval"))
        if interval is None or not 5 <= interval <= 3600:
            return {"success": False, "error": "invalid reportInterval"}
        state.report_interval = interval
        return {"success": True}

    if method == "syncTime":
        target_time = parse_int(params.get("time"))
        if target_time is None or target_time <= 0:
            return {"success": False, "error": "invalid time"}
        state.last_read_time = target_time
        return {"success": True}

    return {"success": False, "error": f"unsupported method: {method}"}


def create_mqtt_client(client_id: str) -> mqtt.Client:
    if hasattr(mqtt, "CallbackAPIVersion"):
        return mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )
    return mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)


def wait_connected(client: mqtt.Client, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if client.is_connected():
            return
        time.sleep(0.1)
    raise RuntimeError("MQTT connection timeout")


def mask_token(token: str) -> str:
    if len(token) <= 6:
        return "***"
    return f"{token[:4]}...{token[-2:]}"


class MeterSimulator:
    def __init__(
            self,
            args: argparse.Namespace,
            tsl: Dict[str, Any],
            rng: random.Random) -> None:
        self.args = args
        self.tsl = tsl
        self.rng = rng
        self.state = MeterState(
            tsl, args.interval, rng, relay=not args.relay_off)
        self.telemetry_interval = max(5.0, float(args.interval))
        self.client = create_mqtt_client(args.client_id)
        self.client.username_pw_set(args.token, "")
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.telemetry_count = 0
        self.event_count = 0
        self.rpc_count = 0

    def _on_connect(
            self,
            client: mqtt.Client,
            userdata: Any,
            flags: Any,
            reason_code: Any,
            *extra: Any) -> None:
        code = getattr(reason_code, "value", reason_code)
        if code != 0:
            print(f"MQTT connect failed: {reason_code}", file=sys.stderr)
            return
        client.subscribe(ATTRIBUTES_TOPIC, qos=self.args.qos)
        client.subscribe(f"{RPC_REQUEST_PREFIX}+", qos=self.args.qos)
        print(
            f"connected host={self.args.mqtt_host}:{self.args.mqtt_port} "
            f"clientId={self.args.client_id} token={mask_token(self.args.token)}")
        print(
            f"subscribed {ATTRIBUTES_TOPIC}, {RPC_REQUEST_PREFIX}+")

    def _on_disconnect(
            self,
            client: mqtt.Client,
            userdata: Any,
            *args: Any) -> None:
        print("MQTT disconnected", file=sys.stderr)

    def _on_message(
            self,
            client: mqtt.Client,
            userdata: Any,
            message: Any) -> None:
        topic = message.topic
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except Exception as exc:
            print(f"invalid payload on {topic}: {exc}", file=sys.stderr)
            return

        if topic == ATTRIBUTES_TOPIC:
            if not isinstance(payload, dict):
                print("shared attributes payload must be an object",
                      file=sys.stderr)
                return
            changed = apply_shared(self.state, payload)
            print(
                f"shared attributes {json.dumps(payload, ensure_ascii=False)}")
            if changed:
                self.apply_report_interval(self.state.report_interval)
                self.publish_telemetry(wait=False)
            return

        if topic.startswith(RPC_REQUEST_PREFIX):
            request_id = topic.rsplit("/", 1)[-1]
            if not isinstance(payload, dict):
                response: Dict[str, Any] = {
                    "success": False,
                    "error": "payload must be a JSON object",
                }
                method = None
            else:
                method = payload.get("method")
                response = handle_rpc(self.state, payload)
            self.rpc_count += 1
            self.publish(
                RPC_RESPONSE_TEMPLATE.format(request_id=request_id),
                response,
                wait=False,
            )
            print(
                f"rpc method={method} params="
                f"{json.dumps(payload.get('params') if isinstance(payload, dict) else None, ensure_ascii=False)} "
                f"response={json.dumps(response, ensure_ascii=False)}")
            if response.get("success"):
                self.apply_report_interval(self.state.report_interval)
                self.publish_telemetry(wait=False)

    def publish(
            self,
            topic: str,
            payload: Any,
            wait: bool = True) -> None:
        info = self.client.publish(
            topic,
            json.dumps(payload, ensure_ascii=False),
            qos=self.args.qos,
        )
        if wait:
            info.wait_for_publish(timeout=30)
            if not info.is_published():
                raise RuntimeError(f"MQTT publish timeout: {topic}")

    def publish_telemetry(self, wait: bool = True) -> None:
        payload = build_telemetry(self.state)
        self.publish(TELEMETRY_TOPIC, payload, wait=wait)
        self.telemetry_count += 1
        print(f"[telemetry] {json.dumps(payload, ensure_ascii=False)}")

    def publish_event(self) -> None:
        event = build_event(self.tsl, self.state, self.rng)
        self.publish(TELEMETRY_TOPIC, {"events": [event]}, wait=True)
        self.event_count += 1
        print(f"[event] {json.dumps(event, ensure_ascii=False)}")

    def run(self) -> int:
        if self.args.tls or self.args.mqtt_port == 8883:
            self.client.tls_set(ca_certs=self.args.ca_cert)
        self.client.connect(
            self.args.mqtt_host,
            self.args.mqtt_port,
            keepalive=self.args.keepalive,
        )
        self.client.loop_start()
        wait_connected(self.client)

        last_event = time.time()
        iterations = 0
        try:
            while self.args.count <= 0 or iterations < self.args.count:
                self.state.advance(self.telemetry_interval)
                self.state.report_interval = max(
                    5, min(3600, int(self.telemetry_interval)))
                self.publish_telemetry()
                iterations += 1

                if (self.args.event_interval > 0
                        and time.time() - last_event >= self.args.event_interval):
                    self.publish_event()
                    last_event = time.time()

                if self.args.count > 0 and iterations >= self.args.count:
                    break
                time.sleep(self.telemetry_interval)
        except KeyboardInterrupt:
            print("\ninterrupted", file=sys.stderr)
        finally:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
            print(
                f"summary telemetry={self.telemetry_count} "
                f"event={self.event_count} rpc={self.rpc_count}")
        return 0

    def apply_report_interval(self, interval: int) -> None:
        self.telemetry_interval = float(max(5, min(3600, interval)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate a DLT645 meter device over ThingsBoard MQTT.")
    parser.add_argument(
        "--mqtt-host",
        default=os.getenv("MQTT_HOST", DEFAULT_MQTT_HOST),
        help="MQTT host",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=int(os.getenv("MQTT_PORT", str(DEFAULT_MQTT_PORT))),
        help="MQTT port",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("ACCESS_TOKEN", DEFAULT_TOKEN),
        help="device access token; defaults to the ACCESS_TOKEN environment variable",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("MQTT_CLIENT_ID", DEFAULT_CLIENT_ID),
        help="MQTT client id",
    )
    parser.add_argument(
        "--tsl",
        default=os.getenv("METER_TSL", str(DEFAULT_TSL)),
        help="meter thing model JSON file",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="telemetry interval in seconds (minimum 5)",
    )
    parser.add_argument(
        "--event-interval",
        type=float,
        default=30.0,
        help="event interval in seconds; 0 disables events",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="telemetry iterations; 0 means run until Ctrl+C",
    )
    parser.add_argument(
        "--qos",
        type=int,
        default=1,
        choices=[0, 1, 2],
        help="MQTT QoS",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="random seed",
    )
    parser.add_argument(
        "--keepalive",
        type=int,
        default=60,
        help="MQTT keepalive seconds",
    )
    parser.add_argument(
        "--relay-off",
        action="store_true",
        help="start with relay off; default is on",
    )
    parser.add_argument(
        "--tls",
        action="store_true",
        help="enable TLS",
    )
    parser.add_argument(
        "--ca-cert",
        default=None,
        help="CA certificate path for TLS",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print payloads without connecting to MQTT",
    )
    return parser.parse_args()


def dry_run(args: argparse.Namespace, tsl: Dict[str, Any],
            rng: random.Random) -> int:
    state = MeterState(
        tsl, args.interval, rng, relay=not args.relay_off)
    for _ in range(2):
        state.advance(max(5.0, args.interval))
        payload = build_telemetry(state)
        print(
            f"[dry-run] {TELEMETRY_TOPIC} "
            f"{json.dumps(payload, ensure_ascii=False)}")
    event = build_event(tsl, state, rng)
    print(
        f"[dry-run] {TELEMETRY_TOPIC} "
        f"{json.dumps({'events': [event]}, ensure_ascii=False)}")
    sample_rpc = [
        {"method": "setRelay", "params": {"on": True}},
        {"method": "applyConfig", "params": {"reportInterval": 30}},
        {"method": "syncTime", "params": {"time": now_ms()}},
    ]
    for request in sample_rpc:
        response = handle_rpc(state, request)
        print(
            f"[dry-run] rpc {request['method']} -> "
            f"{json.dumps(response, ensure_ascii=False)}")
    return 0


def main() -> int:
    args = parse_args()
    if args.count < 0:
        print("error: --count must be >= 0", file=sys.stderr)
        return 1
    rng = random.Random(args.seed)
    try:
        tsl = load_tsl(args.tsl)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        return dry_run(args, tsl, rng)

    try:
        simulator = MeterSimulator(args, tsl, rng)
        return simulator.run()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
