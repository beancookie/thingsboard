#!/usr/bin/env python3
"""DLT645 电表 CoAP 模拟器示例。

通过设备 Access Token 使用 ThingsBoard CoAP 传输上报电表遥测和事件，
使用 Observe 接收共享属性和 RPC 下发。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

try:
    import aiocoap
except ImportError:  # pragma: no cover
    aiocoap = None

LOGGER = logging.getLogger("dlt645-meter-coap")

CONTENT_FORMAT_JSON = 50
DEFAULT_COAP_HOST = "129.211.239.15"
DEFAULT_COAP_PORT = 5683
DEFAULT_TSL_PATH = Path(__file__).with_name("dlt645_meter_thing_model.tsl.json")

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
class CoapConfig:
    coap_host: str
    coap_port: int
    token: str
    tsl_path: Path
    interval: float
    event_interval: float
    count: int
    seed: Optional[int]
    relay_on: bool
    observe: bool
    timeout: float
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


def load_tsl(path: str) -> Dict[str, Any]:
    tsl_path = Path(path)
    if not tsl_path.is_file():
        raise RuntimeError(f"TSL 文件不存在: {tsl_path}")
    with tsl_path.open(encoding="utf-8-sig") as stream:
        tsl = json.load(stream)
    if not isinstance(tsl, dict):
        raise RuntimeError(f"TSL 文件必须是 JSON 对象: {tsl_path}")
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
        self.forward_active = float(starts.get("forwardActiveEnergy_kWh", 0))
        self.reverse_active = float(starts.get("reverseActiveEnergy_kWh", 0))
        self.combined_active = float(starts.get("combinedActiveEnergy_kWh", 0))
        self.forward_reactive = float(starts.get("forwardReactiveEnergy_kvarh", 0))
        self.reverse_reactive = float(starts.get("reverseReactiveEnergy_kvarh", 0))
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
            value = max(state.ua + rng.uniform(10, 25), 230 + rng.uniform(0.1, 20))
            return round(clamp(value, 0, 300), 2)
        if event_id == "underVoltage":
            value = min(state.ua - rng.uniform(20, 40), 180 - rng.uniform(0.1, 20))
            return round(clamp(value, 0, 300), 2)
        return round(state.ua, 2)
    if param_id == "current":
        value = max(max(state.ia, state.ib, state.ic) + rng.uniform(1, 5),
                    10 + rng.uniform(0.1, 5))
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
        return rng.choice(["计量芯片异常", "采样回路异常", "存储器异常", "通信异常"])
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
            values[param_id] = event_param_value(event_id, param, state, rng, event_ts)
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


def endpoint_base(config: CoapConfig) -> str:
    return f"coap://{config.coap_host}:{config.coap_port}/api/v1/{config.token}"


def telemetry_uri(config: CoapConfig) -> str:
    return f"{endpoint_base(config)}/telemetry"


def attributes_uri(config: CoapConfig) -> str:
    return f"{endpoint_base(config)}/attributes"


def rpc_uri(config: CoapConfig) -> str:
    return f"{endpoint_base(config)}/rpc"


def rpc_response_uri(config: CoapConfig, request_id: Any) -> str:
    return f"{endpoint_base(config)}/rpc/{quote(str(request_id))}"


async def send_json(context: Any, code: Any, uri: str, payload: Any, timeout: float) -> Any:
    message = aiocoap.Message(code=code, uri=uri)
    message.payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    message.opt.content_format = CONTENT_FORMAT_JSON
    return await asyncio.wait_for(context.request(message).response, timeout=timeout)


class CoapMeterSimulator:
    def __init__(self, config: CoapConfig, tsl: Dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.tsl = tsl
        self.rng = rng
        self.state = MeterState(tsl, config.interval, rng, relay_on=config.relay_on)
        self.lock = asyncio.Lock()
        self.context = None
        self.telemetry_interval = max(5.0, float(config.interval))
        self.telemetry_count = 0
        self.event_count = 0
        self.rpc_count = 0

    async def publish_telemetry(self) -> None:
        async with self.lock:
            payload = build_telemetry(self.state)
        response = await send_json(
            self.context, aiocoap.POST, telemetry_uri(self.config), payload,
            self.config.timeout)
        if not response.code.is_successful():
            raise RuntimeError(f"遥测上报失败: {response.code}")
        self.telemetry_count += 1
        LOGGER.info("[telemetry] %s", json.dumps(payload, ensure_ascii=False))

    async def publish_event(self) -> None:
        async with self.lock:
            event = build_event(self.tsl, self.state, self.rng)
        response = await send_json(
            self.context, aiocoap.POST, telemetry_uri(self.config),
            {"events": [event]}, self.config.timeout)
        if not response.code.is_successful():
            raise RuntimeError(f"事件上报失败: {response.code}")
        self.event_count += 1
        LOGGER.info("[event] %s", json.dumps(event, ensure_ascii=False))

    async def observe_attributes(self) -> None:
        request = aiocoap.Message(code=aiocoap.GET, uri=attributes_uri(self.config))
        request.opt.observe = 0
        pending = self.context.request(request)
        response = await asyncio.wait_for(pending.response, timeout=self.config.timeout)
        if not response.code.is_successful() or pending.observation is None:
            LOGGER.warning("共享属性 Observe 未建立: %s", response.code)
            return
        LOGGER.info("已订阅共享属性 Observe")
        async for notification in pending.observation:
            try:
                payload = json.loads(notification.payload.decode("utf-8"))
            except Exception as exc:
                LOGGER.warning("共享属性报文解析失败: %s", exc)
                continue
            if not isinstance(payload, dict) or not payload:
                continue
            async with self.lock:
                changed = apply_shared(self.state, payload)
            LOGGER.info("shared attributes %s", json.dumps(payload, ensure_ascii=False))
            if changed:
                self.apply_report_interval(self.state.report_interval)
                await self.publish_telemetry()

    async def observe_rpc(self) -> None:
        request = aiocoap.Message(code=aiocoap.GET, uri=rpc_uri(self.config))
        request.opt.observe = 0
        pending = self.context.request(request)
        response = await asyncio.wait_for(pending.response, timeout=self.config.timeout)
        if not response.code.is_successful() or pending.observation is None:
            LOGGER.warning("RPC Observe 未建立: %s", response.code)
            return
        LOGGER.info("已订阅 RPC Observe")
        async for notification in pending.observation:
            try:
                payload = json.loads(notification.payload.decode("utf-8"))
            except Exception as exc:
                LOGGER.warning("RPC 报文解析失败: %s", exc)
                continue
            if not isinstance(payload, dict) or not payload:
                continue
            request_id = payload.get("id")
            async with self.lock:
                result = handle_rpc(self.state, payload)
            if request_id is not None:
                await send_json(
                    self.context, aiocoap.POST,
                    rpc_response_uri(self.config, request_id), result,
                    self.config.timeout)
            self.rpc_count += 1
            LOGGER.info(
                "rpc method=%s response=%s",
                payload.get("method"),
                json.dumps(result, ensure_ascii=False),
            )
            if result.get("success"):
                self.apply_report_interval(self.state.report_interval)
                await self.publish_telemetry()

    async def run(self) -> int:
        if aiocoap is None:
            raise RuntimeError("未安装 aiocoap，请执行 pip install -r requirements.txt")
        self.context = await aiocoap.Context.create_client_context()
        LOGGER.info(
            "协议=CoAP 地址=%s token=%s",
            endpoint_base(self.config),
            mask_token(self.config.token),
        )
        tasks = []
        if self.config.observe:
            tasks.append(asyncio.create_task(self.observe_attributes()))
            tasks.append(asyncio.create_task(self.observe_rpc()))
            LOGGER.info("已开启共享属性和 RPC Observe")
        last_event = time.time()
        iterations = 0
        try:
            while self.config.count <= 0 or iterations < self.config.count:
                async with self.lock:
                    self.state.advance(self.telemetry_interval)
                    self.state.report_interval = max(
                        5, min(3600, int(self.telemetry_interval)))
                await self.publish_telemetry()
                iterations += 1
                if (self.config.event_interval > 0
                        and time.time() - last_event >= self.config.event_interval):
                    await self.publish_event()
                    last_event = time.time()
                if self.config.count > 0 and iterations >= self.config.count:
                    break
                await asyncio.sleep(self.telemetry_interval)
        except KeyboardInterrupt:
            LOGGER.warning("收到中断，正在退出")
        finally:
            for task in tasks:
                task.cancel()
            await self.context.shutdown()
            LOGGER.info(
                "汇总 telemetry=%s event=%s rpc=%s",
                self.telemetry_count,
                self.event_count,
                self.rpc_count,
            )
        return 0

    def apply_report_interval(self, interval: int) -> None:
        self.telemetry_interval = float(max(5, min(3600, interval)))


def run_dry_run(config: CoapConfig, tsl: Dict[str, Any], rng: random.Random) -> int:
    state = MeterState(tsl, config.interval, rng, relay_on=config.relay_on)
    state.advance(max(5.0, config.interval))
    print(f"[dry-run] POST {telemetry_uri(config)}")
    print(f"[dry-run] {json.dumps(build_telemetry(state), ensure_ascii=False)}")
    print(f"[dry-run] POST {telemetry_uri(config)}")
    print(
        "[dry-run] "
        f"{json.dumps({'events': [build_event(tsl, state, rng)]}, ensure_ascii=False)}")
    if config.observe:
        print(f"[dry-run] GET Observe {attributes_uri(config)}")
        print(f"[dry-run] GET Observe {rpc_uri(config)}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="模拟 DLT645 电表通过 ThingsBoard CoAP 传输上报数据。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    connection = parser.add_argument_group("连接")
    connection.add_argument("--coap-host", default=DEFAULT_COAP_HOST, help="CoAP 服务地址")
    connection.add_argument("--coap-port", type=int, default=DEFAULT_COAP_PORT, help="CoAP 服务端口（UDP）")
    connection.add_argument("--token", default=None, help="设备 Access Token")
    connection.add_argument("--timeout", type=float, default=30.0, help="请求超时秒数")
    behavior = parser.add_argument_group("行为")
    behavior.add_argument("--tsl", default=str(DEFAULT_TSL_PATH), help="物模型 TSL JSON 文件")
    behavior.add_argument("--interval", type=float, default=5.0, help="遥测上报间隔（秒，最小 5）")
    behavior.add_argument("--event-interval", type=float, default=30.0, help="事件上报间隔（秒，0 表示关闭）")
    behavior.add_argument("--count", type=int, default=0, help="遥测轮次，0 表示持续运行")
    behavior.add_argument("--seed", type=int, default=None, help="随机数种子")
    behavior.add_argument("--relay-off", action="store_true", help="启动时继电器为断开状态")
    behavior.add_argument("--observe", action="store_true", help="开启共享属性和 RPC Observe")
    behavior.add_argument("--dry-run", action="store_true", help="只打印示例报文，不访问平台")
    output = parser.add_argument_group("输出")
    output.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="日志级别")
    return parser


def config_from_args(args: argparse.Namespace) -> CoapConfig:
    return CoapConfig(
        coap_host=args.coap_host,
        coap_port=args.coap_port,
        token=args.token or "",
        tsl_path=Path(args.tsl),
        interval=args.interval,
        event_interval=args.event_interval,
        count=args.count,
        seed=args.seed,
        relay_on=not args.relay_off,
        observe=args.observe,
        timeout=args.timeout,
        dry_run=args.dry_run,
        log_level=args.log_level,
    )


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)
    if not args.dry_run and not args.token:
        parser.error("--token 为必填参数；使用 --dry-run 时可省略")
    if args.interval < 5:
        parser.error("--interval 不能小于 5 秒")
    if args.count < 0:
        parser.error("--count 必须大于等于 0")

    config = config_from_args(args)
    rng = random.Random(config.seed)
    try:
        tsl = load_tsl(config.tsl_path)
    except Exception as exc:
        LOGGER.error("加载物模型失败: %s", exc)
        return 1
    if config.dry_run:
        if not config.token:
            config.token = "<TOKEN>"
        return run_dry_run(config, tsl, rng)
    if aiocoap is None:
        print("error: 未安装 aiocoap，请执行 pip install -r requirements.txt", file=sys.stderr)
        return 1
    try:
        return asyncio.run(CoapMeterSimulator(config, tsl, rng).run())
    except Exception as exc:
        LOGGER.error("模拟器运行失败: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
