import argparse
import json
import os
import random
import signal
import sys
import time

import paho.mqtt.client as mqtt

# ===== 默认配置 =====
DEFAULT_HOST = os.getenv("TB_HOST", "localhost")
DEFAULT_PORT = int(os.getenv("TB_PORT", "1883"))
DEFAULT_TOKEN = os.getenv("TB_TOKEN", "")
DEFAULT_INTERVAL = int(os.getenv("INTERVAL", "5"))

DEVICE_NAME = "AQM0001"
PRODUCT_ID = "BDSM4K7T2Q"

TELEMETRY_TOPIC = "v1/devices/me/telemetry"
ATTRIBUTES_TOPIC = "v1/devices/me/attributes"

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


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] 连接成功")
        client.publish(ATTRIBUTES_TOPIC, json.dumps({
            "deviceName": DEVICE_NAME,
            "productId": PRODUCT_ID,
            "firmwareVersion": "1.1.0",
            "mock": True,
        }, ensure_ascii=False), qos=1)
    else:
        print(f"[MQTT] 连接失败，返回码: {rc}")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"[MQTT] 意外断开，返回码: {rc}，将自动重连")


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


def main():
    parser = argparse.ArgumentParser(description="AQM0001 设备数据模拟上报")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="设备 Access Token")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="上报周期（秒）")
    parser.add_argument("--count", type=int, default=0, help="上报条数，0 表示一直上报")
    parser.add_argument("--alert-ratio", type=float, default=0.1,
                        help="触发告警数据的比例，0~1")
    parser.add_argument("--altitude-start", type=float, default=500.0,
                        help="海拔初始值（m）")
    parser.add_argument("--tls", action="store_true", help="启用 TLS")
    parser.add_argument("--ca", default=None, help="CA 证书路径（TLS 时使用）")
    args = parser.parse_args()

    if not args.token:
        sys.exit("请通过 --token 或环境变量 TB_TOKEN 提供设备 Access Token")

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    client = mqtt.Client(client_id=f"{DEVICE_NAME}-mock")
    client.username_pw_set(args.token)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    if args.tls:
        client.tls_set(ca_certs=args.ca)

    client.connect(args.host, args.port, keepalive=60)
    client.loop_start()

    alt_sim = AltitudeSimulator(args.altitude_start)
    sent = 0
    try:
        while _running:
            force_alert = random.random() < args.alert_ratio
            payload = build_payload(alt_sim, force_alert)
            info = client.publish(TELEMETRY_TOPIC, json.dumps(payload), qos=1)
            info.wait_for_publish()

            sent += 1
            flag = " [告警数据]" if force_alert else ""
            print(f"[{sent}] {payload}{flag}")

            if args.count and sent >= args.count:
                break
            time.sleep(args.interval)
    finally:
        client.loop_stop()
        client.disconnect()
        print(f"已停止，共上报 {sent} 条")


if __name__ == "__main__":
    main()