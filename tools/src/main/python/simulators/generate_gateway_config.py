#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from protocol_mapping import (
    DEFAULT_PORTS,
    PROTOCOLS,
    MappingError,
    build_mapping,
    write_json,
)

DEFAULT_TSL_DIR = Path(__file__).resolve().parents[5] / "thing-model" / "migrate" / "integrated"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate one ThingsBoard Gateway connector config for a protocol.")
    parser.add_argument(
        "--protocol",
        required=True,
        choices=list(PROTOCOLS),
        help="protocol to generate; each run uses exactly one protocol",
    )
    parser.add_argument(
        "--tsl-dir",
        default=str(DEFAULT_TSL_DIR),
        help="directory with thing-model TSL JSON files",
    )
    parser.add_argument(
        "--sub-devices-csv",
        default="sub-devices.csv",
        help="CSV produced by setup_gateway.py",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="directory for connector-mapping and gateway config files",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="host used by the Windows protocol simulator",
    )
    parser.add_argument(
        "--gateway-host",
        default="host.docker.internal",
        help="host used by the Dockerized tb-gateway",
    )
    parser.add_argument(
        "--odbc-host",
        default="odbc-db",
        help="PostgreSQL host used by the gateway ODBC connector",
    )
    parser.add_argument("--modbus-port", type=int, default=DEFAULT_PORTS["modbus"])
    parser.add_argument("--opcua-port", type=int, default=DEFAULT_PORTS["opcua"])
    parser.add_argument("--s7-port", type=int, default=DEFAULT_PORTS["s7"])
    parser.add_argument("--can-port", type=int, default=DEFAULT_PORTS["can"])
    return parser.parse_args()


def build_tb_gateway(protocol: str, gateway_host: str) -> Dict[str, Any]:
    return {
        "thingsboard": {
            "host": gateway_host,
            "port": 1883,
            "remoteShell": False,
            "remoteConfiguration": True,
            "statistics": {
                "enable": True,
                "statsSendPeriodInSeconds": 60,
            },
            "security": {
                "type": "accessToken",
                "accessToken": "ACCESS_TOKEN_FROM_TB_GW_ACCESS_TOKEN",
            },
            "qos": 1,
        },
        "storage": {
            "type": "memory",
            "read_records_count": 100,
            "max_records_count": 10000,
        },
        "connectors": [
            {
                "type": protocol,
                "name": f"{protocol} Connector",
                "configuration": f"{protocol}.json",
            }
        ],
    }


def build_modbus_config(mapping: Dict[str, Any]) -> Dict[str, Any]:
    slaves = []
    for device in mapping["devices"].values():
        timeseries = []
        for key, point in device["points"].items():
            if point.get("area") == "skip":
                continue
            if point["type"] == "bool":
                timeseries.append({
                    "tag": key,
                    "type": "bits",
                    "address": point["address"],
                    "objectsCount": point["count"],
                    "functionCode": 1,
                    "bitTargetType": "bool",
                })
            else:
                timeseries.append({
                    "tag": key,
                    "type": "32float" if point["type"] == "float" else "32int",
                    "address": point["address"],
                    "objectsCount": point["count"],
                    "functionCode": 3,
                })
        slaves.append({
            "host": mapping["gateway_host"],
            "port": mapping["port"],
            "type": "tcp",
            "method": "socket",
            "unitId": device["unit_id"],
            "deviceName": device["device_name"],
            "deviceType": device["profile_name"],
            "deviceProfileName": device["profile_name"],
            "timeout": 35,
            "byteOrder": "BIG",
            "wordOrder": "BIG",
            "retries": True,
            "retryOnEmpty": True,
            "retryOnInvalid": True,
            "pollPeriod": 1000,
            "connectAttemptTimeMs": 5000,
            "connectAttemptCount": 5,
            "waitAfterFailedAttemptsMs": 30000,
            "attributes": [],
            "timeseries": timeseries,
            "attributeUpdates": [],
            "rpc": [],
        })
    return {"master": {"slaves": slaves}}


def build_opcua_config(mapping: Dict[str, Any]) -> Dict[str, Any]:
    mappings = []
    for device in mapping["devices"].values():
        timeseries = [
            {
                "key": key,
                "type": "path",
                "value": "${" + key + "}",
            }
            for key in device["nodes"]
        ]
        mappings.append({
            "deviceNodeSource": "path",
            "deviceNodePattern": device["device_node"],
            "deviceInfo": {
                "deviceNameExpression": device["device_name"],
                "deviceNameExpressionSource": "constant",
                "deviceProfileExpression": device["profile_name"],
                "deviceProfileExpressionSource": "constant",
            },
            "attributes": [],
            "timeseries": timeseries,
            "rpc_methods": [],
            "attributes_updates": [],
        })
    return {
        "server": {
            "url": mapping["gateway_endpoint"],
            "timeoutInMillis": 5000,
            "scanPeriodInMillis": 3600000,
            "pollPeriodInMillis": 1000,
            "enableSubscriptions": True,
            "subCheckPeriodInMillis": 100,
            "showMap": False,
            "security": "None",
            "identity": {"type": "anonymous"},
        },
        "mapping": mappings,
    }


def build_s7_config(mapping: Dict[str, Any]) -> Dict[str, Any]:
    devices = []
    for device in mapping["devices"].values():
        timeseries = []
        for key, point in device["points"].items():
            if point.get("type") == "skip":
                continue
            item: Dict[str, Any] = {
                "type": "data",
                "key": key,
                "dataType": point["type"],
                "dbNumber": device["db_number"],
                "start": point["offset"],
                "size": point["size"],
            }
            if point["type"] == "bool":
                item["bit"] = point["bit"]
            timeseries.append(item)
        devices.append({
            "type": "PLC",
            "address": mapping["gateway_host"],
            "port": mapping["port"],
            "rack": 0,
            "slot": 1,
            "deviceName": device["device_name"],
            "deviceProfileName": device["profile_name"],
            "autoReconnect": True,
            "maxRetries": 3,
            "retryDelay": 1,
            "maxDelay": 30,
            "heartbeatInterval": 5,
            "pollPeriod": 1000,
            "attributes": [],
            "timeseries": timeseries,
            "attributeUpdates": [],
            "serverSideRpc": [],
        })
    return {"devices": devices}


def build_can_config(mapping: Dict[str, Any]) -> Dict[str, Any]:
    devices = []
    for device in mapping["devices"].values():
        timeseries = []
        for key, point in device["points"].items():
            if point["type"] == "bool":
                value = "0:1:int"
            elif point["type"] == "float":
                value = "0:4:big:float"
            else:
                value = "0:4:big:int:signed"
            timeseries.append({
                "key": key,
                "nodeId": point["frame_id"],
                "value": value,
            })
        devices.append({
            "name": device["device_name"],
            "type": device["profile_name"],
            "sendDataOnlyOnChange": False,
            "attributes": [],
            "timeseries": timeseries,
            "attributeUpdates": [],
            "serverSideRpc": [],
        })
    return {
        "interface": mapping["interface"],
        "channel": mapping["channel"],
        "backend": {"port": mapping["port"], "fd": False},
        "reconnectPeriod": 5,
        "devices": devices,
    }


def build_odbc_config(mapping: Dict[str, Any], odbc_host: str) -> Dict[str, Any]:
    connection = (
        "Driver={PostgreSQL Unicode};"
        f"Server={odbc_host};Port=5432;Database={mapping['database']};"
        f"Uid={mapping['user']};Pwd={mapping['password']};"
    )
    return {
        "connection": {
            "str": connection,
            "attributes": {"autocommit": True, "timeout": 0},
            "encoding": "utf-8",
            "decoding": {"char": "utf-8", "wchar": "utf-8", "metadata": "utf-8"},
            "reconnect": True,
            "reconnectPeriod": 60,
        },
        "pyodbc": {"pooling": False},
        "polling": {
            "query": (
                "SELECT device_name, product_id, ts, key, value_text, "
                "value_double, value_bool FROM gateway_telemetry "
                "WHERE ts > ? ORDER BY ts ASC LIMIT 1000"
            ),
            "period": 1,
            "iterator": {
                "column": "ts",
                "query": "SELECT COALESCE(MIN(ts), 0) - 1 FROM gateway_telemetry",
                "save": False,
            },
        },
        "mapping": {
            "device": {"type": "odbc", "name": "device_name"},
            "sendDataOnlyOnChange": False,
            "attributes": [],
            "timeseries": [
                {
                    "nameExpression": "key",
                    "value": (
                        "value_double if value_double is not None else "
                        "(value_bool if value_bool is not None else value_text)"
                    ),
                }
            ],
        },
    }


def main() -> int:
    args = parse_args()
    ports = {
        "modbus": args.modbus_port,
        "opcua": args.opcua_port,
        "s7": args.s7_port,
        "can": args.can_port,
    }
    try:
        mapping = build_mapping(
            Path(args.tsl_dir),
            Path(args.sub_devices_csv),
            args.protocol,
            host=args.host,
            gateway_host=args.gateway_host,
            ports=ports,
        )
    except MappingError as exc:
        print(f"error: {exc}")
        return 1

    output = Path(args.output_dir)
    write_json(output / f"connector-mapping-{args.protocol}.json", mapping)
    write_json(output / "tb_gateway.json", build_tb_gateway(args.protocol, args.gateway_host))

    if args.protocol == "modbus":
        config = build_modbus_config(mapping)
    elif args.protocol == "opcua":
        config = build_opcua_config(mapping)
    elif args.protocol == "s7":
        config = build_s7_config(mapping)
    elif args.protocol == "can":
        config = build_can_config(mapping)
    else:
        config = build_odbc_config(mapping, args.odbc_host)

    write_json(output / f"{args.protocol}.json", config)
    print(f"generated protocol={args.protocol} devices={len(mapping['devices'])}")
    print(f"mapping={output / f'connector-mapping-{args.protocol}.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
