#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import paho.mqtt.client as mqtt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate the multi-device scene demo devices over MQTT.")
    parser.add_argument(
        "--devices-csv",
        default="import-output/scene-demo/scene-devices.csv",
        help="scene-devices.csv produced by create_scene_demo.py",
    )
    parser.add_argument(
        "--mqtt-host",
        default=os.getenv("MQTT_HOST", "localhost"),
        help="MQTT host",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=int(os.getenv("MQTT_PORT", "1883")),
        help="MQTT port",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="seconds between telemetry iterations",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="iterations; 0 means run until Ctrl+C",
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
        "--dry-run",
        action="store_true",
        help="print payloads without connecting to MQTT",
    )
    return parser.parse_args()


def load_devices(path: str) -> List[Dict[str, str]]:
    csv_path = Path(path)
    if not csv_path.is_file():
        raise RuntimeError(f"devices CSV not found: {csv_path}")
    devices: List[Dict[str, str]] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            device_name = (row.get("device_name") or "").strip()
            access_token = (row.get("access_token") or "").strip()
            if not device_name or not access_token:
                continue
            devices.append({
                "product_id": (row.get("product_id") or "").strip(),
                "device_name": device_name,
                "access_token": access_token,
                "scene_role": (row.get("scene_role") or "").strip(),
            })
    if not devices:
        raise RuntimeError(f"no usable devices found in {csv_path}")
    return devices


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


def publish(client: mqtt.Client, topic: str, payload: Dict[str, Any], qos: int) -> None:
    info = client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=qos)
    info.wait_for_publish(timeout=30)
    if not info.is_published():
        raise RuntimeError(f"MQTT publish timeout: {topic}")


def publish_async(
        client: mqtt.Client,
        topic: str,
        payload: Dict[str, Any],
        qos: int) -> None:
    client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=qos)


def sensor_payload(
        device: Dict[str, str],
        index: int,
        rng: random.Random) -> Dict[str, Any]:
    product_id = device["product_id"]
    if product_id == "SCENE_MOTION":
        return {
            "motion": index % 2 == 0,
            "battery": rng.randint(80, 100),
            "online": True,
        }
    if product_id == "SCENE_LIGHT_SENSOR":
        return {
            "illuminance": round(rng.uniform(0, 1000), 1),
            "battery": rng.randint(80, 100),
            "online": True,
        }
    if product_id == "SCENE_TEMPERATURE":
        return {
            "temperature": round(rng.uniform(20, 40), 1),
            "humidity": round(rng.uniform(30, 80), 1),
            "battery": rng.randint(80, 100),
            "online": True,
        }
    return {"online": True}


def normalize_state(value: Any) -> str:
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    text = str(value).strip().upper()
    return "ON" if text in ("ON", "TRUE", "1") else "OFF"


def normalize_mode(value: Any) -> str:
    if isinstance(value, bool):
        return "COOL" if value else "OFF"
    text = str(value).strip().upper()
    return "COOL" if text in ("COOL", "ON", "TRUE", "1") else "OFF"


def build_rpc_handler(
        device: Dict[str, str],
        state: Dict[str, Any],
        qos: int):
    device_name = device["device_name"]

    def on_message(client: mqtt.Client, userdata: Any, message: Any) -> None:
        if not message.topic.startswith("v1/devices/me/rpc/request/"):
            return
        request_id = message.topic.rsplit("/", 1)[-1]
        try:
            request = json.loads(message.payload.decode("utf-8"))
        except Exception as exc:
            print(f"[{device_name}] invalid RPC payload: {exc}", file=sys.stderr)
            return
        method = request.get("method")
        params = request.get("params")
        print(
            f"[{device_name}] RPC method={method} params="
            f"{json.dumps(params, ensure_ascii=False)}")
        try:
            if method == "setState":
                value = params.get("state") if isinstance(params, dict) else params
                state["state"] = normalize_state(value)
                publish_async(
                    client,
                    "v1/devices/me/telemetry",
                    {"state": state["state"], "online": True},
                    qos,
                )
                response = {"success": True, "state": state["state"]}
            elif method == "setMode":
                value = params.get("mode") if isinstance(params, dict) else params
                state["mode"] = normalize_mode(value)
                publish_async(
                    client,
                    "v1/devices/me/telemetry",
                    {"mode": state["mode"], "online": True},
                    qos,
                )
                response = {"success": True, "mode": state["mode"]}
            else:
                response = {
                    "success": False,
                    "error": f"unsupported method: {method}",
                }
        except Exception as exc:
            response = {"success": False, "error": str(exc)}
        publish_async(
            client,
            f"v1/devices/me/rpc/response/{request_id}",
            response,
            qos,
        )
        print(
            f"[{device_name}] RPC response "
            f"{json.dumps(response, ensure_ascii=False)}")

    return on_message


def main() -> int:
    args = parse_args()
    if args.count < 0:
        print("error: --count must be >= 0", file=sys.stderr)
        return 1
    rng = random.Random(args.seed)
    try:
        devices = load_devices(args.devices_csv)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    sensors = [
        device for device in devices
        if device["scene_role"] != "actuator"
    ]
    actuators = [
        device for device in devices
        if device["scene_role"] == "actuator"
    ]

    if args.dry_run:
        iterations = args.count if args.count > 0 else 1
        for index in range(iterations):
            for device in sensors:
                print(
                    f"[dry-run] {device['device_name']} "
                    f"{json.dumps(sensor_payload(device, index, rng), ensure_ascii=False)}")
            for device in actuators:
                key = "state" if device["product_id"] == "SCENE_LIGHT" else "mode"
                value = "OFF"
                print(
                    f"[dry-run] {device['device_name']} telemetry "
                    f"{json.dumps({key: value, 'online': True}, ensure_ascii=False)}")
        return 0

    clients: Dict[str, mqtt.Client] = {}
    states: Dict[str, Dict[str, Any]] = {}
    try:
        for device in devices:
            name = device["device_name"]
            client = create_mqtt_client(f"scene-{name}")
            client.username_pw_set(device["access_token"], "")
            if device["scene_role"] == "actuator":
                states[name] = {
                    "state": "OFF" if device["product_id"] == "SCENE_LIGHT" else "OFF",
                    "mode": "OFF",
                }
                client.on_message = build_rpc_handler(
                    device, states[name], args.qos)
            clients[name] = client

        for name, client in clients.items():
            client.connect(args.mqtt_host, args.mqtt_port, keepalive=60)
            client.loop_start()
            wait_connected(client)
            print(f"connected {name}")

        for device in actuators:
            name = device["device_name"]
            clients[name].subscribe("v1/devices/me/rpc/request/+", qos=args.qos)
            key = "state" if device["product_id"] == "SCENE_LIGHT" else "mode"
            publish(
                clients[name],
                "v1/devices/me/telemetry",
                {key: "OFF", "online": True},
                args.qos,
            )
            print(f"subscribed {name} to RPC requests")

        index = 0
        while args.count <= 0 or index < args.count:
            for device in sensors:
                name = device["device_name"]
                payload = sensor_payload(device, index, rng)
                publish(
                    clients[name],
                    "v1/devices/me/telemetry",
                    payload,
                    args.qos,
                )
                print(
                    f"[{name}] telemetry "
                    f"{json.dumps(payload, ensure_ascii=False)}")
            for device in actuators:
                name = device["device_name"]
                key = "state" if device["product_id"] == "SCENE_LIGHT" else "mode"
                payload = {key: states[name][key], "online": True}
                publish(
                    clients[name],
                    "v1/devices/me/telemetry",
                    payload,
                    args.qos,
                )
                print(
                    f"[{name}] telemetry "
                    f"{json.dumps(payload, ensure_ascii=False)}")
            index += 1
            if args.count <= 0 or index < args.count:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        for name, client in clients.items():
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass
        print(f"disconnected {len(clients)} devices")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
