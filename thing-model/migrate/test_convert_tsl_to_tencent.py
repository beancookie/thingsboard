#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from convert_tencent_tsl import convert_document as convert_to_tsl
from convert_tsl_to_tencent import convert_document as convert_to_tencent


ROOT = Path(__file__).resolve().parents[2]
DLT645 = ROOT / "thing-model" / "migrate" / "DLT645智能电表.tsl.json"


class ConvertTslToTencentTest(unittest.TestCase):

    def test_converts_dlt645_model(self) -> None:
        source = json.loads(DLT645.read_text(encoding="utf-8"))
        converted = convert_to_tencent(source)

        self.assertEqual("YUMRMRPOGP", converted["profile"]["ProductId"])
        self.assertEqual(21, len(converted["properties"]))
        self.assertEqual(6, len(converted["events"]))
        self.assertEqual(3, len(converted["actions"]))

        meter_info = converted["properties"][0]["define"]
        self.assertIsInstance(meter_info["specs"], list)
        self.assertEqual("string", meter_info["specs"][0]["dataType"]["type"])

        voltage = next(p for p in converted["properties"] if p["id"] == "UA_V")
        self.assertEqual("0", voltage["define"]["min"])
        self.assertEqual("300", voltage["define"]["max"])

        phase = converted["events"][0]["params"][0]["define"]
        self.assertEqual("stringenum", phase["type"])

        fault = next(e for e in converted["events"] if e["id"] == "meterFault")
        fault_code = next(p for p in fault["params"] if p["id"] == "code")
        self.assertEqual("0", fault_code["define"]["min"])
        self.assertEqual("2048", fault_code["define"]["max"])

        self.assertEqual("0", meter_info["specs"][0]["dataType"]["min"])
        self.assertEqual("2048", meter_info["specs"][0]["dataType"]["max"])

        relay = next(p for p in converted["properties"] if p["id"] == "relayState")
        self.assertEqual({"0": "否", "1": "是"}, relay["define"]["mapping"])
        for action in converted["actions"]:
            for group in ("input", "output"):
                for param in action.get(group, []):
                    if param["define"].get("type") == "bool":
                        self.assertIn("mapping", param["define"])
                    if param["define"].get("type") in ("int", "float"):
                        self.assertIn("start", param["define"])
                        self.assertIn("step", param["define"])

        apply_config = next(a for a in converted["actions"] if a["id"] == "applyConfig")
        report_interval = apply_config["input"][0]["define"]
        self.assertEqual("5", report_interval["start"])
        self.assertEqual("1", report_interval["step"])

    def test_round_trip_keeps_model(self) -> None:
        source = json.loads(DLT645.read_text(encoding="utf-8"))
        tencent = convert_to_tencent(source)
        restored = convert_to_tsl(tencent)

        self.assertEqual(source["profile"], restored["profile"])
        self.assertEqual(len(source["properties"]), len(restored["properties"]))
        self.assertEqual(len(source["events"]), len(restored["events"]))
        self.assertEqual(len(source["actions"]), len(restored["actions"]))
        self.assertEqual(source["properties"][0]["id"], restored["properties"][0]["id"])
        self.assertEqual(source["actions"][1]["id"], restored["actions"][1]["id"])


if __name__ == "__main__":
    unittest.main()
