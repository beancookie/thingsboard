#!/usr/bin/env python3
from __future__ import annotations

import json
import struct
import time
from pathlib import Path
from typing import Any, Dict

from protocol_mapping import PROTOCOLS, MappingError


class ProtocolWriter:
    protocol = ""

    def write(self, device: Dict[str, Any], values: Dict[str, Any]) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


def load_mapping(path: str, protocol: str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("protocol") != protocol:
        raise MappingError(
            f"mapping protocol {data.get('protocol')} does not match --protocol {protocol}")
    return data


class ModbusWriter(ProtocolWriter):
    protocol = "modbus"

    def __init__(self, mapping: Dict[str, Any]) -> None:
        try:
            from pymodbus.client import ModbusTcpClient
        except ImportError as exc:
            raise MappingError(
                "pymodbus is required for --protocol modbus: pip install pymodbus") from exc
        self._modbus = ModbusTcpClient(mapping["host"], port=int(mapping["port"]))
        if not self._modbus.connect():
            raise MappingError(
                f"cannot connect to Modbus simulator at {mapping['host']}:{mapping['port']}")

    def write(self, device: Dict[str, Any], values: Dict[str, Any]) -> None:
        unit_id = device["unit_id"]
        for key, value in values.items():
            point = device["points"].get(key)
            if not point or point.get("area") == "skip":
                continue
            if point["type"] == "bool":
                result = self._modbus.write_coil(
                    point["address"], bool(value), device_id=unit_id)
            elif point["type"] == "float":
                result = self._modbus.write_registers(
                    point["address"], _float_words(value), device_id=unit_id)
            else:
                result = self._modbus.write_registers(
                    point["address"], _int_words(value), device_id=unit_id)
            if result.isError():
                raise MappingError(f"Modbus write failed for {device['device_name']}.{key}")

    def close(self) -> None:
        self._modbus.close()


class OpcUaWriter(ProtocolWriter):
    protocol = "opcua"

    def __init__(self, mapping: Dict[str, Any]) -> None:
        try:
            from asyncua.sync import Client
        except ImportError as exc:
            raise MappingError(
                "asyncua is required for --protocol opcua: pip install asyncua") from exc
        self._client = Client(mapping["endpoint"])
        self._client.connect()

    def write(self, device: Dict[str, Any], values: Dict[str, Any]) -> None:
        for key, value in values.items():
            node = device["nodes"].get(key)
            if not node:
                continue
            self._client.get_node(node["node_id"]).write_value(value)

    def close(self) -> None:
        try:
            self._client.disconnect()
        except Exception:
            pass


class S7Writer(ProtocolWriter):
    protocol = "s7"

    def __init__(self, mapping: Dict[str, Any]) -> None:
        try:
            from snap7.client import Client
        except ImportError as exc:
            raise MappingError(
                "python-snap7 is required for --protocol s7: pip install python-snap7") from exc
        self._client = Client()
        self._client.connect(mapping["host"], 0, 1, tcp_port=int(mapping["port"]))

    def write(self, device: Dict[str, Any], values: Dict[str, Any]) -> None:
        for key, value in values.items():
            point = device["points"].get(key)
            if not point or point["type"] == "skip":
                continue
            if point["type"] == "bool":
                data = bytes([1 if value else 0])
            elif point["type"] == "real":
                data = struct.pack(">f", float(value))
            else:
                data = struct.pack(">i", int(value))
            self._client.db_write(
                device["db_number"], point["offset"], bytearray(data))

    def close(self) -> None:
        try:
            self._client.disconnect()
        except Exception:
            pass


class CanWriter(ProtocolWriter):
    protocol = "can"

    def __init__(self, mapping: Dict[str, Any]) -> None:
        try:
            import can
        except ImportError as exc:
            raise MappingError(
                "python-can is required for --protocol can: pip install python-can") from exc
        self._can = can
        self._bus = can.Bus(
            interface=mapping.get("interface", "udp_multicast"),
            channel=mapping.get("channel", "239.255.0.1"),
            port=int(mapping["port"]),
            fd=bool(mapping.get("fd", False)),
        )

    def write(self, device: Dict[str, Any], values: Dict[str, Any]) -> None:
        for key, value in values.items():
            point = device["points"].get(key)
            if not point or point.get("type") == "skip":
                continue
            if point["type"] == "bool":
                data = bytes([1 if value else 0])
            elif point["type"] == "float":
                data = struct.pack(">f", float(value))
            else:
                data = struct.pack(">i", int(value))
            self._bus.send(self._can.Message(
                arbitration_id=point["frame_id"],
                data=data,
                is_extended_id=False,
            ))

    def close(self) -> None:
        self._bus.shutdown()


class OdbcWriter(ProtocolWriter):
    protocol = "odbc"

    def __init__(self, mapping: Dict[str, Any]) -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise MappingError(
                "psycopg is required for --protocol odbc: pip install 'psycopg[binary]'") from exc
        conninfo = (
            f"host={mapping['host']} port={mapping['port']} "
            f"dbname={mapping['database']} user={mapping['user']} "
            f"password={mapping['password']} connect_timeout=5")
        self._conn = psycopg.connect(conninfo, autocommit=True)

    def write(self, device: Dict[str, Any], values: Dict[str, Any]) -> None:
        ts = int(time.time() * 1000)
        rows = []
        for key, value in values.items():
            point = device["points"].get(key)
            if not point:
                continue
            data_type = point["type"]
            value_text = None
            value_double = None
            value_bool = None
            if data_type in ("bool", "boolean"):
                value_bool = bool(value)
            elif data_type in ("float", "double", "int", "timestamp"):
                value_double = float(value)
            else:
                value_text = str(value)
            rows.append((
                device["device_name"], device["product_id"], ts, key,
                value_text, value_double, value_bool,
            ))
        if not rows:
            return
        with self._conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO gateway_telemetry "
                "(device_name, product_id, ts, key, value_text, value_double, value_bool) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                rows,
            )

    def close(self) -> None:
        self._conn.close()


WRITERS = {
    "modbus": ModbusWriter,
    "opcua": OpcUaWriter,
    "s7": S7Writer,
    "can": CanWriter,
    "odbc": OdbcWriter,
}


def create_writer(protocol: str, mapping: Dict[str, Any]) -> ProtocolWriter:
    if protocol not in PROTOCOLS:
        raise MappingError(f"unsupported protocol: {protocol}")
    return WRITERS[protocol](mapping)


def _float_words(value: Any) -> list[int]:
    raw = struct.pack(">f", float(value))
    return list(struct.unpack(">HH", raw))


def _int_words(value: Any) -> list[int]:
    raw = struct.pack(">i", int(value))
    return list(struct.unpack(">HH", raw))
