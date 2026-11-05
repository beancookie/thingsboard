#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

PROTOCOLS = ("modbus", "opcua", "s7", "can", "odbc")

DEFAULT_PORTS = {
    "modbus": 5021,
    "opcua": 4840,
    "s7": 1102,
    "can": 15000,
    "odbc": 5433,
}


class MappingError(RuntimeError):
    pass


def _type(prop: Dict[str, Any]) -> str:
    define = prop.get("define")
    if not isinstance(define, dict):
        define = prop
    return str(define.get("type") or prop.get("dataType") or "string").lower()


def _props(tsl: Dict[str, Any]) -> List[Dict[str, Any]]:
    properties = tsl.get("properties")
    if not isinstance(properties, list):
        raise MappingError("TSL properties must be an array")
    return [item for item in properties if isinstance(item, dict) and item.get("id")]


def load_tsls(tsl_dir: Path) -> Dict[str, Dict[str, Any]]:
    if not tsl_dir.is_dir():
        raise MappingError(f"TSL directory not found: {tsl_dir}")
    result: Dict[str, Dict[str, Any]] = {}
    for path in sorted(tsl_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            raise MappingError(f"invalid TSL {path.name}: {exc}") from exc
        profile = data.get("profile") or {}
        product_id = str(profile.get("ProductId") or profile.get("productId") or "").strip()
        if not product_id:
            continue
        if product_id in result:
            raise MappingError(f"duplicate ProductId {product_id} in {tsl_dir}")
        result[product_id] = data
    if not result:
        raise MappingError(f"no TSL files found in {tsl_dir}")
    return result


def load_sub_devices(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        raise MappingError(f"sub-devices CSV not found: {path}")
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            product_id = (row.get("product_id") or "").strip()
            device_name = (row.get("device_name") or "").strip()
            if not product_id or not device_name:
                continue
            rows.append({
                "product_id": product_id,
                "device_name": device_name,
                "profile_name": (row.get("profile_name") or "").strip(),
            })
    if not rows:
        raise MappingError(f"no sub-devices found in {path}")
    return rows


def _point_types(tsl: Dict[str, Any]) -> Dict[str, str]:
    return {str(prop["id"]): _type(prop) for prop in _props(tsl)}


def build_mapping(
        tsl_dir: Path,
        sub_devices_csv: Path,
        protocol: str,
        host: str = "127.0.0.1",
        gateway_host: str = "host.docker.internal",
        ports: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    if protocol not in PROTOCOLS:
        raise MappingError(f"unsupported protocol: {protocol}")
    tsls = load_tsls(tsl_dir)
    rows = load_sub_devices(sub_devices_csv)
    port_map = dict(DEFAULT_PORTS)
    if ports:
        port_map.update(ports)

    devices: Dict[str, Dict[str, Any]] = {}
    next_unit_id = 1
    next_db_number = 1
    next_frame_id = 0x100

    for row in rows:
        product_id = row["product_id"]
        device_name = row["device_name"]
        tsl = tsls.get(product_id)
        if tsl is None:
            raise MappingError(
                f"device {device_name} references unknown product {product_id}")
        if device_name in devices:
            continue
        types = _point_types(tsl)
        device: Dict[str, Any] = {
            "product_id": product_id,
            "device_name": device_name,
            "profile_name": row["profile_name"] or "default",
            "types": types,
        }
        if protocol == "modbus":
            device["unit_id"] = next_unit_id
            next_unit_id += 1
            if next_unit_id > 247:
                raise MappingError("too many Modbus devices; unit id exceeds 247")
            device["points"] = _modbus_points(types)
        elif protocol == "opcua":
            device["node_prefix"] = f"ns=2;s={device_name}"
            device["device_node"] = f"Root\\.Objects\\.{device_name}"
            device["nodes"] = {
                key: {"node_id": f"{device['node_prefix']}.{key}", "type": data_type}
                for key, data_type in types.items()
                if data_type not in ("struct",)
            }
        elif protocol == "s7":
            device["db_number"] = next_db_number
            next_db_number += 1
            device["points"] = _s7_points(types)
        elif protocol == "can":
            points = {}
            for key, data_type in types.items():
                if data_type not in ("bool", "boolean", "float", "double", "int", "timestamp"):
                    continue
                length = 4 if data_type in ("float", "int", "timestamp") else 1
                points[key] = {
                    "frame_id": next_frame_id,
                    "start": 0,
                    "length": length,
                    "type": data_type,
                }
                next_frame_id += 1
            device["points"] = points
        elif protocol == "odbc":
            device["points"] = {
                key: {"type": data_type} for key, data_type in types.items()
            }
        devices[device_name] = device

    if not devices:
        raise MappingError("no devices generated")

    mapping: Dict[str, Any] = {
        "protocol": protocol,
        "host": host,
        "gateway_host": gateway_host,
        "port": port_map[protocol],
        "devices": devices,
    }
    if protocol == "opcua":
        mapping["endpoint"] = f"opc.tcp://{host}:{port_map['opcua']}"
        mapping["gateway_endpoint"] = f"opc.tcp://{gateway_host}:{port_map['opcua']}"
    if protocol == "can":
        mapping["interface"] = "udp_multicast"
        mapping["channel"] = "239.255.0.1"
        mapping["port"] = port_map["can"]
        mapping["fd"] = False
    if protocol == "odbc":
        mapping["database"] = "gateway_sim"
        mapping["user"] = "gateway"
        mapping["password"] = "gateway"
        mapping["table"] = "gateway_telemetry"
    return mapping


def _modbus_points(types: Dict[str, str]) -> Dict[str, Any]:
    points: Dict[str, Any] = {}
    hr_address = 0
    co_address = 0
    for key, data_type in types.items():
        if data_type in ("bool", "boolean"):
            points[key] = {
                "area": "co",
                "address": co_address,
                "count": 1,
                "type": "bool",
            }
            co_address += 1
        elif data_type in ("float", "double"):
            points[key] = {
                "area": "hr",
                "address": hr_address,
                "count": 2,
                "type": "float",
            }
            hr_address += 2
        elif data_type in ("int", "timestamp"):
            points[key] = {
                "area": "hr",
                "address": hr_address,
                "count": 2,
                "type": "int",
            }
            hr_address += 2
        else:
            points[key] = {"area": "skip", "type": "string"}
    return points


def _s7_points(types: Dict[str, str]) -> Dict[str, Any]:
    points: Dict[str, Any] = {}
    offset = 0
    for key, data_type in types.items():
        if data_type in ("bool", "boolean"):
            points[key] = {
                "offset": offset,
                "bit": 0,
                "size": 1,
                "type": "bool",
            }
            offset += 1
        elif data_type in ("float", "double"):
            points[key] = {
                "offset": offset,
                "size": 4,
                "type": "real",
            }
            offset += 4
        elif data_type in ("int", "timestamp"):
            points[key] = {
                "offset": offset,
                "size": 4,
                "type": "dint",
            }
            offset += 4
        else:
            points[key] = {"offset": offset, "size": 0, "type": "skip"}
    return points


def invert_devices(mapping: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    devices = mapping.get("devices")
    if not isinstance(devices, dict):
        raise MappingError("mapping has no devices")
    return devices


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
