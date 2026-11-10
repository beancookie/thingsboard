#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from export_products import (
    CSV_FIELDS,
    ProductExportClient,
    base_row,
    sanitize_filename,
    write_csv,
    write_json,
)


class FakeResponse:

    def __init__(self, payload, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:

    def __init__(self, responses: list) -> None:
        self.responses = list(responses)
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, headers))
        return self.responses.pop(0)


class SanitizeFilenameTest(unittest.TestCase):

    def test_replaces_invalid_characters(self) -> None:
        self.assertEqual("A_B_C", sanitize_filename('A/B\\C'))

    def test_falls_back_for_blank(self) -> None:
        self.assertEqual("product", sanitize_filename("   "))

    def test_keeps_safe_product_id(self) -> None:
        self.assertEqual("SCENE_LIGHT", sanitize_filename("SCENE_LIGHT"))


class BaseRowTest(unittest.TestCase):

    def test_maps_metadata_fields(self) -> None:
        row = base_row({
            "productId": "P1",
            "name": "电表",
            "model": "P1",
            "categoryId": "1",
            "tslVersion": "1.2",
            "status": "PUBLISHED",
            "propertyCount": 21,
            "eventCount": 6,
            "actionCount": 3,
            "tbProfileId": "profile",
            "tbAssetId": "asset",
            "tbRuleChainId": "chain",
            "updatedAt": "2026-11-06T08:21:11.972243Z",
        })

        self.assertEqual("P1", row["product_id"])
        self.assertEqual("电表", row["name"])
        self.assertEqual(21, row["property_count"])
        self.assertEqual("profile", row["tb_profile_id"])
        self.assertEqual("", row["tsl_file"])
        self.assertEqual("", row["error"])

    def test_missing_fields_become_empty(self) -> None:
        row = base_row({})

        self.assertEqual("", row["product_id"])
        self.assertIsNone(row["property_count"])


class WriteOutputTest(unittest.TestCase):

    def test_csv_has_all_columns_and_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "products.csv"
            write_csv(path, [base_row({"productId": "P1", "name": "电表"})])

            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
            with path.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(CSV_FIELDS, list(rows[0].keys()))
            self.assertEqual("电表", rows[0]["name"])

    def test_json_preserves_chinese(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "products.json"
            write_json(path, {"name": "电表"})

            text = path.read_text(encoding="utf-8")
            self.assertIn("电表", text)
            self.assertEqual({"name": "电表"}, json.loads(text))


class ClientEndpointsTest(unittest.TestCase):

    def client(self) -> ProductExportClient:
        return ProductExportClient(
            "https://tb.example.com",
            "https://tb.example.com/api/thing-model",
            1,
        )

    def test_list_products(self) -> None:
        client = self.client()
        client.session = FakeSession([FakeResponse([{"productId": "P1"}])])

        products = client.list_products("jwt")

        self.assertEqual([{"productId": "P1"}], products)
        self.assertTrue(
            client.session.calls[0][0].endswith("/api/thing-model/products"))

    def test_get_thing_model_escapes_product_id(self) -> None:
        client = self.client()
        client.session = FakeSession([FakeResponse({"tsl": {}})])

        client.get_thing_model("jwt", "A B")

        self.assertTrue(
            client.session.calls[0][0].endswith(
                "/api/thing-model/products/A%20B/thing-model"))


if __name__ == "__main__":
    unittest.main()
