#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import paho.mqtt.client as mqtt

from simulate_telemetry import (
    ApiError,
    TelemetryGenerator,
    ThingsBoardClient,
    load_tsl,
    mode_sequence,
    parse_tsl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate ThingsBoard gateway and sub-device telemetry over MQTT.")
    parser.add_argument(
        "--tb-url",
        default=os.getenv("TB_URL", "http://localhost:18080"),
        help="ThingsBoard base URL for TSL lookup",
    )
    parser.add_argument(
        "--thingmodel-url",
        default=os.getenv("THINGMODEL_URL", "http://localhost:8090"),
        help="thing-model base URL for TSL lookup",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("TB_USERNAME", "tenant@thingsboard.org"),
        help="ThingsBoard tenant admin username",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("TB_PASSWORD"),
        help="ThingsBoard password; defaults to TB_PASSWORD or prompt",
    )
    parser.add_argument(
        "--gateway-csv",
        default=os.getenv("GATEWAY_CSV", "gateway-credentials.csv"),
        help="CSV produced when registering gateway devices",
    )
    parser.add_argument(
        "--gateway-name",
        default=None,
        help="gateway device name from the gateway CSV; defaults to the first row",
    )
    parser.add_argument(
        "--gateway-names",
        default=None,
        help="comma-separated gateway names; sub-devices are split evenly",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="sub-devices per gateway telemetry message",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="only print batch progress and summary",
    )
    parser.add_argument(
        "--sub-devices-csv",
        default=None,
        help="CSV produced by register_devices.py for sub-devices",
    )
    parser.add_argument(
        "--sub-device",
        action="append",
        default=[],
        help="sub-device name; repeat for multiple devices",
    )
    parser.add_argument(
        "--product-id",
        default=os.getenv("PRODUCT_ID"),
        help="thing-model product id",
    )
    parser.add_argument(
        "--tsl",
        default=None,
        help="local TSL JSON file; when omitted, fetch the product TSL",
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
        "--qos",
        type=int,
        default=1,
        choices=[0, 1, 2],
        help="MQTT QoS",
    )
    parser.add_argument(
        "--mode",
        choices=["telemetry", "event", "invalid", "mixed"],
        default="mixed",
        help="message mode",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="packet count; 0 means unlimited",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="seconds between packets",
    )
    parser.add_argument(
        "--events-per-packet",
        type=int,
        default=4,
        help="number of same-type events per event packet",
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
        help="print gateway payloads without connecting to MQTT",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds",
    )
    return parser.parse_args()


def load_gateways(
        path: str,
        gateway_names: List[str]) -> List[Tuple[str, str]]:
    csv_path = Path(path)
    if not csv_path.is_file():
        raise ApiError(f"gateway CSV not found: {csv_path}")
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ApiError(f"no gateways found in {csv_path}")

    by_name = {}
    for row in rows:
        name = (row.get("device_name") or "").strip()
        token = (row.get("access_token") or "").strip()
        if not name or not token:
            raise ApiError(
                f"gateway row is missing device_name or access_token: {csv_path}")
        by_name[name] = token

    selected = list(dict.fromkeys(gateway_names)) if gateway_names else [rows[0]["device_name"].strip()]
    result = []
    for name in selected:
        if name not in by_name:
            raise ApiError(f"gateway not found in {csv_path}: {name}")
        result.append((name, by_name[name]))
    return result


def split_devices(devices: List[str], parts: int) -> List[List[str]]:
    groups: List[List[str]] = [[] for _ in range(parts)]
    for index, device_name in enumerate(devices):
        groups[index % parts].append(device_name)
    return groups


def chunked(items: List[Any], size: int) -> Iterable[List[Any]]:
    step = max(1, size)
    for index in range(0, len(items), step):
        yield items[index:index + step]


def load_sub_devices(
        path: Optional[str],
        cli_names: List[str],
        product_id: str) -> List[str]:
    if cli_names:
        return list(dict.fromkeys(cli_names))
    if not path:
        raise ApiError("use --sub-devices-csv or --sub-device")
    csv_path = Path(path)
    if not csv_path.is_file():
        raise ApiError(f"sub-devices CSV not found: {csv_path}")
    names: List[str] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            name = (row.get("device_name") or "").strip()
            if not name:
                continue
            row_product = (row.get("product_id") or "").strip()
            if row_product and row_product != product_id:
                continue
            names.append(name)
    names = list(dict.fromkeys(names))
    if not names:
        raise ApiError(f"no sub-devices found in {csv_path} for product {product_id}")
    return names


def resolve_tsl(args: argparse.Namespace, product_id: str) -> Dict[str, Any]:
    if args.tsl:
        tsl = load_tsl(args.tsl)
        profile = tsl.get("profile") or {}
        tsl_product_id = profile.get("ProductId") or profile.get("productId")
        if tsl_product_id and tsl_product_id != product_id:
            raise ApiError(
                f"TSL ProductId {tsl_product_id} does not match "
                f"--product-id {product_id}")
        return tsl

    password = args.password
    if not password:
        password = getpass.getpass(
            f"ThingsBoard password for {args.username}: ")

    client = ThingsBoardClient(args.tb_url, args.thingmodel_url, args.timeout)
    token = client.login(args.username, password)
    product = client.get_product(token, product_id)
    product_info = product.get("product") or {}
    try:
        thing_model = client.get_thing_model(token, product_id)
        return parse_tsl(thing_model.get("tsl"))
    except Exception as exc:
        print(
            f"warning: failed to load product TSL, falling back to catalog: {exc}",
            file=sys.stderr,
        )
        catalog = product.get("catalog") or {}
        return {
            "properties": catalog.get("properties") or [],
            "events": catalog.get("events") or [],
            "version": product_info.get("tslVersion") or "1.0",
        }


def build_connect_payload(device_name: str, product_id: str) -> Dict[str, Any]:
    return {"device": device_name, "type": product_id}


def build_disconnect_payload(device_name: str) -> Dict[str, Any]:
    return {"device": device_name}


def build_telemetry_payload(
        device_name: str,
        values: Dict[str, Any],
        ts: Optional[int] = None) -> Dict[str, Any]:
    packet_ts = int(time.time() * 1000) if ts is None else ts
    return {device_name: [{"ts": packet_ts, "values": values}]}


def build_batch_telemetry_payload(
        items: Iterable[Tuple[str, Dict[str, Any]]],
        ts: Optional[int] = None) -> Dict[str, Any]:
    packet_ts = int(time.time() * 1000) if ts is None else ts
    return {
        device_name: [{"ts": packet_ts, "values": values}]
        for device_name, values in items
    }


def build_values(
        generator: TelemetryGenerator,
        kind: str,
        events_per_packet: int) -> Dict[str, Any]:
    if kind == "telemetry":
        return generator.telemetry()
    if kind == "event":
        return generator.payload("event", True, events_per_packet)
    if kind == "invalid":
        return generator.invalid()
    raise ApiError(f"unsupported mode: {kind}")


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
    raise ApiError("MQTT connection timeout")


def publish(client: mqtt.Client, topic: str, payload: Dict[str, Any], qos: int) -> None:
    info = client.publish(
        topic,
        json.dumps(payload, ensure_ascii=False),
        qos=qos,
    )
    info.wait_for_publish(timeout=30)
    if not info.is_published():
        raise ApiError(f"MQTT publish timeout: {topic}")


def main() -> int:
    args = parse_args()
    product_id = args.product_id or os.getenv("PRODUCT_ID")
    if not product_id:
        print("error: --product-id is required (or set PRODUCT_ID)", file=sys.stderr)
        return 1

    gateway_names: List[str] = []
    if args.gateway_names:
        gateway_names = [
            part.strip() for part in args.gateway_names.split(",") if part.strip()
        ]
    elif args.gateway_name:
        gateway_names = [args.gateway_name]

    try:
        gateways = load_gateways(args.gateway_csv, gateway_names)
        sub_devices = load_sub_devices(
            args.sub_devices_csv, args.sub_device, product_id)
        tsl = resolve_tsl(args, product_id)
        properties = tsl.get("properties") or []
        events = tsl.get("events") or []
        if not properties:
            raise ApiError(f"no properties found for product {product_id}")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    sequence = mode_sequence(args.mode)
    device_groups = split_devices(sub_devices, len(gateways))
    workers = []
    for gateway_index, ((gateway_name, gateway_token), devices) in enumerate(
            zip(gateways, device_groups)):
        generators = [
            TelemetryGenerator(
                properties,
                events,
                random.Random(
                    args.seed + gateway_index * 10000 + index
                    if args.seed is not None else None),
            )
            for index in range(len(devices))
        ]
        workers.append({
            "name": gateway_name,
            "token": gateway_token,
            "devices": devices,
            "generators": generators,
            "client": None,
        })

    print(
        f"gateways={len(workers)} subDevices={len(sub_devices)} "
        f"product={product_id} mode={args.mode} count={args.count} "
        f"batchSize={args.batch_size}")
    for worker in workers:
        print(f"  {worker['name']}: {len(worker['devices'])} devices")

    if args.dry_run:
        total = args.count if args.count > 0 else 1
        for index in range(total):
            kind = sequence[index % len(sequence)]
            for worker in workers:
                pairs = [
                    (device_name, build_values(
                        generator, kind, args.events_per_packet))
                    for device_name, generator in zip(
                        worker["devices"], worker["generators"])
                ]
                for batch in chunked(pairs, args.batch_size):
                    payload = build_batch_telemetry_payload(batch)
                    if args.quiet:
                        print(
                            f"[dry-run] gateway={worker['name']} "
                            f"kind={kind} devices={len(batch)}")
                    else:
                        print(
                            f"[dry-run] gateway={worker['name']} "
                            f"{json.dumps(payload, ensure_ascii=False)}")
        return 0

    errors = 0
    batches = 0
    index = 0
    try:
        for worker in workers:
            client = create_mqtt_client(worker["name"])
            client.username_pw_set(worker["token"], "")
            client.connect(args.mqtt_host, args.mqtt_port, keepalive=60)
            client.loop_start()
            wait_connected(client)
            worker["client"] = client

        for worker in workers:
            for device_name in worker["devices"]:
                publish(
                    worker["client"],
                    "v1/gateway/connect",
                    build_connect_payload(device_name, product_id),
                    args.qos,
                )
            print(
                f"connected gateway={worker['name']} "
                f"devices={len(worker['devices'])}")

        while args.count <= 0 or index < args.count:
            kind = sequence[index % len(sequence)]
            for worker in workers:
                pairs = [
                    (device_name, build_values(
                        generator, kind, args.events_per_packet))
                    for device_name, generator in zip(
                        worker["devices"], worker["generators"])
                ]
                for batch in chunked(pairs, args.batch_size):
                    payload = build_batch_telemetry_payload(batch)
                    publish(
                        worker["client"],
                        "v1/gateway/telemetry",
                        payload,
                        args.qos,
                    )
                    batches += 1
                    if args.quiet:
                        print(
                            f"[{kind}] gateway={worker['name']} "
                            f"devices={len(batch)}")
                    else:
                        print(
                            f"[{kind}] gateway={worker['name']} "
                            f"{json.dumps(payload, ensure_ascii=False)}")
            index += 1
            if args.count <= 0 or index < args.count:
                time.sleep(args.interval)

        print(
            f"summary gateways={len(workers)} subDevices={len(sub_devices)} "
            f"packets={index} batches={batches} errors={errors}")
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        errors += 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        errors += 1
    finally:
        disconnect_errors = 0
        for worker in workers:
            client = worker["client"]
            if not client:
                continue
            for device_name in worker["devices"]:
                try:
                    publish(
                        client,
                        "v1/gateway/disconnect",
                        build_disconnect_payload(device_name),
                        args.qos,
                    )
                except Exception as exc:
                    disconnect_errors += 1
                    print(
                        f"failed to disconnect gateway={worker['name']} "
                        f"device={device_name}: {exc}",
                        file=sys.stderr,
                    )
            print(
                f"disconnected gateway={worker['name']} "
                f"devices={len(worker['devices'])}")
            client.loop_stop()
            client.disconnect()
        if disconnect_errors:
            print(
                f"disconnect errors={disconnect_errors}",
                file=sys.stderr,
            )
            errors += disconnect_errors

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
