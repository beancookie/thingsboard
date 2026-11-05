#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import os
import sys
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

import requests

DEFAULT_TB_URL = "http://localhost:18080"
DEFAULT_USERNAME = "tenant@thingsboard.org"
DEFAULT_OLD_TYPE = "创建d"
DEFAULT_NEW_TYPE = "Contains"


class RelationMigrationError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate gateway sub-device relations to a new relation type.")
    parser.add_argument(
        "--tb-url",
        default=None,
        help="ThingsBoard base URL; defaults to TB_URL or http://localhost:18080",
    )
    parser.add_argument(
        "--username",
        default=None,
        help="TENANT_ADMIN username; defaults to TB_USERNAME or tenant@thingsboard.org",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="TENANT_ADMIN password; defaults to TB_PASSWORD or prompt",
    )
    parser.add_argument(
        "--old-type",
        default=DEFAULT_OLD_TYPE,
        help="relation type to migrate from",
    )
    parser.add_argument(
        "--new-type",
        default=DEFAULT_NEW_TYPE,
        help="relation type to migrate to",
    )
    parser.add_argument(
        "--delete-old",
        action="store_true",
        help="delete the old relations after the new relations are created",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each migrated relation",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply the migration; without this flag the script only prints a dry run",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicitly request a dry run (the default)",
    )
    return parser.parse_args()


class TbClient:

    def __init__(
            self,
            base_url: str,
            timeout: float,
            verify: bool = True,
            session: Optional[requests.Session] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        parsed = urlparse(self.base_url)
        if parsed.hostname in ("localhost", "127.0.0.1", "::1"):
            self.session.trust_env = False
        if not verify:
            self.session.verify = False

    def _headers(self, token: str) -> Dict[str, str]:
        return {"X-Authorization": f"Bearer {token}"}

    def _check(self, response: requests.Response, action: str) -> None:
        if response.status_code >= 400:
            body = response.text
            if len(body) > 700:
                body = body[:700] + "..."
            raise RelationMigrationError(
                f"{action} failed: HTTP {response.status_code} "
                f"{response.url}: {body}")

    def login(self, username: str, password: str) -> str:
        response = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password},
            timeout=self.timeout,
        )
        self._check(response, "login")
        token = response.json().get("token")
        if not token:
            raise RelationMigrationError("login response did not contain a token")
        return token

    def get_devices(self, token: str) -> List[Dict[str, Any]]:
        devices: List[Dict[str, Any]] = []
        page = 0
        while True:
            response = self.session.get(
                f"{self.base_url}/api/tenant/devices",
                headers=self._headers(token),
                params={"pageSize": 100, "page": page},
                timeout=self.timeout,
            )
            self._check(response, "device list")
            payload = response.json()
            devices.extend(payload.get("data") or [])
            if not payload.get("hasNext"):
                break
            page += 1
        return devices

    def get_relations(
            self,
            token: str,
            from_id: str,
            relation_type: str) -> List[Dict[str, Any]]:
        response = self.session.get(
            f"{self.base_url}/api/relations",
            headers=self._headers(token),
            params={
                "fromId": from_id,
                "fromType": "DEVICE",
                "relationType": relation_type,
            },
            timeout=self.timeout,
        )
        self._check(response, "relation list")
        return response.json()

    def save_relation(
            self,
            token: str,
            from_id: str,
            to_id: str,
            relation_type: str) -> None:
        response = self.session.post(
            f"{self.base_url}/api/relation",
            headers=self._headers(token),
            json={
                "from": {"entityType": "DEVICE", "id": from_id},
                "to": {"entityType": "DEVICE", "id": to_id},
                "type": relation_type,
                "typeGroup": "COMMON",
            },
            timeout=self.timeout,
        )
        self._check(response, "relation create")

    def delete_relation(
            self,
            token: str,
            from_id: str,
            to_id: str,
            relation_type: str) -> None:
        response = self.session.delete(
            f"{self.base_url}/api/relation",
            headers=self._headers(token),
            params={
                "fromId": from_id,
                "fromType": "DEVICE",
                "relationType": relation_type,
                "toId": to_id,
                "toType": "DEVICE",
            },
            timeout=self.timeout,
        )
        self._check(response, "relation delete")


def find_gateways(devices: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        device for device in devices
        if isinstance(device.get("additionalInfo"), dict)
        and device["additionalInfo"].get("gateway") is True
    ]


def relation_target_ids(relations: Iterable[Dict[str, Any]]) -> set:
    result = set()
    for relation in relations:
        to = relation.get("to") or {}
        if to.get("entityType") == "DEVICE" and to.get("id"):
            result.add(to["id"])
    return result


def migrate_gateway(
        client: TbClient,
        token: str,
        gateway: Dict[str, Any],
        old_type: str,
        new_type: str,
        delete_old: bool,
        dry_run: bool,
        verbose: bool) -> Dict[str, int]:
    gateway_id = gateway.get("id", {}).get("id")
    gateway_name = gateway.get("name", "")
    if not gateway_id:
        raise RelationMigrationError(
            f"gateway {gateway_name} has no id")

    old_relations = client.get_relations(token, gateway_id, old_type)
    new_relations = client.get_relations(token, gateway_id, new_type)
    new_targets = relation_target_ids(new_relations)

    to_create = []
    for relation in old_relations:
        to = relation.get("to") or {}
        target_id = to.get("id")
        if to.get("entityType") != "DEVICE" or not target_id:
            continue
        if target_id not in new_targets:
            to_create.append(target_id)

    result = {
        "old": len(old_relations),
        "new": len(new_relations),
        "created": 0,
        "deleted": 0,
        "skipped": len(old_relations) - len(to_create),
    }

    for target_id in to_create:
        if verbose or dry_run:
            print(
                f"[{'dry-run' if dry_run else 'migrate'}] "
                f"gateway={gateway_name} {old_type} -> {new_type} "
                f"to={target_id}")
        if not dry_run:
            client.save_relation(token, gateway_id, target_id, new_type)
            result["created"] += 1
    if dry_run:
        result["created"] = len(to_create)

    if delete_old and old_relations:
        for relation in old_relations:
            to = relation.get("to") or {}
            target_id = to.get("id")
            if to.get("entityType") != "DEVICE" or not target_id:
                continue
            if verbose or dry_run:
                print(
                    f"[{'dry-run' if dry_run else 'migrate'}] "
                    f"delete gateway={gateway_name} {old_type} "
                    f"to={target_id}")
            if not dry_run:
                client.delete_relation(token, gateway_id, target_id, old_type)
                result["deleted"] += 1
        if dry_run:
            result["deleted"] = len(old_relations)

    return result


def main() -> int:
    args = parse_args()
    tb_url = args.tb_url or os.environ.get("TB_URL", DEFAULT_TB_URL)
    username = args.username or os.environ.get("TB_USERNAME", DEFAULT_USERNAME)
    password = args.password or os.environ.get("TB_PASSWORD")
    if not password:
        password = getpass.getpass(
            f"ThingsBoard password for {username}: ")

    client = TbClient(tb_url, args.timeout, verify=not args.insecure)
    try:
        token = client.login(username, password)
        gateways = find_gateways(client.get_devices(token))
        if not gateways:
            print("no gateway devices found")
            return 0

        totals = {"old": 0, "new": 0, "created": 0, "deleted": 0, "skipped": 0}
        print(
            f"gateways={len(gateways)} oldType={args.old_type} "
            f"newType={args.new_type} apply={args.apply} "
            f"deleteOld={args.delete_old}")
        for gateway in gateways:
            result = migrate_gateway(
                client,
                token,
                gateway,
                args.old_type,
                args.new_type,
                args.delete_old,
                not args.apply,
                args.verbose,
            )
            for key in totals:
                totals[key] += result[key]
            print(
                f"gateway={gateway.get('name')} old={result['old']} "
                f"new={result['new']} created={result['created']} "
                f"skipped={result['skipped']} deleted={result['deleted']}")

        print(
            f"summary old={totals['old']} new={totals['new']} "
            f"created={totals['created']} skipped={totals['skipped']} "
            f"deleted={totals['deleted']}")
        if not args.apply:
            print("dry run: no relations were changed; use --apply to migrate")
        return 0
    except RelationMigrationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
