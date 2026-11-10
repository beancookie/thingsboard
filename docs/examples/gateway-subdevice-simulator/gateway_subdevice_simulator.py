#!/usr/bin/env python3
"""网关子设备 MQTT 模拟器示例。

使用网关设备 Access Token 连接 ThingsBoard MQTT，模拟多个子设备上线、上报遥测和属性，
退出时发送下线消息。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import paho.mqtt.client as mqtt

LOGGER = logging.getLogger("gateway-subdevice-simulator")

CONNECT_TOPIC = "v1/gateway/connect"
DISCONNECT_TOPIC = "v1/gateway/disconnect"
TELEMETRY_TOPIC = "v1/gateway/telemetry"
ATTRIBUTES_TOPIC = "v1/gateway/attributes"


@dataclass
class SimulatorConfig:
    mqtt_host: str
    mqtt_port: int
    gateway_token: str
    gateway_name: str
    sub_devices: List[Dict[str, str]]
    interval: float
    count: int
    qos: int
    keepalive: int
    device_type: str
    publish_attributes: bool
    tls: bool
    ca_cert: Optional[str]
    seed: Optional[int]
    dry_run: bool
    log_level: str


@dataclass
class DeviceState:
    name: str
    device_type: str
    temperature: float
    humidity: float
    voltage: float
    current: float
    online: bool = True

    def advance(self, rng: random.Random) -> Dict[str, Any]:
        self.temperature = round(
            max(0.0, min(80.0, self.temperature + rng.uniform(-0.6, 0.6))), 1)
        self.humidity = round(
            max(0.0, min(100.0, self.humidity + rng.uniform(-1.5, 1.5))), 1)
        self.voltage = round(
            max(0.0, min(300.0, self.voltage + rng.uniform(-1.2, 1.2))), 1)
        self.current = round(
            max(0.0, min(100.0, self.current + rng.uniform(-0.2, 0.2))), 2)
        return {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "voltage": self.voltage,
            "current": self.current,
            "status": "online" if self.online else "offline",
        }

    def attributes(self) -> Dict[str, Any]:
        return {
            "device_type": self.device_type,
            "gateway": True,
            "status": "online" if self.online else "offline",
        }


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )


def now_ms() -> int:
    return int(time.time() * 1000)


def mask_token(token: str) -> str:
    if len(token) <= 6:
        return "***"
    return f"{token[:4]}...{token[-2:]}"


def load_sub_devices(
        config: SimulatorConfig,
        csv_path: Optional[Path]) -> List[Dict[str, str]]:
    devices: List[Dict[str, str]] = []
    if csv_path:
        if not csv_path.is_file():
            raise RuntimeError(f"子设备 CSV 不存在: {csv_path}")
        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                name = (row.get("device_name") or "").strip()
                if not name:
                    continue
                device_type = (
                    (row.get("device_type") or "").strip()
                    or (row.get("product_id") or "").strip()
                    or (row.get("profile_name") or "").strip()
                    or config.device_type
                )
                devices.append({"name": name, "type": device_type})
    for name in config.sub_devices:
        devices.append({"name": name, "type": config.device_type})
    if not devices:
        raise RuntimeError("请通过 --sub-devices-csv 或 --sub-device 指定子设备")
    seen = set()
    unique = []
    for device in devices:
        if device["name"] in seen:
            continue
        seen.add(device["name"])
        unique.append(device)
    return unique


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


class GatewaySimulator:
    def __init__(
            self,
            config: SimulatorConfig,
            devices: List[Dict[str, str]],
            rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self.states = [
            DeviceState(
                name=device["name"],
                device_type=device["type"],
                temperature=rng.uniform(20, 30),
                humidity=rng.uniform(40, 70),
                voltage=rng.uniform(215, 225),
                current=rng.uniform(1, 10),
            )
            for device in devices
        ]
        self.client = create_mqtt_client(config.gateway_name)
        self.client.username_pw_set(config.gateway_token, "")
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

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
        LOGGER.info(
            "已连接 host=%s:%s gateway=%s token=%s",
            self.config.mqtt_host,
            self.config.mqtt_port,
            self.config.gateway_name,
            mask_token(self.config.gateway_token),
        )

    def _on_disconnect(
            self,
            client: mqtt.Client,
            userdata: Any,
            *args: Any) -> None:
        LOGGER.warning("MQTT 连接已断开")

    def publish(self, topic: str, payload: Any) -> None:
        info = self.client.publish(
            topic,
            json.dumps(payload, ensure_ascii=False),
            qos=self.config.qos,
        )
        info.wait_for_publish(timeout=30)
        if not info.is_published():
            raise RuntimeError(f"MQTT 发布超时: {topic}")

    def connect_devices(self) -> None:
        for state in self.states:
            self.publish(
                CONNECT_TOPIC,
                {"device": state.name, "type": state.device_type},
            )
            LOGGER.info("子设备上线 %s (%s)", state.name, state.device_type)
            if self.config.publish_attributes:
                self.publish(
                    ATTRIBUTES_TOPIC, {state.name: state.attributes()})

    def disconnect_devices(self) -> None:
        for state in self.states:
            try:
                self.publish(DISCONNECT_TOPIC, {"device": state.name})
                LOGGER.info("子设备下线 %s", state.name)
            except Exception as exc:
                LOGGER.warning("子设备下线失败 %s: %s", state.name, exc)

    def send_telemetry(self) -> None:
        timestamp = now_ms()
        payload: Dict[str, Any] = {}
        for state in self.states:
            values = state.advance(self.rng)
            payload[state.name] = [{"ts": timestamp, "values": values}]
        self.publish(TELEMETRY_TOPIC, payload)
        LOGGER.debug(
            "遥测 %s", json.dumps(payload, ensure_ascii=False))

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
        self.connect_devices()

        iterations = 0
        try:
            while self.config.count <= 0 or iterations < self.config.count:
                self.send_telemetry()
                iterations += 1
                if (self.config.count > 0
                        and iterations >= self.config.count):
                    break
                time.sleep(self.config.interval)
        except KeyboardInterrupt:
            LOGGER.warning("收到中断，正在退出")
        finally:
            self.disconnect_devices()
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
            LOGGER.info("汇总 devices=%s packets=%s",
                        len(self.states), iterations)
        return 0


def run_dry_run(
        config: SimulatorConfig,
        devices: List[Dict[str, str]],
        rng: random.Random) -> int:
    states = [
        DeviceState(
            name=device["name"],
            device_type=device["type"],
            temperature=rng.uniform(20, 30),
            humidity=rng.uniform(40, 70),
            voltage=rng.uniform(215, 225),
            current=rng.uniform(1, 10),
        )
        for device in devices
    ]
    for state in states:
        print(
            f"[dry-run] {CONNECT_TOPIC} "
            f"{json.dumps({'device': state.name, 'type': state.device_type}, ensure_ascii=False)}")
    timestamp = now_ms()
    payload = {
        state.name: [{"ts": timestamp, "values": state.advance(rng)}]
        for state in states
    }
    print(
        f"[dry-run] {TELEMETRY_TOPIC} "
        f"{json.dumps(payload, ensure_ascii=False)}")
    if config.publish_attributes:
        attributes = {
            state.name: state.attributes() for state in states
        }
        print(
            f"[dry-run] {ATTRIBUTES_TOPIC} "
            f"{json.dumps(attributes, ensure_ascii=False)}")
    for state in states:
        print(
            f"[dry-run] {DISCONNECT_TOPIC} "
            f"{json.dumps({'device': state.name}, ensure_ascii=False)}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="模拟网关和子设备通过 ThingsBoard MQTT 上报数据。",
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
        "--gateway-token",
        default=None,
        help="网关设备 Access Token；--dry-run 时可省略",
    )
    connection.add_argument(
        "--gateway-name",
        default="gateway-01",
        help="网关设备名称，同时作为 MQTT Client ID",
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

    devices = parser.add_argument_group("子设备")
    devices.add_argument(
        "--sub-devices-csv",
        default=None,
        help="子设备 CSV，读取 device_name、device_type/product_id/profile_name",
    )
    devices.add_argument(
        "--sub-device",
        action="append",
        default=[],
        metavar="NAME",
        help="子设备名称，可重复",
    )
    devices.add_argument(
        "--device-type",
        default="default",
        help="子设备类型（网关上报的 type）",
    )

    behavior = parser.add_argument_group("行为")
    behavior.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="遥测上报间隔（秒）",
    )
    behavior.add_argument(
        "--count",
        type=int,
        default=0,
        help="上报轮次，0 表示持续运行",
    )
    behavior.add_argument(
        "--publish-attributes",
        action="store_true",
        help="子设备上线时同时上报属性",
    )
    behavior.add_argument(
        "--seed",
        type=int,
        default=None,
        help="随机数种子",
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
    return SimulatorConfig(
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        gateway_token=args.gateway_token or "",
        gateway_name=args.gateway_name,
        sub_devices=[name.strip() for name in args.sub_device if name.strip()],
        interval=args.interval,
        count=args.count,
        qos=args.qos,
        keepalive=args.keepalive,
        device_type=args.device_type,
        publish_attributes=args.publish_attributes,
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

    if not args.dry_run and not args.gateway_token:
        parser.error("--gateway-token 为必填参数；使用 --dry-run 时可省略")
    if args.interval < 1:
        parser.error("--interval 不能小于 1 秒")

    config = config_from_args(args)
    try:
        csv_path = (
            Path(args.sub_devices_csv) if args.sub_devices_csv else None)
        sub_devices = load_sub_devices(config, csv_path)
    except RuntimeError as exc:
        parser.error(str(exc))

    rng = random.Random(config.seed)
    if config.dry_run:
        return run_dry_run(config, sub_devices, rng)

    try:
        return GatewaySimulator(config, sub_devices, rng).run()
    except Exception as exc:
        LOGGER.error("网关模拟器运行失败: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
