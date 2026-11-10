#!/usr/bin/env python3
"""DLT645 智能电表 MQTT 设备模拟器。

按 `thing-model/migrate/DLT645智能电表.tsl.json` 的物模型上报遥测和事件，
并订阅共享属性、RPC 下行主题，模拟一台真实电表的完整 MQTT 行为：

上行（设备 -> 平台）：
    v1/devices/me/telemetry    遥测（物模型 properties）与事件（events 数组）

下行（平台 -> 设备）：
    v1/devices/me/attributes        共享属性增量
    v1/devices/me/rpc/request/+     RPC 请求
    v1/devices/me/rpc/response/{id} RPC 响应

规则链约定（thing-model 生成的 <ProductId> 规则链）：

- 遥测报文里不能带 `events` 键，否则整条报文会被当作事件批处理；
- 事件单独发一条报文，用 `events` 数组，同一批事件的 `event_id` 必须一致；
- 事件字段为 `event_id` / `event_type` / `event_ts` + 物模型 params；
- 单条报文 JSON <= 4096 字符。

用法：

    # 自动创建（或复用）设备并连接本机 ThingsBoard 的 MQTT
    python tools/src/main/python/simulators/simulate_dlt645_meter.py \
        --product-id YUMRMRPOGP --device-name DLT645-0001 --interval 5

    # 已有 Access Token，跳过 HTTP 开通，只跑 MQTT
    python tools/src/main/python/simulators/simulate_dlt645_meter.py \
        --access-token <token> --device-name DLT645-0001

    # 只看报文，不连平台
    python tools/src/main/python/simulators/simulate_dlt645_meter.py --dry-run
"""
from __future__ import annotations

import argparse
import getpass
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

from simulate_telemetry import (
    ApiError,
    ThingsBoardClient,
    find_tsl_schema,
    load_tsl,
)

TOPIC_TELEMETRY = "v1/devices/me/telemetry"
TOPIC_ATTRIBUTES = "v1/devices/me/attributes"
TOPIC_RPC_REQUEST = "v1/devices/me/rpc/request/+"
TOPIC_RPC_RESPONSE = "v1/devices/me/rpc/response/"

DEFAULT_PRODUCT_ID = "YUMRMRPOGP"
DEFAULT_PRODUCT_NAME = "DLT645智能电表"
DEFAULT_TSL = (
    Path(__file__).resolve().parents[5]
    / "thing-model"
    / "migrate"
    / f"{DEFAULT_PRODUCT_NAME}.tsl.json"
)

# 物模型范围上限，超出会被规则链判为非法
LIMITS = {
    "UA_V": (0.0, 300.0),
    "UB_V": (0.0, 300.0),
    "UC_V": (0.0, 300.0),
    "IA_A": (0.0, 100.0),
    "IB_A": (0.0, 100.0),
    "IC_A": (0.0, 100.0),
    "P_kW": (0.0, 1000.0),
    "Q_kvar": (0.0, 1000.0),
    "S_kVA": (0.0, 1000.0),
    "PF": (0.0, 1.0),
    "F_Hz": (45.0, 65.0),
    "forwardActiveEnergy_kWh": (0.0, 99999999.0),
    "reverseActiveEnergy_kWh": (0.0, 99999999.0),
    "combinedActiveEnergy_kWh": (0.0, 99999999.0),
    "forwardReactiveEnergy_kvarh": (0.0, 99999999.0),
    "reverseReactiveEnergy_kvarh": (0.0, 99999999.0),
}

EVENT_TYPES = {
    "powerFailure": "alert",
    "phaseLoss": "alert",
    "overVoltage": "alert",
    "underVoltage": "alert",
    "overCurrent": "alert",
    "meterFault": "fault",
}

PHASES = ("A", "B", "C", "ALL")


def now_ms() -> int:
    return int(time.time() * 1000)


def clamp(value: float, name: str) -> float:
    low, high = LIMITS[name]
    return max(low, min(high, value))


def round_to(value: float, digits: int = 3) -> float:
    return round(value, digits)


class MeterModel:
    """一台三相 DLT645 电表的运行状态与读数生成。"""

    def __init__(self, rng: random.Random, report_interval: int) -> None:
        self.rng = rng
        self.report_interval = max(5, min(3600, int(report_interval)))
        self.relay_on = True
        self.load_kw = rng.uniform(1.5, 4.0)
        self.meter_status = 0
        self.clock_offset_ms = 0
        self.energies = {
            "forwardActiveEnergy_kWh": rng.uniform(1000.0, 5000.0),
            "reverseActiveEnergy_kWh": 0.0,
            "combinedActiveEnergy_kWh": 0.0,
            "forwardReactiveEnergy_kvarh": rng.uniform(200.0, 900.0),
            "reverseReactiveEnergy_kvarh": 0.0,
        }
        self.meter_info = {
            "meterNo": "000000000123",
            "manufacturer": "ZHG",
            "model": "DTZY-3P",
            "protocolVersion": "DL/T645-2007",
            "softwareVersion": "V1.2.3",
            "hardwareVersion": "HW-1.0",
            "assetNo": "ASSET-0001",
        }

    def meter_time_ms(self) -> int:
        return now_ms() + self.clock_offset_ms

    def reading(self, elapsed_seconds: float) -> Dict[str, Any]:
        """生成一帧遥测；elapsed_seconds 用于累加电能。"""
        self.load_kw = min(9.0, max(0.3, self.load_kw + self.rng.uniform(-0.25, 0.25)))
        load = 0.0 if not self.relay_on else self.load_kw

        pf = min(0.999, max(0.85, self.rng.gauss(0.96, 0.015)))
        ua = 220.0 + self.rng.gauss(0.0, 1.2)
        ub = 220.0 + self.rng.gauss(0.0, 1.2)
        uc = 220.0 + self.rng.gauss(0.0, 1.2)

        p_kw = load * pf
        q_kvar = abs(load * math.tan(math.acos(pf)))
        s_kva = math.hypot(p_kw, q_kvar)
        current = (p_kw * 1000.0) / (3.0 * 220.0 * pf) if pf else 0.0
        ia = max(0.0, current + self.rng.gauss(0.0, 0.02))
        ib = max(0.0, current + self.rng.gauss(0.0, 0.02))
        ic = max(0.0, current + self.rng.gauss(0.0, 0.02))
        frequency = 50.0 + self.rng.gauss(0.0, 0.02)

        delta_hours = max(0.0, elapsed_seconds) / 3600.0
        self.energies["forwardActiveEnergy_kWh"] += p_kw * delta_hours
        self.energies["forwardReactiveEnergy_kvarh"] += q_kvar * delta_hours
        self.energies["combinedActiveEnergy_kWh"] = (
            self.energies["forwardActiveEnergy_kWh"]
            + self.energies["reverseActiveEnergy_kWh"]
        )

        return {
            "UA_V": round_to(clamp(ua, "UA_V"), 2),
            "UB_V": round_to(clamp(ub, "UB_V"), 2),
            "UC_V": round_to(clamp(uc, "UC_V"), 2),
            "IA_A": round_to(clamp(ia, "IA_A"), 3),
            "IB_A": round_to(clamp(ib, "IB_A"), 3),
            "IC_A": round_to(clamp(ic, "IC_A"), 3),
            "P_kW": round_to(clamp(p_kw, "P_kW"), 3),
            "Q_kvar": round_to(clamp(q_kvar, "Q_kvar"), 3),
            "S_kVA": round_to(clamp(s_kva, "S_kVA"), 3),
            "PF": round_to(clamp(pf, "PF"), 3),
            "F_Hz": round_to(clamp(frequency, "F_Hz"), 2),
            "forwardActiveEnergy_kWh": round_to(
                clamp(self.energies["forwardActiveEnergy_kWh"],
                      "forwardActiveEnergy_kWh"), 2),
            "reverseActiveEnergy_kWh": round_to(
                clamp(self.energies["reverseActiveEnergy_kWh"],
                      "reverseActiveEnergy_kWh"), 2),
            "combinedActiveEnergy_kWh": round_to(
                clamp(self.energies["combinedActiveEnergy_kWh"],
                      "combinedActiveEnergy_kWh"), 2),
            "forwardReactiveEnergy_kvarh": round_to(
                clamp(self.energies["forwardReactiveEnergy_kvarh"],
                      "forwardReactiveEnergy_kvarh"), 2),
            "reverseReactiveEnergy_kvarh": round_to(
                clamp(self.energies["reverseReactiveEnergy_kvarh"],
                      "reverseReactiveEnergy_kvarh"), 2),
            "meterStatus": int(self.meter_status),
            "relayState": bool(self.relay_on),
            "reportInterval": int(self.report_interval),
            "lastReadTime": self.meter_time_ms(),
        }

    def event(self, name: Optional[str] = None) -> Dict[str, Any]:
        """生成一条物模型事件，字段与规则链事件校验约定一致。"""
        event_id = name or self.rng.choice(list(EVENT_TYPES.keys()))
        phase = self.rng.choice(PHASES)
        base: Dict[str, Any] = {
            "event_id": event_id,
            "event_type": EVENT_TYPES.get(event_id, "info"),
            "event_ts": self.meter_time_ms(),
        }
        if event_id in ("powerFailure", "phaseLoss"):
            base["phase"] = phase
            base["eventTs"] = self.meter_time_ms()
        elif event_id in ("overVoltage", "underVoltage"):
            threshold = 250.0 if event_id == "overVoltage" else 190.0
            voltage = 255.0 if event_id == "overVoltage" else 185.0
            base["phase"] = phase if phase != "ALL" else "A"
            base["voltage"] = round_to(clamp(voltage, "UA_V"), 2)
            base["threshold"] = round_to(clamp(threshold, "UA_V"), 2)
        elif event_id == "overCurrent":
            base["phase"] = phase if phase != "ALL" else "A"
            base["current"] = round_to(clamp(105.0, "IA_A"), 2)
            base["threshold"] = round_to(clamp(100.0, "IA_A"), 2)
        else:  # meterFault
            base["code"] = "E-1001"
            base["message"] = "计量芯片通信异常"
        return base

    def apply_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        applied: Dict[str, Any] = {}
        if "reportInterval" in attributes:
            try:
                value = int(attributes["reportInterval"])
            except (TypeError, ValueError):
                value = self.report_interval
            self.report_interval = max(5, min(3600, value))
            applied["reportInterval"] = self.report_interval
        if "relayState" in attributes:
            self.relay_on = bool(attributes["relayState"])
            applied["relayState"] = self.relay_on
        if "meterStatus" in attributes:
            applied["meterStatus"] = self.meter_status
        return applied


class MeterDevice:
    """MQTT 设备端：上行遥测/事件，下行共享属性与 RPC。"""

    def __init__(
        self,
        args: argparse.Namespace,
        access_token: str,
        device_name: str,
        model: MeterModel,
    ) -> None:
        self.args = args
        self.access_token = access_token
        self.device_name = device_name
        self.model = model
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.reports = 0
        self.events_sent = 0
        self.rpc_handled = 0
        self._stopping = False

    # ---- MQTT 生命周期 -------------------------------------------------
    def build_client(self) -> mqtt.Client:
        if hasattr(mqtt, "CallbackAPIVersion"):
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.device_name,
                protocol=mqtt.MQTTv311,
            )
        else:  # paho-mqtt 1.x
            client = mqtt.Client(client_id=self.device_name,
                                 protocol=mqtt.MQTTv311)
        client.username_pw_set(self.access_token, "")
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        if self.args.mqtt_tls:
            client.tls_set()
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_message
        self.client = client
        return client

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        value = getattr(reason_code, "value", reason_code)
        if value != 0:
            print(f"MQTT connect rejected: {reason_code}", file=sys.stderr)
            return
        self.connected = True
        client.subscribe(TOPIC_ATTRIBUTES, qos=1)
        client.subscribe(TOPIC_RPC_REQUEST, qos=1)
        print(
            f"MQTT connected {self.args.mqtt_host}:{self.args.mqtt_port} "
            f"device={self.device_name}; subscribed attributes + rpc")

    def on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self.connected = False
        print(f"MQTT disconnected: {reason_code}", file=sys.stderr)

    def on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"invalid payload on {message.topic}: {exc}", file=sys.stderr)
            return
        if not isinstance(payload, dict):
            print(f"payload must be an object on {message.topic}", file=sys.stderr)
            return
        if message.topic == TOPIC_ATTRIBUTES:
            self.handle_attributes(payload)
        elif message.topic.startswith("v1/devices/me/rpc/request/"):
            request_id = message.topic.rsplit("/", 1)[-1]
            self.handle_rpc(client, request_id, payload)

    # ---- 下行处理 ------------------------------------------------------
    def handle_attributes(self, payload: Dict[str, Any]) -> None:
        applied = self.model.apply_attributes(payload)
        print(f"[attributes] {json.dumps(payload, ensure_ascii=False)} -> {applied}")

    def handle_rpc(self, client: mqtt.Client, request_id: str,
                   payload: Dict[str, Any]) -> None:
        method = payload.get("method")
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        result = self.dispatch_rpc(method, params)
        client.publish(
            f"{TOPIC_RPC_RESPONSE}{request_id}",
            json.dumps(result, ensure_ascii=False),
            qos=1,
        )
        self.rpc_handled += 1
        print(f"[rpc] {method} {json.dumps(params, ensure_ascii=False)} "
              f"-> {json.dumps(result, ensure_ascii=False)}")

    def dispatch_rpc(self, method: Optional[str],
                     params: Dict[str, Any]) -> Dict[str, Any]:
        if method == "setRelay":
            on = params.get("on")
            if not isinstance(on, bool):
                return {"success": False, "error": "invalid relay state"}
            self.model.relay_on = on
            return {"success": True, "relayState": on}

        if method == "applyConfig":
            value = params.get("reportInterval")
            if not isinstance(value, int) or isinstance(value, bool):
                return {"success": False, "error": "invalid reportInterval"}
            if not 5 <= value <= 3600:
                return {"success": False, "error": "reportInterval out of range"}
            self.model.report_interval = value
            return {"success": True, "reportInterval": value}

        if method == "syncTime":
            target = params.get("time")
            if not isinstance(target, int) or isinstance(target, bool):
                return {"success": False, "error": "invalid time"}
            self.model.clock_offset_ms = target - now_ms()
            return {"success": True, "time": target}

        if method == "set":
            applied = self.model.apply_attributes(params)
            if not applied:
                return {"success": False, "error": "no supported key"}
            return {"success": True, "applied": applied}

        if method == "getMeterInfo":
            return {"success": True, "meterInfo": self.model.meter_info}

        if method == "getConfig":
            return {
                "success": True,
                "reportInterval": self.model.report_interval,
                "relayState": self.model.relay_on,
                "meterStatus": self.model.meter_status,
            }

        return {"success": False, "error": f"unsupported method: {method}"}

    # ---- 上行 ----------------------------------------------------------
    def publish_telemetry(self, include_meter_info: bool) -> None:
        payload = self.model.reading(self.model.report_interval)
        if include_meter_info:
            payload["meterInfo"] = self.model.meter_info
        self._publish(TOPIC_TELEMETRY, payload, "telemetry")
        self.reports += 1

    def publish_event(self, name: Optional[str] = None) -> None:
        event = self.model.event(name)
        self._publish(TOPIC_TELEMETRY, {"events": [event]}, "event")
        self.events_sent += 1

    def _publish(self, topic: str, payload: Dict[str, Any], kind: str) -> None:
        encoded = json.dumps(payload, ensure_ascii=False)
        if len(encoded) > 4096:
            print(f"[{kind}] skipped: payload {len(encoded)} > 4096 chars",
                  file=sys.stderr)
            return
        if self.args.dry_run:
            print(f"[dry-run] {topic} {encoded}")
            return
        assert self.client is not None
        info = self.client.publish(topic, encoded, qos=1)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            print(f"[{kind}] publish failed rc={info.rc}", file=sys.stderr)
            return
        if kind == "telemetry" and self.args.quiet:
            return
        print(f"[{kind}] {encoded}")

    # ---- 主循环 --------------------------------------------------------
    def run(self, count: int, interval: float, meter_info_every: int,
            event_every: int) -> int:
        assert self.client is not None
        self.client.connect(self.args.mqtt_host, self.args.mqtt_port,
                            keepalive=60)
        self.client.loop_start()
        try:
            last = time.monotonic()
            index = 0
            while count <= 0 or index < count:
                if not self.connected:
                    time.sleep(0.2)
                    continue
                delay = max(0.0, self.model.report_interval - interval)
                if index > 0 and delay > 0:
                    time.sleep(delay)
                elapsed = time.monotonic() - last
                last = time.monotonic()
                include_info = index == 0 or (
                    meter_info_every > 0 and index % meter_info_every == 0)
                self.publish_telemetry(include_info)
                if event_every > 0 and index > 0 and index % event_every == 0:
                    self.publish_event()
                index += 1
                _ = elapsed
        except KeyboardInterrupt:
            print("\ninterrupted", file=sys.stderr)
        finally:
            self.client.disconnect()
            self.client.loop_stop()
        print(f"summary reports={self.reports} events={self.events_sent} "
              f"rpc={self.rpc_handled}")
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="模拟 DLT645 智能电表通过 MQTT 上报遥测/事件并响应下行 RPC。")
    parser.add_argument("--tb-url",
                        default=os.getenv("TB_URL", "http://localhost:18080"),
                        help="ThingsBoard HTTP 地址（用于开通设备）")
    parser.add_argument("--thingmodel-url",
                        default=os.getenv("THINGMODEL_URL", "http://localhost:8090"),
                        help="thing-model 地址（用于读取产品信息）")
    parser.add_argument("--username",
                        default=os.getenv("TB_USERNAME", "tenant@thingsboard.org"),
                        help="ThingsBoard 租户管理员账号")
    parser.add_argument("--password", default=os.getenv("TB_PASSWORD"),
                        help="ThingsBoard 密码；默认读 TB_PASSWORD 或交互输入")
    parser.add_argument("--api-key", default=os.getenv("TB_API_KEY"),
                        help="ThingsBoard API Key；优先于账号密码")
    parser.add_argument("--product-id", default=DEFAULT_PRODUCT_ID,
                        help="产品 ID")
    parser.add_argument("--tsl", default=str(DEFAULT_TSL),
                        help="本地 TSL 文件；为空时从 thing-model 读取")
    parser.add_argument("--device-name", default="DLT645-0001",
                        help="设备名，同时作为 MQTT Client ID")
    parser.add_argument("--access-token", default=os.getenv("ACCESS_TOKEN"),
                        help="设备 Access Token；不传则通过 HTTP 创建/复用设备")
    parser.add_argument("--site-code", default=os.getenv("SITE_CODE", "SIM"),
                        help="设备 site_code 服务端属性")
    parser.add_argument("--mqtt-host",
                        default=os.getenv("MQTT_HOST", "localhost"),
                        help="MQTT Broker 地址")
    parser.add_argument("--mqtt-port", type=int,
                        default=int(os.getenv("MQTT_PORT", "1883")),
                        help="MQTT Broker 端口")
    parser.add_argument("--mqtt-tls", action="store_true",
                        help="使用 TLS（8883）")
    parser.add_argument("--interval", type=float, default=5.0,
                        help="上报间隔秒数（共享属性 reportInterval 会覆盖）")
    parser.add_argument("--count", type=int, default=0,
                        help="上报次数；0 表示一直运行")
    parser.add_argument("--meter-info-every", type=int, default=12,
                        help="每多少次上报带一次 meterInfo；0 表示只发首帧")
    parser.add_argument("--event-every", type=int, default=30,
                        help="每多少次上报发一条随机事件；0 表示不发事件")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument("--quiet", action="store_true",
                        help="不打印每帧遥测报文")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印报文，不连接 HTTP/MQTT")
    parser.add_argument("--timeout", type=float, default=10.0,
                        help="HTTP 超时秒数")
    return parser.parse_args()


def provision_device(args: argparse.Namespace) -> Dict[str, Any]:
    """通过 HTTP 创建/复用产品下的设备，返回设备信息与 Access Token。"""
    client = ThingsBoardClient(args.tb_url, args.thingmodel_url, args.timeout)

    token = args.api_key or None
    if token:
        try:
            token = client.exchange_api_key_for_token(token)
        except Exception:  # noqa: BLE001
            token = client.api_key_token(args.api_key)
    else:
        password = args.password or getpass.getpass(
            f"ThingsBoard password for {args.username}: ")
        token = client.login(args.username, password)

    product = client.get_product(token, args.product_id)
    product_info = product.get("product") or {}
    profile_id = product_info.get("tbProfileId")
    asset_id = product_info.get("tbAssetId")
    tenant_id = product_info.get("tenantId")
    if not profile_id or not asset_id or not tenant_id:
        raise ApiError("product is missing tbProfileId, tbAssetId or tenantId; "
                       "run product sync first")

    device = client.find_device_by_name(token, args.device_name)
    created = False
    if not device:
        device = client.create_device(
            token, profile_id, args.device_name,
            label=f"{args.product_id} {args.device_name}")
        created = True
    device_id = device["id"]["id"]

    credentials = client.get_credentials(token, device_id)
    access_token = credentials["credentialsId"]

    tsl = load_tsl(args.tsl) if args.tsl and Path(args.tsl).is_file() else None
    tsl_version = (product_info.get("tslVersion")
                   or (tsl or {}).get("version") or "1.0")
    tsl_schema = find_tsl_schema(client.get_asset_attributes(token, asset_id))
    client.set_server_attributes(token, device_id, {
        "tsl_schema": tsl_schema,
        "tsl_version": tsl_version,
        "tenant_id": tenant_id,
        "device_uuid": device_id,
        "site_code": args.site_code,
        "product_id": args.product_id,
    })

    print(f"device={args.device_name} id={device_id} "
          f"{'created' if created else 'reused'} product={args.product_id} "
          f"tslVersion={tsl_version}")
    return {
        "device_id": device_id,
        "access_token": access_token,
        "tsl_version": tsl_version,
    }


def main() -> int:
    args = parse_args()

    if args.tsl and not Path(args.tsl).is_file():
        print(f"warning: TSL file not found: {args.tsl}", file=sys.stderr)
        args.tsl = ""

    model = MeterModel(random.Random(args.seed), int(args.interval))

    access_token = args.access_token
    if not access_token:
        if args.dry_run:
            access_token = "dry-run-token"
        else:
            try:
                info = provision_device(args)
            except Exception as exc:  # noqa: BLE001
                print(f"error: device provisioning failed: {exc}", file=sys.stderr)
                return 1
            access_token = info["access_token"]

    if args.dry_run:
        print("[dry-run] 首帧遥测:")
        model.reading(float(args.interval))
        payload = model.reading(float(args.interval))
        payload["meterInfo"] = model.meter_info
        print(json.dumps(payload, ensure_ascii=False))
        for name in EVENT_TYPES:
            print(json.dumps({"events": [model.event(name)]},
                             ensure_ascii=False))
        return 0

    device = MeterDevice(args, access_token, args.device_name, model)
    client = device.build_client()
    try:
        client.connect(args.mqtt_host, args.mqtt_port, keepalive=60)
    except Exception as exc:  # noqa: BLE001
        print(f"error: MQTT connect failed: {exc}", file=sys.stderr)
        return 1
    return device.run(args.count, args.interval, args.meter_info_every,
                      args.event_every)


if __name__ == "__main__":
    raise SystemExit(main())
