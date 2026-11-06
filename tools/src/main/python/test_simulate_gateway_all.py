#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from simulate_gateway_all import (
    ApiError,
    build_gateway_telemetry,
    load_sub_devices_by_product,
    select_kind,
)


class LoadSubDevicesTest(unittest.TestCase):

    def test_groups_products_and_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub-devices.csv"
            path.write_text(
                "product_id,device_name\n"
                "AAA,AAA-01\n"
                "BBB,BBB-01\n"
                "AAA,AAA-02\n"
                "AAA,AAA-01\n",
                encoding="utf-8",
            )

            groups = load_sub_devices_by_product(str(path))

            self.assertEqual(["AAA-01", "AAA-02"], groups["AAA"])
            self.assertEqual(["BBB-01"], groups["BBB"])

    def test_missing_file(self) -> None:
        with self.assertRaises(ApiError):
            load_sub_devices_by_product("missing.csv")

    def test_empty_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub-devices.csv"
            path.write_text("product_id,device_name\n", encoding="utf-8")

            with self.assertRaises(ApiError):
                load_sub_devices_by_product(str(path))


class GatewayTelemetryTest(unittest.TestCase):

    def test_builds_gateway_statistics(self) -> None:
        payload = build_gateway_telemetry(2, 8, random.Random(1))

        service = json.loads(payload["serviceStats"])
        machine = json.loads(payload["machineStats"])
        self.assertEqual(16, service["storageMsgCount"])
        self.assertEqual(16, service["storageMsgPulled"])
        self.assertEqual(16, machine["msgsSentToPlatform"])
        self.assertEqual(0, payload["ALL_ERRORS_COUNT"])


class SelectKindTest(unittest.TestCase):

    def test_auto_with_events_alternates(self) -> None:
        self.assertEqual("telemetry", select_kind("auto", True, 0))
        self.assertEqual("event", select_kind("auto", True, 1))
        self.assertEqual("telemetry", select_kind("auto", True, 2))

    def test_auto_without_events_uses_telemetry(self) -> None:
        self.assertEqual("telemetry", select_kind("auto", False, 0))
        self.assertEqual("telemetry", select_kind("auto", False, 1))

    def test_explicit_modes(self) -> None:
        self.assertEqual("telemetry", select_kind("telemetry", True, 1))
        self.assertEqual("event", select_kind("event", False, 1))
        self.assertEqual("event", select_kind("mixed", False, 1))


if __name__ == "__main__":
    unittest.main()
