#!/usr/bin/env python3
from __future__ import annotations

import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from create_scene_demo import SCENE_DEVICES, SCENE_RELATIONS
from simulate_scene_demo import (
    load_devices,
    normalize_mode,
    normalize_state,
    sensor_payload,
)


class SceneDefinitionsTest(unittest.TestCase):

    def test_device_names(self) -> None:
        names = [item["device_name"] for item in SCENE_DEVICES]
        self.assertEqual([
            "motion-01",
            "light-sensor-01",
            "light-01",
            "temperature-01",
            "air-conditioner-01",
        ], names)

    def test_relations(self) -> None:
        self.assertIn(
            ("motion-01", "light-01", "Controls"), SCENE_RELATIONS)
        self.assertIn(
            ("motion-01", "light-sensor-01", "ConnectedTo"), SCENE_RELATIONS)
        self.assertIn(
            ("temperature-01", "air-conditioner-01", "Controls"),
            SCENE_RELATIONS)


class ScenePayloadTest(unittest.TestCase):

    def test_motion_payload_toggles(self) -> None:
        device = {"product_id": "SCENE_MOTION", "device_name": "motion-01"}
        rng = random.Random(1)
        self.assertTrue(sensor_payload(device, 0, rng)["motion"])
        self.assertFalse(sensor_payload(device, 1, rng)["motion"])

    def test_light_sensor_payload(self) -> None:
        device = {
            "product_id": "SCENE_LIGHT_SENSOR",
            "device_name": "light-sensor-01",
        }
        payload = sensor_payload(device, 0, random.Random(1))
        self.assertIn("illuminance", payload)
        self.assertGreaterEqual(payload["illuminance"], 0)

    def test_temperature_payload(self) -> None:
        device = {
            "product_id": "SCENE_TEMPERATURE",
            "device_name": "temperature-01",
        }
        payload = sensor_payload(device, 0, random.Random(1))
        self.assertIn("temperature", payload)
        self.assertIn("humidity", payload)

    def test_normalizes_state_and_mode(self) -> None:
        self.assertEqual("ON", normalize_state(True))
        self.assertEqual("OFF", normalize_state(False))
        self.assertEqual("ON", normalize_state("on"))
        self.assertEqual("COOL", normalize_mode("cool"))
        self.assertEqual("OFF", normalize_mode("off"))


class LoadDevicesTest(unittest.TestCase):

    def test_loads_tokens_and_skips_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scene-devices.csv"
            path.write_text(
                "product_id,device_name,access_token,scene_role\n"
                "SCENE_MOTION,motion-01,token-1,trigger\n"
                "SCENE_LIGHT,light-01,,actuator\n",
                encoding="utf-8",
            )

            devices = load_devices(str(path))

            self.assertEqual(1, len(devices))
            self.assertEqual("motion-01", devices[0]["device_name"])
            self.assertEqual("token-1", devices[0]["access_token"])


if __name__ == "__main__":
    unittest.main()
