#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from setup_gateway import ApiError, load_products, resolve_output_path


class LoadProductsTest(unittest.TestCase):

    def test_loads_product_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "a.json").write_text(
                json.dumps({"profile": {"ProductId": "AAA"}, "properties": []}),
                encoding="utf-8",
            )
            (directory / "b.json").write_text(
                json.dumps({"profile": {"productId": "BBB"}, "properties": []}),
                encoding="utf-8",
            )

            products = load_products(directory)

            self.assertEqual(["AAA", "BBB"], [item["product_id"] for item in products])

    def test_missing_product_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "a.json").write_text(
                json.dumps({"properties": []}), encoding="utf-8")

            with self.assertRaises(ApiError):
                load_products(directory)

    def test_duplicate_product_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name in ("a.json", "b.json"):
                (directory / name).write_text(
                    json.dumps({"profile": {"ProductId": "AAA"}}), encoding="utf-8")

            with self.assertRaises(ApiError):
                load_products(directory)

    def test_invalid_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "a.json").write_bytes(b'{"profile":{"ProductId":"\xa0"}}')

            with self.assertRaises(ApiError):
                load_products(directory)


class ResolveOutputPathTest(unittest.TestCase):

    def test_keeps_name_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = resolve_output_path(tmp, "sub-devices.csv")

            self.assertEqual(Path(tmp) / "sub-devices.csv", path)

    def test_adds_timestamp_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / "sub-devices.csv"
            existing.write_text("existing", encoding="utf-8")

            path = resolve_output_path(tmp, "sub-devices.csv")

            self.assertNotEqual(existing, path)
            self.assertTrue(path.stem.startswith("sub-devices-"))
            self.assertEqual(".csv", path.suffix)


if __name__ == "__main__":
    unittest.main()
