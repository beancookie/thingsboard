#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fix_gateways_dashboard import (
    DEFAULT_RELATION_ALIAS_ID,
    DEFAULT_WIDGET_ID,
    DashboardFixError,
    TbClient,
    apply_gateway_fix,
    dump_json,
    load_json,
    save_backup,
)


def dashboard_fixture() -> dict:
    markdown = (
        "const isActive =\n"
        "  data[0].Status === 'true' &&\n"
        "  (!lastDisconnectTime || lastConnectTime > lastDisconnectTime);\n"
        "createDataBlock(data[0].Name, 'name');\n"
        "createDataBlock(data[0].Type, 'type');\n"
    )
    return {
        "configuration": {
            "entityAliases": {
                DEFAULT_RELATION_ALIAS_ID: {
                    "id": DEFAULT_RELATION_ALIAS_ID,
                    "alias": "GatewayDevices",
                    "filter": {
                        "type": "relationsQuery",
                        "filters": [
                            {
                                "relationType": "创建d",
                                "entityTypes": ["DEVICE"],
                            }
                        ],
                    },
                },
            },
            "widgets": {
                DEFAULT_WIDGET_ID: {
                    "type": "latest",
                    "config": {
                        "settings": {
                            "markdownTextFunction": markdown,
                        },
                        "datasources": [
                            {
                                "dataKeys": [
                                    {"name": "name", "type": "entityField",
                                     "label": "Name"},
                                    {"name": "type", "type": "entityField",
                                     "label": "Type"},
                                    {"name": "active", "type": "attribute",
                                     "label": "状态"},
                                    {"name": "Version", "type": "attribute",
                                     "label": "版本"},
                                ]
                            }
                        ],
                    },
                }
            }
        }
    }


def data_keys(data: dict) -> list:
    widget = data["configuration"]["widgets"][DEFAULT_WIDGET_ID]
    return widget["config"]["datasources"][0]["dataKeys"]


def has_data_key(data: dict, name: str, key_type: str) -> bool:
    return any(
        data_key.get("name") == name and data_key.get("type") == key_type
        for data_key in data_keys(data)
    )


def has_data_key_label(data: dict, name: str, label: str) -> bool:
    return any(
        data_key.get("name") == name and data_key.get("label") == label
        for data_key in data_keys(data)
    )


def relation_type(data: dict) -> str:
    alias = data["configuration"]["entityAliases"][DEFAULT_RELATION_ALIAS_ID]
    return alias["filter"]["filters"][0]["relationType"]


class ApplyGatewayFixTest(unittest.TestCase):

    def test_attribute_mode(self) -> None:
        data = dashboard_fixture()

        report = apply_gateway_fix(data, DEFAULT_WIDGET_ID, "attribute")

        self.assertEqual(
            {"relation-type", "status-label", "version-label",
             "status", "name", "type"},
            set(report["changes"]),
        )
        self.assertEqual("Contains", relation_type(data))
        markdown = data["configuration"]["widgets"][DEFAULT_WIDGET_ID][
            "config"]["settings"]["markdownTextFunction"]
        self.assertIn(
            "(data[0].Status === true || String(data[0].Status) === 'true')",
            markdown,
        )
        self.assertIn("data[0].entityName", markdown)
        self.assertIn("data[0].Type", markdown)
        self.assertNotIn("data[0].active", markdown)
        self.assertNotIn("data[0].Name", markdown)
        self.assertTrue(has_data_key_label(data, "active", "Status"))
        self.assertTrue(has_data_key_label(data, "Version", "Version"))
        self.assertTrue(has_data_key(data, "Type", "attribute"))
        self.assertFalse(has_data_key(data, "type", "entityField"))

    def test_relation_type_already_contains(self) -> None:
        data = dashboard_fixture()
        data["configuration"]["entityAliases"][DEFAULT_RELATION_ALIAS_ID][
            "filter"]["filters"][0]["relationType"] = "Contains"

        report = apply_gateway_fix(data, DEFAULT_WIDGET_ID, "attribute")

        self.assertNotIn("relation-type", report["changes"])
        self.assertEqual("Contains", relation_type(data))

    def test_relation_type_created_is_migrated(self) -> None:
        data = dashboard_fixture()
        data["configuration"]["entityAliases"][DEFAULT_RELATION_ALIAS_ID][
            "filter"]["filters"][0]["relationType"] = "Created"

        report = apply_gateway_fix(data, DEFAULT_WIDGET_ID, "attribute")

        self.assertIn("relation-type", report["changes"])
        self.assertEqual("Contains", relation_type(data))

    def test_attribute_mode_is_idempotent(self) -> None:
        data = dashboard_fixture()
        apply_gateway_fix(data, DEFAULT_WIDGET_ID, "attribute")

        report = apply_gateway_fix(data, DEFAULT_WIDGET_ID, "attribute")

        self.assertEqual([], report["changes"])

    def test_intermediate_state_is_migrated(self) -> None:
        data = dashboard_fixture()
        widget = data["configuration"]["widgets"][DEFAULT_WIDGET_ID]
        widget["config"]["settings"]["markdownTextFunction"] = (
            "const isActive =\n"
            "  (data[0].active === true || String(data[0].active) === 'true') &&\n"
            "  (!lastDisconnectTime || lastConnectTime > lastDisconnectTime);\n"
            "createDataBlock(data[0].name, 'name');\n"
            "createDataBlock(data[0].Type, 'type');\n"
        )

        report = apply_gateway_fix(data, DEFAULT_WIDGET_ID, "attribute")

        self.assertIn("status", report["changes"])
        self.assertIn("name", report["changes"])
        markdown = widget["config"]["settings"]["markdownTextFunction"]
        self.assertIn(
            "(data[0].Status === true || String(data[0].Status) === 'true')",
            markdown,
        )
        self.assertIn("data[0].entityName", markdown)
        self.assertNotIn("data[0].active", markdown)
        self.assertNotIn("data[0].name", markdown)

    def test_entity_mode(self) -> None:
        data = dashboard_fixture()

        report = apply_gateway_fix(data, DEFAULT_WIDGET_ID, "entity")

        self.assertIn("type", report["changes"])
        markdown = data["configuration"]["widgets"][DEFAULT_WIDGET_ID][
            "config"]["settings"]["markdownTextFunction"]
        self.assertIn("data[0].type", markdown)
        self.assertNotIn("data[0].Type", markdown)
        self.assertTrue(has_data_key(data, "type", "entityField"))

    def test_entity_mode_reverts_attribute_key(self) -> None:
        data = dashboard_fixture()
        apply_gateway_fix(data, DEFAULT_WIDGET_ID, "attribute")

        report = apply_gateway_fix(data, DEFAULT_WIDGET_ID, "entity")

        self.assertIn("type", report["changes"])
        self.assertTrue(has_data_key(data, "type", "entityField"))

    def test_none_mode_keeps_type_key(self) -> None:
        data = dashboard_fixture()

        report = apply_gateway_fix(data, DEFAULT_WIDGET_ID, "none")

        self.assertNotIn("type", report["changes"])
        self.assertTrue(has_data_key(data, "type", "entityField"))

    def test_missing_widget(self) -> None:
        with self.assertRaises(DashboardFixError):
            apply_gateway_fix(dashboard_fixture(), "missing", "attribute")

    def test_unsupported_markdown(self) -> None:
        data = dashboard_fixture()
        data["configuration"]["widgets"][DEFAULT_WIDGET_ID][
            "config"]["settings"]["markdownTextFunction"] = "return 1;"

        with self.assertRaises(DashboardFixError):
            apply_gateway_fix(data, DEFAULT_WIDGET_ID, "attribute")


class JsonHelpersTest(unittest.TestCase):

    def test_dump_and_load(self) -> None:
        data = dashboard_fixture()

        content = dump_json(data)
        loaded = load_json(content, "test")

        self.assertEqual(data, loaded)

    def test_save_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = save_backup(tmp, "gateways_dashboard.json", b"{}")

            self.assertTrue(path.is_file())
            self.assertEqual(b"{}", path.read_bytes())


class FakeResponse:

    def __init__(
            self,
            status_code: int,
            payload: dict,
            content: bytes = b"",
            headers: dict | None = None,
            url: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.content = content
        self.headers = headers or {}
        self.url = url
        self.text = json.dumps(payload)

    def json(self) -> dict:
        return self._payload


class FakeSession:

    def __init__(self) -> None:
        self.calls = []
        self.trust_env = True
        self.verify = True

    def post(self, url, json=None, timeout=None):
        self.calls.append(("POST", url, json))
        return FakeResponse(200, {"token": "token-value"}, url=url)

    def get(self, url, headers=None, timeout=None):
        self.calls.append(("GET", url, headers))
        if url.endswith("/info"):
            return FakeResponse(200, {
                "id": {"id": "resource-id"},
                "fileName": "gateways_dashboard.json",
                "etag": "old-etag",
            }, url=url)
        return FakeResponse(
            200, {}, content=b'{"configuration":{}}',
            headers={"ETag": "old-etag"}, url=url)

    def put(self, url, headers=None, files=None, timeout=None):
        self.calls.append(("PUT", url, headers, files))
        return FakeResponse(200, {"etag": "new-etag"}, url=url)


class TbClientTest(unittest.TestCase):

    def test_calls(self) -> None:
        session = FakeSession()
        client = TbClient("http://127.0.0.1:1", 1, session=session)

        token = client.login("sysadmin@thingsboard.org", "sysadmin")
        info = client.get_resource_info(
            token, "dashboard", "system", "gateways_dashboard.json")
        content, etag = client.get_resource_data(
            token, "dashboard", "system", "gateways_dashboard.json")
        result = client.put_resource_data(
            token, "resource-id", "gateways_dashboard.json", b"{}")

        self.assertEqual("token-value", token)
        self.assertEqual("resource-id", info["id"]["id"])
        self.assertEqual(b'{"configuration":{}}', content)
        self.assertEqual("old-etag", etag)
        self.assertEqual("new-etag", result["etag"])
        put_call = session.calls[-1]
        self.assertEqual(
            "http://127.0.0.1:1/api/resource/resource-id/data", put_call[1])
        self.assertEqual(
            "gateways_dashboard.json", put_call[3]["file"][0])


if __name__ == "__main__":
    unittest.main()
