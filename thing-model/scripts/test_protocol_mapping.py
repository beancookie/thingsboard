#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from generate_gateway_config import (
    build_can_config,
    build_modbus_config,
    build_odbc_config,
    build_opcua_config,
    build_s7_config,
)
from protocol_mapping import build_mapping
from protocol_writers import _float_words, _int_words


TSL = {
    "version": "1.0",
    "properties": [
        {"id": "temperature", "define": {"type": "float", "min": 0, "max": 100}},
        {"id": "energy", "define": {"type": "int", "min": 0, "max": 1000}},
        {"id": "relay", "define": {"type": "bool"}},
        {"id": "info", "define": {"type": "struct", "specs": {}}},
    ],
    "events": [],
    "actions": [],
    "profile": {"ProductId": "P1", "CategoryId": "1"},
}


class MappingTest(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "p1.json").write_text(json.dumps(TSL), encoding="utf-8")
        (root / "sub-devices.csv").write_text(
            "product_id,device_name,profile_name\n"
            "P1,DEV-01,Profile 1\n"
            "P1,DEV-02,Profile 1\n",
            encoding="utf-8",
        )
        self.root = root

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def mapping(self, protocol: str):
        return build_mapping(
            self.root,
            self.root / "sub-devices.csv",
            protocol,
            host="127.0.0.1",
            gateway_host="host.docker.internal",
        )

    def test_modbus_addresses_and_unit_ids(self) -> None:
        mapping = self.mapping("modbus")
        first = mapping["devices"]["DEV-01"]
        second = mapping["devices"]["DEV-02"]
        self.assertEqual(1, first["unit_id"])
        self.assertEqual(2, second["unit_id"])
        self.assertEqual(0, first["points"]["temperature"]["address"])
        self.assertEqual(2, first["points"]["energy"]["address"])
        self.assertEqual(0, first["points"]["relay"]["address"])
        self.assertEqual("skip", first["points"]["info"]["area"])
        config = build_modbus_config(mapping)
        slave = config["master"]["slaves"][0]
        self.assertEqual("DEV-01", slave["deviceName"])
        self.assertEqual("Profile 1", slave["deviceProfileName"])
        self.assertEqual("32float", slave["timeseries"][0]["type"])

    def test_opcua_nodes_and_config(self) -> None:
        mapping = self.mapping("opcua")
        device = mapping["devices"]["DEV-01"]
        self.assertIn("temperature", device["nodes"])
        self.assertNotIn("info", device["nodes"])
        self.assertEqual(
            "opc.tcp://host.docker.internal:4840", mapping["gateway_endpoint"])
        config = build_opcua_config(mapping)
        self.assertEqual(2, len(config["mapping"]))

    def test_s7_offsets(self) -> None:
        mapping = self.mapping("s7")
        device = mapping["devices"]["DEV-01"]
        self.assertEqual(0, device["points"]["temperature"]["offset"])
        self.assertEqual(4, device["points"]["energy"]["offset"])
        self.assertEqual(8, device["points"]["relay"]["offset"])
        config = build_s7_config(mapping)
        self.assertEqual("real", config["devices"][0]["timeseries"][0]["dataType"])

    def test_can_skips_struct(self) -> None:
        mapping = self.mapping("can")
        device = mapping["devices"]["DEV-01"]
        self.assertNotIn("info", device["points"])
        self.assertEqual("float", device["points"]["temperature"]["type"])
        config = build_can_config(mapping)
        self.assertEqual("0:4:big:float", config["devices"][0]["timeseries"][0]["value"])

    def test_odbc_config(self) -> None:
        mapping = self.mapping("odbc")
        config = build_odbc_config(mapping, "odbc-db")
        self.assertIn("PostgreSQL Unicode", config["connection"]["str"])
        self.assertIn("gateway_telemetry", config["polling"]["query"])

    def test_writer_encoding_helpers(self) -> None:
        self.assertEqual(2, len(_float_words(1.5)))
        self.assertEqual(2, len(_int_words(42)))


if __name__ == "__main__":
    unittest.main()
