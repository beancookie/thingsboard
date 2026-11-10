#!/usr/bin/env python3
"""设备下行接收示例。

设备使用 Access Token 连接 ThingsBoard MQTT，订阅共享属性和 RPC 主题，
演示平台如何向设备推送配置和下发控制命令。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

LOGGER = logging.getLogger("device-downlink-client")

ATTRIBUTES_TOPIC = "v1/devices/me/attributes"
RPC_REQUEST_PREFIX = "v1/devices/me/rpc/request/"
RPC_RESPONSE_TEMPLATE = "v1/devices/me/rpc/response/{request_id}"
TELEMETRY_TOPIC = "v1/devices/me/telemetry"

DEFAULT_CONFIG = {
    "reportInterval": 60,
    "alarmThreshold": 80,
    "mode": 0,
    "relay": False,
}


@dataclass
class ClientConfig:
    mqtt_host: str
    mqtt_port: int
    token: str
    client_id: str
    qos: int
    keepalive: int
    tls: bool
    ca_cert: Optional[str]
    ack_telemetry: bool
    dry_run: bool
    log_level: str


@dataclass
class DeviceState:
    config: Dict[str, Any] = field(
        default_factory=lambda: dict(DEFAULT_CONFIG))

    def apply(self, values: Dict[str, Any]) -> None:
        if isinstance(values, dict):
            self.config.update(values)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )


def mask_token(token: str) -> str:
    if len(token) <= 6:
        return "***"
    return f"{token[:4]}...{token[-2:]}"


def parse_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def parse_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "1", "on", "yes"):
            return True
        if text in ("false", "0", "off", "no"):
            return False
    return None


def handle_rpc(state: DeviceState, payload: Dict[str, Any]) -> Dict[str, Any]:
    method = payload.get("method")
    params = payload.get("params")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return {"error": "params must be an object"}

    if method == "set":
        state.apply(params)
        return {"result": "ok", "config": state.config}

    if method == "setMode":
        mode = parse_int(params.get("mode"))
        if mode not in (0, 1, 2):
            return {"error": "invalid mode"}
        state.config["mode"] = mode
        return {"result": "ok", "mode": mode}

    if method == "setRelay":
        relay = parse_bool(params.get("on"))
        if relay is None:
            return {"error": "invalid relay state"}
        state.config["relay"] = relay
        return {"result": "ok", "relay": relay}

    if method == "applyConfig":
        interval = parse_int(params.get("reportInterval"))
        if interval is None or not 5 <= interval <= 3600:
            return {"error": "invalid reportInterval"}
        state.config["reportInterval"] = interval
        return {"result": "ok", "reportInterval": interval}

    return {"error": f"unsupported method: {method}"}


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


class DownlinkClient:
    def __init__(self, config: ClientConfig) -> None:
        self.config = config
        self.state = DeviceState()
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
        LOGGER.info("已订阅 %s 和 %s+", ATTRIBUTES_TOPIC, RPC_REQUEST_PREFIX)

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
            self.state.apply(payload)
            LOGGER.info(
                "共享属性: %s", json.dumps(payload, ensure_ascii=False))
            LOGGER.info(
                "当前配置: %s",
                json.dumps(self.state.config, ensure_ascii=False))
            return

        if topic.startswith(RPC_REQUEST_PREFIX):
            request_id = topic.rsplit("/", 1)[-1]
            if not isinstance(payload, dict):
                response: Dict[str, Any] = {
                    "error": "payload must be a JSON object"}
                method = None
            else:
                method = payload.get("method")
                response = handle_rpc(self.state, payload)
            self.publish(
                RPC_RESPONSE_TEMPLATE.format(request_id=request_id),
                response,
            )
            LOGGER.info(
                "RPC method=%s response=%s",
                method,
                json.dumps(response, ensure_ascii=False),
            )
            if self.config.ack_telemetry and "error" not in response:
                self.publish(TELEMETRY_TOPIC, {
                    "lastRpc": method,
                    "config": self.state.config,
                })

    def publish(self, topic: str, payload: Any) -> None:
        info = self.client.publish(
            topic,
            json.dumps(payload, ensure_ascii=False),
            qos=self.config.qos,
        )
        info.wait_for_publish(timeout=30)
        if not info.is_published():
            raise RuntimeError(f"MQTT 发布超时: {topic}")

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
        LOGGER.info("等待平台下发共享属性或 RPC，按 Ctrl+C 退出")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            LOGGER.warning("收到中断，正在退出")
        finally:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
        return 0


def run_dry_run(config: ClientConfig) -> int:
    state = DeviceState()
    samples = [
        ("attributes", {"reportInterval": 30, "mode": 1}),
        ("rpc", {"method": "setMode", "params": {"mode": 1}}),
        ("rpc", {"method": "setRelay", "params": {"on": True}}),
        ("rpc", {"method": "applyConfig", "params": {"reportInterval": 30}}),
        ("rpc", {"method": "unknown", "params": {}}),
    ]
    for kind, payload in samples:
        if kind == "attributes":
            state.apply(payload)
            print(
                f"[dry-run] {ATTRIBUTES_TOPIC} "
                f"{json.dumps(payload, ensure_ascii=False)}")
            print(
                "[dry-run] config "
                f"{json.dumps(state.config, ensure_ascii=False)}")
        else:
            response = handle_rpc(state, payload)
            print(
                f"[dry-run] rpc {payload['method']} -> "
                f"{json.dumps(response, ensure_ascii=False)}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="订阅 ThingsBoard 共享属性和 RPC，演示设备下行处理。",
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
        default="device-downlink-client",
        help="MQTT Client ID",
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
        "--ack-telemetry",
        action="store_true",
        help="RPC 成功后上报一条确认遥测",
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


def config_from_args(args: argparse.Namespace) -> ClientConfig:
    return ClientConfig(
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        token=args.token or "",
        client_id=args.client_id,
        qos=args.qos,
        keepalive=args.keepalive,
        tls=args.tls,
        ca_cert=args.ca_cert,
        ack_telemetry=args.ack_telemetry,
        dry_run=args.dry_run,
        log_level=args.log_level,
    )


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)

    if not args.dry_run and not args.token:
        parser.error("--token 为必填参数；使用 --dry-run 时可省略")

    config = config_from_args(args)
    if config.dry_run:
        return run_dry_run(config)

    try:
        return DownlinkClient(config).run()
    except Exception as exc:
        LOGGER.error("运行失败: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
