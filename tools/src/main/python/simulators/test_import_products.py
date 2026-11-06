#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from import_products import (
    ApiError,
    ProductImportClient,
    build_payload,
    format_issues,
    load_product_files,
    resolve_output_path,
)


def write_model(path: Path, product_id: str = "P1",
                category_id: str = "1", version: str = "1.0",
                encoding: str = "utf-8") -> None:
    document = {
        "version": version,
        "profile": {"ProductId": product_id, "CategoryId": category_id},
        "properties": [{
            "id": "temperature",
            "name": "温度",
            "mode": "r",
            "define": {"type": "float", "min": -40, "max": 125},
            "required": False,
        }],
        "events": [],
        "actions": [],
    }
    path.write_text(json.dumps(document, ensure_ascii=False), encoding=encoding)


class LoadProductFilesTest(unittest.TestCase):

    def test_maps_filename_to_name_and_product_id_to_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_model(directory / "CoAP姿态监测仪.json", "AAA", "1", "1.0")

            products = load_product_files(directory)

            self.assertEqual(1, len(products))
            product = products[0]
            self.assertEqual("CoAP姿态监测仪", product["name"])
            self.assertEqual("AAA", product["product_id"])
            self.assertEqual("AAA", product["model"])
            self.assertEqual("1", product["category_id"])
            self.assertEqual("1.0", product["tsl_version"])
            self.assertEqual("AAA", product["tsl"]["profile"]["ProductId"])

    def test_reads_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_model(directory / "bom.json", "BBB", encoding="utf-8-sig")

            products = load_product_files(directory)

            self.assertEqual("BBB", products[0]["product_id"])

    def test_missing_product_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "a.json").write_text(
                json.dumps({"version": "1.0", "properties": []}),
                encoding="utf-8")

            with self.assertRaises(ApiError):
                load_product_files(directory)

    def test_duplicate_product_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_model(directory / "a.json", "AAA")
            write_model(directory / "b.json", "AAA")

            with self.assertRaises(ApiError):
                load_product_files(directory)

    def test_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "a.json").write_text("{", encoding="utf-8")

            with self.assertRaises(ApiError):
                load_product_files(directory)

    def test_invalid_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "a.json").write_bytes(b'{"profile":{"ProductId":"\xa0"}}')

            with self.assertRaises(ApiError):
                load_product_files(directory)

    def test_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ApiError):
                load_product_files(Path(tmp) / "missing")


class ProductApiBaseTest(unittest.TestCase):

    def test_service_root(self) -> None:
        client = ProductImportClient("http://tb", "http://thingmodel:8090", 1)

        self.assertEqual(
            "http://thingmodel:8090/api/products", client.product_api_base)

    def test_gateway_proxy_prefix(self) -> None:
        client = ProductImportClient(
            "https://tb.example.com",
            "https://tb.example.com/api/thing-model",
            1,
        )

        self.assertEqual(
            "https://tb.example.com/api/thing-model/products",
            client.product_api_base)

    def test_explicit_api_suffix(self) -> None:
        client = ProductImportClient("http://tb", "http://thingmodel:8090/api", 1)

        self.assertEqual(
            "http://thingmodel:8090/api/products", client.product_api_base)


class ApiKeyTokenTest(unittest.TestCase):

    def test_prefixes_bare_key(self) -> None:
        client = ProductImportClient("http://tb", "http://thingmodel:8090", 1)

        self.assertEqual("ApiKey tb_abc", client.api_key_token("tb_abc"))

    def test_keeps_existing_prefix(self) -> None:
        client = ProductImportClient("http://tb", "http://thingmodel:8090", 1)

        self.assertEqual("ApiKey tb_abc", client.api_key_token("ApiKey tb_abc"))

    def test_rejects_blank_key(self) -> None:
        client = ProductImportClient("http://tb", "http://thingmodel:8090", 1)

        with self.assertRaises(ApiError):
            client.api_key_token("   ")

    def test_auth_headers_use_api_key_prefix(self) -> None:
        client = ProductImportClient("http://tb", "http://thingmodel:8090", 1)

        self.assertEqual(
            {"X-Authorization": "ApiKey tb_abc"},
            client._auth_headers(client.api_key_token("tb_abc")))

    def test_auth_headers_use_bearer_for_jwt(self) -> None:
        client = ProductImportClient("http://tb", "http://thingmodel:8090", 1)

        self.assertEqual(
            {"X-Authorization": "Bearer eyJ.payload.signature"},
            client._auth_headers("eyJ.payload.signature"))


class FakeResponse:

    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


class FakeSession:

    def __init__(self, responses: list) -> None:
        self.responses = list(responses)
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, headers))
        return self.responses.pop(0)


class ExchangeApiKeyForTokenTest(unittest.TestCase):

    def test_returns_jwt_from_thingsboard(self) -> None:
        client = ProductImportClient(
            "https://tb.example.com",
            "https://tb.example.com/api/thing-model",
            1,
        )
        client.session = FakeSession([
            FakeResponse({"id": {"id": "user-1"}}),
            FakeResponse({"token": "jwt-token"}),
        ])

        token = client.exchange_api_key_for_token("tb_key")

        self.assertEqual("jwt-token", token)
        self.assertEqual(
            "ApiKey tb_key", client.session.calls[0][1]["X-Authorization"])
        self.assertTrue(
            client.session.calls[1][0].endswith("/api/user/user-1/token"))

    def test_rejects_missing_user_id(self) -> None:
        client = ProductImportClient(
            "https://tb.example.com",
            "https://tb.example.com/api/thing-model",
            1,
        )
        client.session = FakeSession([FakeResponse({"id": {}})])

        with self.assertRaises(ApiError):
            client.exchange_api_key_for_token("tb_key")

    def test_rejects_missing_token(self) -> None:
        client = ProductImportClient(
            "https://tb.example.com",
            "https://tb.example.com/api/thing-model",
            1,
        )
        client.session = FakeSession([
            FakeResponse({"id": {"id": "user-1"}}),
            FakeResponse({}),
        ])

        with self.assertRaises(ApiError):
            client.exchange_api_key_for_token("tb_key")


class BuildPayloadTest(unittest.TestCase):

    def test_builds_create_request(self) -> None:
        product = {
            "product_id": "P1",
            "name": "设备",
            "model": "P1",
            "category_id": "1",
            "tsl_version": "1.0",
            "tsl": {"profile": {"ProductId": "P1"}},
        }

        payload = build_payload(product, strict_unknown=True)

        self.assertEqual("P1", payload["productId"])
        self.assertEqual("设备", payload["name"])
        self.assertEqual("P1", payload["model"])
        self.assertEqual("1", payload["categoryId"])
        self.assertEqual("1.0", payload["tslVersion"])
        self.assertTrue(payload["strictUnknown"])
        self.assertEqual(product["tsl"], payload["tsl"])

    def test_empty_category_id_becomes_null(self) -> None:
        product = {
            "product_id": "P1",
            "name": "设备",
            "model": "P1",
            "category_id": "",
            "tsl_version": "1.0",
            "tsl": {},
        }

        payload = build_payload(product)

        self.assertIsNone(payload["categoryId"])
        self.assertFalse(payload["strictUnknown"])


class FormatIssuesTest(unittest.TestCase):

    def test_formats_code_path_and_message(self) -> None:
        text = format_issues([
            {"code": "ID_DUP", "path": "/properties/2/id", "message": "重复"},
        ])

        self.assertIn("ID_DUP@/properties/2/id", text)
        self.assertIn("重复", text)


class ResolveOutputPathTest(unittest.TestCase):

    def test_keeps_name_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = resolve_output_path(tmp, "product-import-report.csv")

            self.assertEqual(Path(tmp) / "product-import-report.csv", path)

    def test_adds_timestamp_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / "product-import-report.csv"
            existing.write_text("existing", encoding="utf-8")

            path = resolve_output_path(tmp, "product-import-report.csv")

            self.assertNotEqual(existing, path)
            self.assertTrue(path.stem.startswith("product-import-report-"))


if __name__ == "__main__":
    unittest.main()
