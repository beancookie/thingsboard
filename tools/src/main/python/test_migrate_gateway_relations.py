#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from migrate_gateway_relations import (
    find_gateways,
    migrate_gateway,
    relation_target_ids,
)


def relation(target_id: str) -> dict:
    return {
        "from": {"entityType": "DEVICE", "id": "gateway-id"},
        "to": {"entityType": "DEVICE", "id": target_id},
    }


class FakeClient:

    def __init__(self, old_relations, new_relations, old_type="创建d") -> None:
        self.old_relations = old_relations
        self.new_relations = new_relations
        self.old_type = old_type
        self.saved = []
        self.deleted = []

    def get_relations(self, token, from_id, relation_type):
        if relation_type == self.old_type:
            return list(self.old_relations)
        return list(self.new_relations)

    def save_relation(self, token, from_id, to_id, relation_type):
        self.saved.append((from_id, to_id, relation_type))

    def delete_relation(self, token, from_id, to_id, relation_type):
        self.deleted.append((from_id, to_id, relation_type))


class FindGatewaysTest(unittest.TestCase):

    def test_filters_gateway_devices(self) -> None:
        devices = [
            {"name": "gw", "additionalInfo": {"gateway": True}},
            {"name": "device", "additionalInfo": {"gateway": False}},
            {"name": "plain", "additionalInfo": {}},
        ]

        self.assertEqual(1, len(find_gateways(devices)))

    def test_relation_target_ids(self) -> None:
        relations = [relation("a"), relation("b")]

        self.assertEqual({"a", "b"}, relation_target_ids(relations))


class MigrateGatewayTest(unittest.TestCase):

    def test_creates_missing_and_deletes_old(self) -> None:
        client = FakeClient(
            [relation("a"), relation("b")],
            [],
        )

        result = migrate_gateway(
            client, "token", {"id": {"id": "gateway-id"}, "name": "gw"},
            "创建d", "Contains", True, False, False)

        self.assertEqual(2, result["created"])
        self.assertEqual(2, result["deleted"])
        self.assertEqual(
            [("gateway-id", "a", "Contains"), ("gateway-id", "b", "Contains")],
            client.saved,
        )

    def test_skips_existing_new_relation(self) -> None:
        client = FakeClient(
            [relation("a"), relation("b")],
            [relation("a")],
        )

        result = migrate_gateway(
            client, "token", {"id": {"id": "gateway-id"}, "name": "gw"},
            "创建d", "Contains", False, False, False)

        self.assertEqual(1, result["created"])
        self.assertEqual(1, result["skipped"])
        self.assertEqual([("gateway-id", "b", "Contains")], client.saved)
        self.assertEqual([], client.deleted)

    def test_dry_run_does_not_change(self) -> None:
        client = FakeClient([relation("a")], [])

        result = migrate_gateway(
            client, "token", {"id": {"id": "gateway-id"}, "name": "gw"},
            "创建d", "Contains", True, True, False)

        self.assertEqual(1, result["created"])
        self.assertEqual(1, result["deleted"])
        self.assertEqual([], client.saved)
        self.assertEqual([], client.deleted)

    def test_created_to_contains(self) -> None:
        client = FakeClient(
            [relation("a")],
            [],
            old_type="Created",
        )

        result = migrate_gateway(
            client, "token", {"id": {"id": "gateway-id"}, "name": "gw"},
            "Created", "Contains", True, False, False)

        self.assertEqual(1, result["created"])
        self.assertEqual(1, result["deleted"])
        self.assertEqual([("gateway-id", "a", "Contains")], client.saved)
        self.assertEqual([("gateway-id", "a", "Created")], client.deleted)


if __name__ == "__main__":
    unittest.main()
