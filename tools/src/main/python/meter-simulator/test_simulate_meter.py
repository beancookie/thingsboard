#!/usr/bin/env python3
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from simulate_meter import (
    MeterState,
    apply_shared,
    build_event,
    build_telemetry,
    handle_rpc,
    load_tsl,
    now_ms,
    parse_bool,
)


TSL_PATH = Path(__file__).with_name("meter-thing-model.tsl.json")


class MeterTelemetryTest(unittest.TestCase):

    def setUp(self) -> None:
        self.tsl = load_tsl(str(TSL_PATH))
        self.rng = random.Random(1)
        self.state = MeterState(self.tsl, 5, self.rng)

    def test_payload_contains_all_properties(self) -> None:
        self.state.advance(5)
        payload = build_telemetry(self.state)
        expected = {prop["id"] for prop in self.tsl["properties"]}
        self.assertEqual(expected, set(payload))

    def test_numeric_values_are_within_tsl_ranges(self) -> None:
        for _ in range(20):
            self.state.advance(5)
        payload = build_telemetry(self.state)
        for prop in self.tsl["properties"]:
            define = prop.get("define") or {}
            data_type = define.get("type")
            value = payload[prop["id"]]
            if data_type in ("int", "float"):
                if "min" in define:
                    self.assertGreaterEqual(value, define["min"], prop["id"])
                if "max" in define:
                    self.assertLessEqual(value, define["max"], prop["id"])
            elif data_type == "timestamp":
                self.assertIsInstance(value, int)
            elif data_type == "bool":
                self.assertIsInstance(value, bool)
            elif data_type == "struct":
                self.assertEqual(set(define["specs"]), set(value))

    def test_relay_off_reduces_current_and_power(self) -> None:
        state = MeterState(self.tsl, 5, random.Random(2), relay=False)
        for _ in range(30):
            state.advance(5)
        self.assertLess(state.ia, 0.5)
        self.assertLess(state.ib, 0.5)
        self.assertLess(state.ic, 0.5)
        self.assertLess(state.p, 0.1)


class MeterEventTest(unittest.TestCase):

    def setUp(self) -> None:
        self.tsl = load_tsl(str(TSL_PATH))
        self.rng = random.Random(3)
        self.state = MeterState(self.tsl, 5, self.rng)

    def test_each_event_has_runtime_and_param_fields(self) -> None:
        for event in self.tsl["events"]:
            payload = build_event(self.tsl, self.state, self.rng, event)
            self.assertEqual(event["id"], payload["event_id"])
            self.assertEqual(event["type"], payload["event_type"])
            self.assertIsInstance(payload["event_ts"], int)
            for param in event["params"]:
                self.assertIn(param["id"], payload)

    def test_over_voltage_event_uses_voltage_fields(self) -> None:
        event = next(
            item for item in self.tsl["events"]
            if item["id"] == "overVoltage")
        payload = build_event(self.tsl, self.state, self.rng, event)
        self.assertIn(payload["phase"], ("A", "B", "C", "ALL"))
        self.assertGreaterEqual(payload["voltage"], payload["threshold"])
        self.assertLessEqual(payload["voltage"], 300)
        self.assertEqual(payload["threshold"], 230.0)

    def test_under_voltage_event_is_below_threshold(self) -> None:
        event = next(
            item for item in self.tsl["events"]
            if item["id"] == "underVoltage")
        payload = build_event(self.tsl, self.state, self.rng, event)
        self.assertLessEqual(payload["voltage"], payload["threshold"])
        self.assertGreaterEqual(payload["voltage"], 0)
        self.assertEqual(payload["threshold"], 180.0)

    def test_over_current_event_exceeds_threshold(self) -> None:
        event = next(
            item for item in self.tsl["events"]
            if item["id"] == "overCurrent")
        payload = build_event(self.tsl, self.state, self.rng, event)
        self.assertGreaterEqual(payload["current"], payload["threshold"])
        self.assertLessEqual(payload["current"], 100)
        self.assertEqual(payload["threshold"], 10.0)

    def test_meter_fault_event_has_code_and_message(self) -> None:
        event = next(
            item for item in self.tsl["events"]
            if item["id"] == "meterFault")
        payload = build_event(self.tsl, self.state, self.rng, event)
        self.assertTrue(payload["code"].startswith("E"))
        self.assertIsInstance(payload["message"], str)


class MeterCommandTest(unittest.TestCase):

    def setUp(self) -> None:
        self.tsl = load_tsl(str(TSL_PATH))
        self.state = MeterState(self.tsl, 5, random.Random(4))

    def test_set_relay(self) -> None:
        response = handle_rpc(
            self.state, {"method": "setRelay", "params": {"on": False}})
        self.assertEqual({"success": True}, response)
        self.assertFalse(self.state.relay)
        response = handle_rpc(
            self.state, {"method": "setRelay", "params": {"on": 1}})
        self.assertEqual({"success": True}, response)
        self.assertTrue(self.state.relay)

    def test_set_relay_rejects_invalid_value(self) -> None:
        response = handle_rpc(
            self.state, {"method": "setRelay", "params": {"on": "abc"}})
        self.assertFalse(response["success"])

    def test_apply_config(self) -> None:
        response = handle_rpc(
            self.state,
            {"method": "applyConfig", "params": {"reportInterval": 30}})
        self.assertEqual({"success": True}, response)
        self.assertEqual(30, self.state.report_interval)

    def test_apply_config_rejects_out_of_range(self) -> None:
        for value in (4, 3601, "abc", None):
            response = handle_rpc(
                self.state,
                {"method": "applyConfig",
                 "params": {"reportInterval": value}})
            self.assertFalse(response["success"])

    def test_sync_time(self) -> None:
        target = now_ms()
        response = handle_rpc(
            self.state, {"method": "syncTime", "params": {"time": target}})
        self.assertEqual({"success": True}, response)
        self.assertEqual(target, self.state.last_read_time)

    def test_unknown_method(self) -> None:
        response = handle_rpc(
            self.state, {"method": "unknown", "params": {}})
        self.assertFalse(response["success"])
        self.assertIn("unsupported", response["error"])

    def test_apply_shared(self) -> None:
        changed = apply_shared(
            self.state, {"reportInterval": 15, "relayState": False})
        self.assertTrue(changed)
        self.assertEqual(15, self.state.report_interval)
        self.assertFalse(self.state.relay)
        self.assertFalse(apply_shared(self.state, {"reportInterval": 1}))

    def test_parse_bool(self) -> None:
        self.assertTrue(parse_bool(True))
        self.assertTrue(parse_bool("1"))
        self.assertTrue(parse_bool("on"))
        self.assertFalse(parse_bool(False))
        self.assertFalse(parse_bool("0"))
        self.assertFalse(parse_bool("off"))
        self.assertIsNone(parse_bool("maybe"))


if __name__ == "__main__":
    unittest.main()
