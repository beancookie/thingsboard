#!/usr/bin/env python3
"""DLT645 电表 MQTT 模拟器示例。

通过设备 Access Token 连接 ThingsBoard MQTT，按物模型周期性上报遥测和事件，
并处理共享属性、RPC 下发。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

LOGGER = logging.getLogger("dlt645-meter-simulator")

TELEMETRY_TOPIC = "v1/devices/me/telemetry"
ATTRIBUTES_TOPIC = "v1/devices/me/attributes"
RPC_REQUEST_PREFIX = "v1/devices/me/rpc/request/"
RPC_RESPONSE_TEMPLATE = "v1/devices/me/rpc/response/{request_id}"

DEFAULT_TSL_PATH = Path(__file__).with_name(
    "dlt645_meter_thing_model.tsl.json")

METER_INFO = {
    "model": "DTZ341",
    "assetNo": "ASSET-000000000001",
    "meterNo": "000000000001",
    "manufacturer": "中国中铁物联网平台",
    "hardwareVersion": "HW-1.0",
    "protocolVersion": "DL/T 645-2007",
    "softwareVersion": "SW-1.0",
}


@dataclass
class SimulatorConfig:
    mqtt_host: str
    mqtt_port: int
    token: str
    client_id: str
    tsl_path: Path
    interval: float
    event_interval: float
    count: int
    qos: int
    keepalive: int
    relay_on: bool
    tls: bool
    ca_cert: Optional[str]
    seed: Optional[int]
    dry_run: bool
    log_level: str


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )


def now_ms() -> int:
    return int(time.time() * 1000)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def load_tsl(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"TSL 文件不存在: {path}")
    with path.open(encoding="utf-8") as stream:
        tsl = json.load(stream)
    if not isinstance(tsl, dict):
        raise RuntimeError(f"TSL 文件必须是 JSON 对象: {path}")
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


def mask_token(token: str) -> str:
    if len(token) <= 6:
        return "***"
    return f"{token[:4]}...{token[-2:]}"


class MeterState:
    def __init__(
            self,
            tsl: Dict[str, Any],
            interval: float,
            rng: random.Random,
            relay_on: bool) -> None:
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
        self.forward_active = float(
            starts.get("forwardActiveEnergy_kWh", 0))
        self.reverse_active = float(
            starts.get("reverseActiveEnergy_kWh", 0))
        self.combined_active = float(
            starts.get("combinedActiveEnergy_kWh", 0))
        self.forward_reactive = float(
            starts.get("forwardReactiveEnergy_kvarh", 0))
        self.reverse_reactive = float(
            starts.get("reverseReactiveEnergy_kvarh", 0))
        self.meter_status = 0
        self.relay = relay_on
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
    raise RuntimeError("MQTT 连接超时")


class Dlt645MeterSimulator:
    def __init__(
            self,
            config: SimulatorConfig,
            tsl: Dict[str, Any],
            rng: random.Random) -> None:
        self.config = config
        self.tsl = tsl
        self.rng = rng
        self.state = MeterState(
            tsl, config.interval, rng, relay_on=config.relay_on)
        self.telemetry_interval = max(5.0, float(config.interval))
        self.telemetry_count = 0
        self.event_count = 0
        self.rpc_count = 0
        self.client = create_mqtt_client(config.client_id)
        self.client.username_pw_set(config.token, "")
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(
            self,
            client: mqtt.Client,
            userdata: Any,
            flags: Any,
            reason_code: Any,
            *extra: Any) -> None:
        code = getattr(reason_code, "value", reason_code)
        if code != 0:
            LOGGER.error("MQTT 连接失败: %s", reason_code)
            return
        client.subscribe(ATTRIBUTES_TOPIC, qos=self.config.qos)
        client.subscribe(f"{RPC_REQUEST_PREFIX}+", qos=self.config.qos)
        LOGGER.info(
            "已连接 host=%s:%s clientId=%s token=%s",
            self.config.mqtt_host,
            self.config.mqtt_port,
            self.config.client_id,
            mask_token(self.config.token),
        )
        LOGGER.info("已订阅 %s, %s+", ATTRIBUTES_TOPIC, RPC_REQUEST_PREFIX)

    def _on_disconnect(
            self,
            client: mqtt.Client,
            userdata: Any,
            *args: Any) -> None:
        LOGGER.warning("MQTT 连接已断开")

    def _on_message(
            self,
            client: mqtt.Client,
            userdata: Any,
            message: Any) -> None:
        topic = message.topic
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except Exception as exc:
            LOGGER.error("主题 %s 收到非法 JSON: %s", topic, exc)
            return

        if topic == ATTRIBUTES_TOPIC:
            if not isinstance(payload, dict):
                LOGGER.error("共享属性必须是 JSON 对象")
                return
            changed = apply_shared(self.state, payload)
            LOGGER.info(
                "收到共享属性: %s", json.dumps(payload, ensure_ascii=False))
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
            params = payload.get("params") if isinstance(payload, dict) else None
            LOGGER.info(
                "收到 RPC method=%s params=%s response=%s",
                method,
                json.dumps(params, ensure_ascii=False),
                json.dumps(response, ensure_ascii=False),
            )
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
            qos=self.config.qos,
        )
        if wait:
            info.wait_for_publish(timeout=30)
            if not info.is_published():
                raise RuntimeError(f"MQTT 发布超时: {topic}")

    def publish_telemetry(self, wait: bool = True) -> None:
        payload = build_telemetry(self.state)
        self.publish(TELEMETRY_TOPIC, payload, wait=wait)
        self.telemetry_count += 1
        LOGGER.info(
            "[telemetry] %s", json.dumps(payload, ensure_ascii=False))

    def publish_event(self) -> None:
        event = build_event(self.tsl, self.state, self.rng)
        self.publish(TELEMETRY_TOPIC, {"events": [event]}, wait=True)
        self.event_count += 1
        LOGGER.info("[event] %s", json.dumps(event, ensure_ascii=False))

    def run(self) -> int:
        if self.config.tls or self.config.mqtt_port == 8883:
            self.client.tls_set(ca_certs=self.config.ca_cert)

        self.client.connect(
            self.config.mqtt_host,
            self.config.mqtt_port,
            keepalive=self.config.keepalive,
        )
        self.client.loop_start()
        wait_connected(self.client)

        last_event = time.time()
        iterations = 0
        try:
            while self.config.count <= 0 or iterations < self.config.count:
                self.state.advance(self.telemetry_interval)
                self.state.report_interval = max(
                    5, min(3600, int(self.telemetry_interval)))
                self.publish_telemetry()
                iterations += 1

                if (self.config.event_interval > 0
                        and time.time() - last_event
                        >= self.config.event_interval):
                    self.publish_event()
                    last_event = time.time()

                if (self.config.count > 0
                        and iterations >= self.config.count):
                    break
                time.sleep(self.telemetry_interval)
        except KeyboardInterrupt:
            LOGGER.warning("收到中断，正在退出")
        finally:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
            LOGGER.info(
                "汇总 telemetry=%s event=%s rpc=%s",
                self.telemetry_count,
                self.event_count,
                self.rpc_count,
            )
        return 0

    def apply_report_interval(self, interval: int) -> None:
        self.telemetry_interval = float(max(5, min(3600, interval)))


def run_dry_run(
        config: SimulatorConfig,
        tsl: Dict[str, Any],
        rng: random.Random) -> int:
    state = MeterState(
        tsl, config.interval, rng, relay_on=config.relay_on)
    for _ in range(2):
        state.advance(max(5.0, config.interval))
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


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="模拟 DLT645 电表通过 ThingsBoard MQTT 上报数据。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    connection = parser.add_argument_group("连接")
    connection.add_argument(
        "--mqtt-host",
        default="127.0.0.1",
        help="MQTT 服务地址",
    )
    connection.add_argument(
        "--mqtt-port",
        type=int,
        default=1883,
        help="MQTT 服务端口",
    )
    connection.add_argument(
        "--client-id",
        default=None,
        help="MQTT Client ID，默认根据设备令牌自动生成",
    )
    connection.add_argument(
        "--keepalive",
        type=int,
        default=60,
        help="MQTT Keepalive 秒数",
    )
    connection.add_argument(
        "--qos",
        type=int,
        default=1,
        choices=[0, 1, 2],
        help="MQTT QoS",
    )
    connection.add_argument(
        "--tls",
        action="store_true",
        help="启用 TLS",
    )
    connection.add_argument(
        "--ca-cert",
        default=None,
        help="TLS CA 证书路径",
    )

    auth = parser.add_argument_group("认证")
    auth.add_argument(
        "--token",
        default=None,
        help="设备 Access Token；--dry-run 时可省略",
    )

    behavior = parser.add_argument_group("行为")
    behavior.add_argument(
        "--tsl",
        default=str(DEFAULT_TSL_PATH),
        help="物模型 TSL JSON 文件",
    )
    behavior.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="遥测上报间隔（秒，最小 5）",
    )
    behavior.add_argument(
        "--event-interval",
        type=float,
        default=30.0,
        help="事件上报间隔（秒，0 表示关闭）",
    )
    behavior.add_argument(
        "--count",
        type=int,
        default=0,
        help="遥测轮次，0 表示持续运行",
    )
    behavior.add_argument(
        "--seed",
        type=int,
        default=None,
        help="随机数种子",
    )
    behavior.add_argument(
        "--relay-off",
        action="store_true",
        help="启动时继电器为断开状态",
    )
    behavior.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印示例报文，不连接 MQTT",
    )

    output = parser.add_argument_group("输出")
    output.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> SimulatorConfig:
    client_id = args.client_id
    if not client_id:
        token_suffix = (args.token or "dryrun")[-10:]
        client_id = f"meter-{token_suffix}"
    return SimulatorConfig(
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        token=args.token or "",
        client_id=client_id,
        tsl_path=Path(args.tsl),
        interval=args.interval,
        event_interval=args.event_interval,
        count=args.count,
        qos=args.qos,
        keepalive=args.keepalive,
        relay_on=not args.relay_off,
        tls=args.tls,
        ca_cert=args.ca_cert,
        seed=args.seed,
        dry_run=args.dry_run,
        log_level=args.log_level,
    )


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)

    if not args.dry_run and not args.token:
        parser.error("--token 为必填参数；使用 --dry-run 时可省略")
    if args.count < 0:
        parser.error("--count 必须大于等于 0")
    if args.interval < 5:
        parser.error("--interval 不能小于 5 秒")

    config = config_from_args(args)
    rng = random.Random(config.seed)
    try:
        tsl = load_tsl(config.tsl_path)
    except Exception as exc:
        LOGGER.error("加载物模型失败: %s", exc)
        return 1

    if config.dry_run:
        return run_dry_run(config, tsl, rng)

    try:
        return Dlt645MeterSimulator(config, tsl, rng).run()
    except Exception as exc:
        LOGGER.error("模拟器运行失败: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
