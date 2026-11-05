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
from typing import Any, Dict, List, Optional

from simulate_gateway import (
    build_batch_telemetry_payload,
    build_connect_payload,
    build_disconnect_payload,
    build_values,
    chunked,
    create_mqtt_client,
    load_gateways,
    publish,
    resolve_tsl,
    wait_connected,
)
from simulate_telemetry import ApiError, TelemetryGenerator, ThingsBoardClient

DEFAULT_TSL_DIR = Path(__file__).resolve().parent.parent / "migrate" / "integrated"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate multiple thing-model products through one ThingsBoard gateway.")
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
        help="gateway credentials CSV",
    )
    parser.add_argument(
        "--gateway-name",
        default=None,
        help="gateway device name from the CSV; defaults to the first row",
    )
    parser.add_argument(
        "--sub-devices-csv",
        default=os.getenv("SUB_DEVICES_CSV", "sub-devices.csv"),
        help="sub-device credentials CSV grouped by product_id",
    )
    parser.add_argument(
        "--tsl-dir",
        default=str(DEFAULT_TSL_DIR),
        help="directory with local product TSL files; falls back to thing-model",
    )
    parser.add_argument(
        "--gateway-mock",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="write gateway status attributes and publish gateway telemetry",
    )
    parser.add_argument(
        "--gateway-version",
        default="3.6.0",
        help="mock gateway version attribute",
    )
    parser.add_argument(
        "--gateway-type",
        default="tb-gateway",
        help="mock gateway type attribute",
    )
    parser.add_argument(
        "--connectors",
        default="modbus,mqtt,socket,rest",
        help="comma-separated active connector names",
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
        "--mode",
        choices=["auto", "telemetry", "event", "mixed"],
        default="auto",
        help="auto uses mixed for products with events, telemetry otherwise",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="seconds between iterations",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="sub-devices per gateway telemetry message",
    )
    parser.add_argument(
        "--events-per-packet",
        type=int,
        default=4,
        help="number of events per event packet",
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
        "--count",
        type=int,
        default=0,
        help="iterations; 0 means run until Ctrl+C",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="only print progress and summary",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print payloads without connecting to MQTT",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds",
    )
    return parser.parse_args()


def load_sub_devices_by_product(path: str) -> Dict[str, List[str]]:
    csv_path = Path(path)
    if not csv_path.is_file():
        raise ApiError(f"sub-devices CSV not found: {csv_path}")
    groups: Dict[str, List[str]] = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            product_id = (row.get("product_id") or "").strip()
            device_name = (row.get("device_name") or "").strip()
            if not product_id or not device_name:
                continue
            groups.setdefault(product_id, [])
            if device_name not in groups[product_id]:
                groups[product_id].append(device_name)
    if not groups:
        raise ApiError(f"no sub-devices found in {csv_path}")
    return groups


def ensure_localhost_no_proxy() -> None:
    hosts = ["localhost", "127.0.0.1", "::1"]
    current = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
    parts = [part.strip() for part in current.split(",") if part.strip()]
    for host in hosts:
        if host not in parts:
            parts.append(host)
    value = ",".join(parts)
    os.environ["NO_PROXY"] = value
    os.environ["no_proxy"] = value


def find_local_tsl(tsl_dir: Path, product_id: str) -> Optional[Dict[str, Any]]:
    if not tsl_dir.is_dir():
        return None
    for path in sorted(tsl_dir.glob("*.json")):
        try:
            data = json.loads(path.read_bytes().decode("utf-8-sig"))
        except Exception:
            continue
        profile = data.get("profile") or {}
        current = str(profile.get("ProductId") or profile.get("productId") or "")
        if current == product_id:
            return data
    return None


def resolve_product_tsl(args: argparse.Namespace,
                        product_id: str) -> Dict[str, Any]:
    local = find_local_tsl(Path(args.tsl_dir), product_id)
    if local is not None:
        return local
    if args.password is None:
        args.password = getpass.getpass(
            f"ThingsBoard password for {args.username}: ")
    return resolve_tsl(args, product_id)


def select_kind(mode: str, has_events: bool, index: int) -> str:
    if mode == "auto":
        mode = "mixed" if has_events else "telemetry"
    if mode == "mixed":
        return "telemetry" if index % 2 == 0 else "event"
    return mode


def build_contexts(
        groups: Dict[str, List[str]],
        args: argparse.Namespace) -> List[Dict[str, Any]]:
    contexts: List[Dict[str, Any]] = []
    for product_index, (product_id, devices) in enumerate(groups.items()):
        tsl = resolve_product_tsl(args, product_id)
        properties = tsl.get("properties") or []
        events = tsl.get("events") or []
        if not properties:
            raise ApiError(f"no properties found for product {product_id}")
        generators = []
        for device_index in range(len(devices)):
            seed = (args.seed + product_index * 10000 + device_index
                    if args.seed is not None else None)
            generators.append(
                TelemetryGenerator(properties, events, random.Random(seed)))
        contexts.append({
            "product_id": product_id,
            "devices": devices,
            "generators": generators,
            "has_events": bool(events),
        })
    return contexts


def build_pairs(context: Dict[str, Any], kind: str,
                 events_per_packet: int) -> List[Any]:
    return [
        (device_name, build_values(generator, kind, events_per_packet))
        for device_name, generator in zip(
            context["devices"], context["generators"])
    ]


def set_entity_attributes(
        client: ThingsBoardClient,
        token: str,
        device_id: str,
        scope: str,
        attributes: Dict[str, Any]) -> None:
    response = client.session.post(
        f"{client.tb_url}/api/plugins/telemetry/DEVICE/{device_id}/attributes/{scope}",
        headers=client._auth_headers(token),
        json=attributes,
        timeout=client.timeout,
    )
    client._check(response)


def start_gateway_mock(
        client: ThingsBoardClient,
        token: str,
        gateway_id: str,
        gateway_name: str,
        args: argparse.Namespace) -> None:
    connectors = [
        item.strip() for item in args.connectors.split(",") if item.strip()
    ]
    connectors_json = json.dumps(connectors, ensure_ascii=False)
    general_configuration = json.dumps({
        "host": "127.0.0.1",
        "port": args.mqtt_port,
        "remoteShell": False,
        "remoteConfiguration": True,
        "checkConnectorsConfigurationInSeconds": 60,
        "statistics": {
            "enable": True,
            "enableCustom": False,
        },
    }, ensure_ascii=False)
    set_entity_attributes(client, token, gateway_id, "SERVER_SCOPE", {
        "Status": "true",
        "Name": gateway_name,
        "Type": args.gateway_type,
        "Version": args.gateway_version,
        "active_connectors": connectors_json,
        "inactive_connectors": "[]",
        "RemoteLoggingLevel": "INFO",
        "general_configuration": general_configuration,
    })
    set_entity_attributes(client, token, gateway_id, "SHARED_SCOPE", {
        "active_connectors": connectors_json,
        "general_configuration": general_configuration,
    })


def stop_gateway_mock(
        client: ThingsBoardClient,
        token: str,
        gateway_id: str) -> None:
    set_entity_attributes(client, token, gateway_id, "SERVER_SCOPE", {
        "Status": "false",
    })


def build_gateway_telemetry(
        iteration: int,
        total_devices: int,
        rng: random.Random) -> Dict[str, Any]:
    service_stats = {
        "storageMsgCount": iteration * total_devices,
        "storageMsgPulled": iteration * total_devices,
        "platformAttrProduced": iteration * total_devices * 2,
        "platformTsProduced": iteration * total_devices * 4,
        "platformMsgPushed": iteration * total_devices * 3,
    }
    machine_stats = {
        "msgsSentToPlatform": iteration * total_devices,
        "gwProcessCpuUsage": rng.randint(5, 40),
        "gwMemory": rng.randint(20, 60),
        "diskUsage": rng.randint(30, 70),
    }
    return {
        "serviceStats": json.dumps(service_stats, ensure_ascii=False),
        "machineStats": json.dumps(machine_stats, ensure_ascii=False),
        "ALL_ERRORS_COUNT": 0,
    }


def main() -> int:
    args = parse_args()
    args.tsl = None
    ensure_localhost_no_proxy()

    gateway_names = [args.gateway_name] if args.gateway_name else []
    admin_client: Optional[ThingsBoardClient] = None
    admin_token: Optional[str] = None
    gateway_id: Optional[str] = None
    try:
        gateways = load_gateways(args.gateway_csv, gateway_names)
        gateway_name, gateway_token = gateways[0]
        groups = load_sub_devices_by_product(args.sub_devices_csv)
        contexts = build_contexts(groups, args)
        if args.gateway_mock:
            if args.password is None:
                args.password = getpass.getpass(
                    f"ThingsBoard password for {args.username}: ")
            admin_client = ThingsBoardClient(
                args.tb_url, args.thingmodel_url, args.timeout)
            admin_token = admin_client.login(args.username, args.password)
            gateway_device = admin_client.find_device_by_name(
                admin_token, gateway_name)
            if not gateway_device or not gateway_device.get("id"):
                raise ApiError(f"gateway not found in ThingsBoard: {gateway_name}")
            gateway_id = gateway_device["id"]["id"]
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    total_devices = sum(len(context["devices"]) for context in contexts)
    print(
        f"gateway={gateway_name} products={len(contexts)} "
        f"subDevices={total_devices} mode={args.mode} count={args.count}")
    for context in contexts:
        print(
            f"  {context['product_id']}: {len(context['devices'])} devices, "
            f"events={'yes' if context['has_events'] else 'no'}")

    gateway_rng = random.Random(args.seed)

    if args.dry_run:
        iterations = args.count if args.count > 0 else 1
        for index in range(iterations):
            if args.gateway_mock:
                gateway_payload = build_gateway_telemetry(
                    index + 1, total_devices, gateway_rng)
                if args.quiet:
                    print("[dry-run] gateway telemetry")
                else:
                    print(
                        "[dry-run] gateway "
                        f"{json.dumps(gateway_payload, ensure_ascii=False)}")
            for context in contexts:
                kind = select_kind(
                    args.mode, context["has_events"], index)
                pairs = build_pairs(
                    context, kind, args.events_per_packet)
                for batch in chunked(pairs, args.batch_size):
                    payload = build_batch_telemetry_payload(batch)
                    if args.quiet:
                        print(
                            f"[dry-run] product={context['product_id']} "
                            f"kind={kind} devices={len(batch)}")
                    else:
                        print(
                            f"[dry-run] product={context['product_id']} "
                            f"{json.dumps(payload, ensure_ascii=False)}")
        return 0

    client = create_mqtt_client(gateway_name)
    client.username_pw_set(gateway_token, "")
    errors = 0
    batches = 0
    index = 0
    connected = False

    try:
        client.connect(args.mqtt_host, args.mqtt_port, keepalive=60)
        client.loop_start()
        wait_connected(client)
        connected = True

        if args.gateway_mock and admin_client and admin_token and gateway_id:
            start_gateway_mock(
                admin_client, admin_token, gateway_id, gateway_name, args)
            print(
                f"gateway mock enabled version={args.gateway_version} "
                f"type={args.gateway_type}")
            publish(
                client,
                "v1/devices/me/attributes",
                {"Version": args.gateway_version},
                args.qos,
            )

        for context in contexts:
            for device_name in context["devices"]:
                publish(
                    client,
                    "v1/gateway/connect",
                    build_connect_payload(device_name, context["product_id"]),
                    args.qos,
                )
        print(f"connected gateway={gateway_name} devices={total_devices}")

        while args.count <= 0 or index < args.count:
            for context in contexts:
                kind = select_kind(
                    args.mode, context["has_events"], index)
                pairs = build_pairs(
                    context, kind, args.events_per_packet)
                for batch in chunked(pairs, args.batch_size):
                    payload = build_batch_telemetry_payload(batch)
                    publish(
                        client,
                        "v1/gateway/telemetry",
                        payload,
                        args.qos,
                    )
                    batches += 1
                    if args.quiet:
                        print(
                            f"[{kind}] product={context['product_id']} "
                            f"devices={len(batch)}")
                    else:
                        print(
                            f"[{kind}] product={context['product_id']} "
                            f"{json.dumps(payload, ensure_ascii=False)}")
            if args.gateway_mock:
                gateway_payload = build_gateway_telemetry(
                    index + 1, total_devices, gateway_rng)
                publish(
                    client,
                    "v1/devices/me/telemetry",
                    gateway_payload,
                    args.qos,
                )
                if args.quiet:
                    print("[gateway] telemetry")
                else:
                    print(
                        "[gateway] "
                        f"{json.dumps(gateway_payload, ensure_ascii=False)}")
            index += 1
            if args.count <= 0 or index < args.count:
                time.sleep(args.interval)

        print(
            f"summary gateway={gateway_name} products={len(contexts)} "
            f"subDevices={total_devices} packets={index} batches={batches} "
            f"errors={errors}")
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        errors += 1
    finally:
        disconnect_errors = 0
        if connected:
            for context in contexts:
                for device_name in context["devices"]:
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
                            f"failed to disconnect device={device_name}: {exc}",
                            file=sys.stderr,
                        )
            print(f"disconnected gateway={gateway_name} devices={total_devices}")
            client.loop_stop()
            client.disconnect()
        if args.gateway_mock and admin_client and admin_token and gateway_id:
            try:
                stop_gateway_mock(admin_client, admin_token, gateway_id)
            except Exception as exc:
                errors += 1
                print(f"failed to set gateway offline: {exc}", file=sys.stderr)
        if disconnect_errors:
            errors += disconnect_errors

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
