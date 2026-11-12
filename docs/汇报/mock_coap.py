import argparse
import asyncio
import json
import os
import random
import signal
import sys
import time

try:
    from aiocoap import Code, Context, Message
except ImportError:
    sys.exit("缺少依赖 aiocoap，请执行: pip install aiocoap")

# ===== 默认配置 =====
DEFAULT_HOST = os.getenv("TB_HOST", "localhost")
DEFAULT_PORT = int(os.getenv("TB_PORT", "5683"))
DEFAULT_TOKEN = os.getenv("TB_TOKEN", "")
DEFAULT_INTERVAL = int(os.getenv("INTERVAL", "5"))
DEFAULT_TIMEOUT = int(os.getenv("COAP_TIMEOUT", "10"))

DEVICE_NAME = "AQM0001"
PRODUCT_ID = "BDSM4K7T2Q"

TELEMETRY_PATH = "/api/v1/{token}/telemetry"
ATTRIBUTES_PATH = "/api/v1/{token}/attributes"

# CoAP Content-Format: application/json
CONTENT_FORMAT_JSON = 50

# 物模型属性 id（必须与平台一致）
KEYS = [
    "temperature", "humidity", "battery",
    "altitude", "latitude", "longitude", "helmetWorn",
]

# 告警阈值
ALTITUDE_ALERT = 1000.0     # 海拔超限（m）
TEMPERATURE_ALERT = 38.0    # 温度超限（℃）
BATTERY_LOW = 20            # 电量过低（%）

# 海拔模拟范围（与物模型 -500 ~ 9000 保持一致）
ALTITUDE_MIN = 0.0
ALTITUDE_MAX = 9000.0

_running = True


def _stop(signum, frame):
    global _running
    _running = False


class AltitudeSimulator:
    """海拔缓慢漂移模拟器"""

    def __init__(self, start: float = 500.0):
        self.value = max(ALTITUDE_MIN, min(ALTITUDE_MAX, start))

    def next(self) -> float:
        self.value += random.uniform(-8.0, 8.0)
        self.value = max(ALTITUDE_MIN, min(ALTITUDE_MAX, self.value))
        return round(self.value, 1)

    def force_high(self) -> float:
        """强制抬升到告警阈值以上"""
        self.value = random.uniform(ALTITUDE_ALERT + 50, 1500.0)
        return round(self.value, 1)


def build_values(alt_sim: AltitudeSimulator, force_alert: bool = False):
    """按物模型生成一条模拟遥测值"""
    values = {
        "temperature": round(random.uniform(20.0, 36.0), 1),
        "humidity": round(random.uniform(30.0, 80.0), 1),
        "battery": random.randint(40, 100),
        "altitude": alt_sim.next(),
        "latitude": round(random.uniform(30.0, 32.0), 6),
        "longitude": round(random.uniform(118.0, 120.0), 6),
        "helmetWorn": random.choice([True, True, True, False]),
    }

    if force_alert:
        values["altitude"] = alt_sim.force_high()
        values["temperature"] = round(random.uniform(TEMPERATURE_ALERT + 1, 42.0), 1)
        values["battery"] = random.randint(5, BATTERY_LOW - 1)

    return values


def build_payload(alt_sim: AltitudeSimulator, force_alert: bool = False):
    return {
        "ts": int(time.time() * 1000),
        "values": build_values(alt_sim, force_alert),
    }


async def post_json(context, uri, payload, timeout):
    request = Message(
        code=Code.POST,
        uri=uri,
        payload=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        content_format=CONTENT_FORMAT_JSON,
    )
    return await asyncio.wait_for(context.request(request).response, timeout=timeout)


async def run(args):
    base_url = f"coap://{args.host}:{args.port}"
    telemetry_uri = base_url + TELEMETRY_PATH.format(token=args.token)
    attributes_uri = base_url + ATTRIBUTES_PATH.format(token=args.token)

    context = await Context.create_client_context()
    try:
        attributes = {
            "deviceName": DEVICE_NAME,
            "productId": PRODUCT_ID,
            "firmwareVersion": "1.1.0",
            "mock": True,
        }
        try:
            response = await post_json(context, attributes_uri, attributes, args.timeout)
            if response.code.is_successful():
                print("[CoAP] 属性上报成功")
            else:
                print(f"[CoAP] 属性上报失败，响应码: {response.code}")
        except Exception as exc:
            print(f"[CoAP] 属性上报异常: {exc}")

        alt_sim = AltitudeSimulator(args.altitude_start)
        sent = 0
        while _running:
            force_alert = random.random() < args.alert_ratio
            payload = build_payload(alt_sim, force_alert)
            flag = " [告警数据]" if force_alert else ""
            try:
                response = await post_json(context, telemetry_uri, payload, args.timeout)
                if response.code.is_successful():
                    sent += 1
                    print(f"[{sent}] CoAP {response.code} {payload}{flag}")
                else:
                    print(f"[CoAP] 上报失败，响应码: {response.code}")
            except Exception as exc:
                print(f"[CoAP] 上报异常: {exc}")

            if args.count and sent >= args.count:
                break
            await asyncio.sleep(args.interval)

        print(f"已停止，共上报 {sent} 条")
    finally:
        await context.shutdown()


def main():
    parser = argparse.ArgumentParser(description="AQM0001 设备 CoAP 数据模拟上报")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="设备 Access Token")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="上报周期（秒）")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="请求超时（秒）")
    parser.add_argument("--count", type=int, default=0, help="上报条数，0 表示一直上报")
    parser.add_argument("--alert-ratio", type=float, default=0.1,
                        help="触发告警数据的比例，0~1")
    parser.add_argument("--altitude-start", type=float, default=500.0,
                        help="海拔初始值（m）")
    args = parser.parse_args()

    if not args.token:
        sys.exit("请通过 --token 或环境变量 TB_TOKEN 提供设备 Access Token")

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
