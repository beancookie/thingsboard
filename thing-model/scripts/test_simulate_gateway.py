#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from simulate_gateway import (
    build_batch_telemetry_payload,
    build_connect_payload,
    build_disconnect_payload,
    build_telemetry_payload,
    build_values,
    chunked,
    split_devices,
)
from simulate_telemetry import TelemetryGenerator


class GatewayPayloadTest(unittest.TestCase):

    def setUp(self) -> None:
        properties = [
            {
                "id": "speed",
                "define": {"type": "float", "min": 0, "max": 100},
            }
        ]
        events = [
            {
                "id": "alarm",
                "type": "alert",
                "params": [
                    {
                        "id": "address",
                        "define": {"type": "string"},
                    }
                ],
            }
        ]
        self.generator = TelemetryGenerator(
            properties, events, random.Random(1))

    def test_connect_payload(self) -> None:
        payload = build_connect_payload("4DZDCQUA2D-gw-0001", "4DZDCQUA2D")

        self.assertEqual("4DZDCQUA2D-gw-0001", payload["device"])
        self.assertEqual("4DZDCQUA2D", payload["type"])

    def test_disconnect_payload(self) -> None:
        payload = build_disconnect_payload("4DZDCQUA2D-gw-0001")

        self.assertEqual({"device": "4DZDCQUA2D-gw-0001"}, payload)

    def test_telemetry_payload(self) -> None:
        payload = build_telemetry_payload(
            "4DZDCQUA2D-gw-0001", {"speed": 12.5}, ts=1793253653000)

        self.assertEqual([{"ts": 1793253653000, "values": {"speed": 12.5}}],
                         payload["4DZDCQUA2D-gw-0001"])

    def test_event_values_use_events_array(self) -> None:
        values = build_values(self.generator, "event", 2)

        self.assertEqual(2, len(values["events"]))
        self.assertEqual(
            {"alarm"}, {item["event_id"] for item in values["events"]})
        self.assertEqual(
            values, json.loads(json.dumps(values, ensure_ascii=False)))

    def test_telemetry_values(self) -> None:
        values = build_values(self.generator, "telemetry", 4)

        self.assertIn("speed", values)
        self.assertNotIn("events", values)

    def test_split_devices_balances_gateways(self) -> None:
        devices = [f"dev-{index:02d}" for index in range(50)]
        groups = split_devices(devices, 2)

        self.assertEqual(25, len(groups[0]))
        self.assertEqual(25, len(groups[1]))
        self.assertEqual(set(devices), set(groups[0] + groups[1]))

    def test_chunked_uses_batch_size(self) -> None:
        batches = list(chunked(list(range(25)), 10))

        self.assertEqual([10, 10, 5], [len(batch) for batch in batches])

    def test_batch_telemetry_payload(self) -> None:
        payload = build_batch_telemetry_payload(
            [("dev-01", {"speed": 1}), ("dev-02", {"speed": 2})],
            ts=1793253653000,
        )

        self.assertEqual(2, len(payload))
        self.assertEqual(
            [{"ts": 1793253653000, "values": {"speed": 1}}],
            payload["dev-01"])


if __name__ == "__main__":
    unittest.main()
