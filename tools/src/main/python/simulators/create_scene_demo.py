#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import getpass
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from import_products import ProductImportClient
from setup_gateway import ensure_relation
from simulate_telemetry import ApiError, find_tsl_schema

CSV_FIELDS = [
    "product_id",
    "device_name",
    "device_id",
    "access_token",
    "scene_role",
    "site_code",
    "profile_id",
    "profile_name",
    "tsl_version",
    "status",
    "error",
    "created_at",
]

SCENE_DEVICES: List[Dict[str, str]] = [
    {
        "product_id": "SCENE_MOTION",
        "device_name": "motion-01",
        "scene_role": "trigger",
    },
    {
        "product_id": "SCENE_LIGHT_SENSOR",
        "device_name": "light-sensor-01",
        "scene_role": "sensor",
    },
    {
        "product_id": "SCENE_LIGHT",
        "device_name": "light-01",
        "scene_role": "actuator",
    },
    {
        "product_id": "SCENE_TEMPERATURE",
        "device_name": "temperature-01",
        "scene_role": "trigger",
    },
    {
        "product_id": "SCENE_AIR_CONDITIONER",
        "device_name": "air-conditioner-01",
        "scene_role": "actuator",
    },
]

SCENE_RELATIONS: List[Tuple[str, str, str]] = [
    ("motion-01", "light-01", "Controls"),
    ("motion-01", "light-sensor-01", "ConnectedTo"),
    ("temperature-01", "air-conditioner-01", "Controls"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create demo devices and relations for the multi-device scene manual.")
    parser.add_argument(
        "--tb-url",
        default=os.getenv("TB_URL", "http://localhost:18080"),
        help="ThingsBoard base URL",
    )
    parser.add_argument(
        "--thingmodel-url",
        default=os.getenv("THINGMODEL_URL", "http://localhost:8090"),
        help="thing-model base URL; for a gateway proxy use <host>/api/thing-model",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("TB_USERNAME", "tenant@thingsboard.org"),
        help="ThingsBoard tenant admin username",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("TB_PASSWORD"),
        help="ThingsBoard password; defaults to TB_PASSWORD or prompt",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("TB_API_KEY"),
        help="ThingsBoard API key; defaults to TB_API_KEY; takes precedence over password",
    )
    parser.add_argument(
        "--output-dir",
        default="import-output/scene-demo",
        help="directory for scene-devices.csv",
    )
    parser.add_argument(
        "--site-code",
        default="SCENE_DEMO",
        help="site_code server attribute",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print planned devices and relations without creating them",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def authenticate(client: ProductImportClient, args: argparse.Namespace) -> str:
    if args.api_key:
        try:
            return client.exchange_api_key_for_token(args.api_key)
        except Exception as exc:
            print(
                "warning: API key to JWT exchange failed; using API key "
                f"directly: {exc}", file=sys.stderr)
            return client.api_key_token(args.api_key)
    password = args.password
    if not password:
        password = getpass.getpass(
            f"ThingsBoard password for {args.username}: ")
    return client.login(args.username, password)


def load_product_context(
        client: ProductImportClient,
        token: str,
        product_id: str) -> Dict[str, Any]:
    product = client.find_product(token, product_id)
    if product is None:
        raise ApiError(f"product not found: {product_id}")
    info = product.get("product") or {}
    profile_id = info.get("tbProfileId")
    asset_id = info.get("tbAssetId")
    tenant_id = info.get("tenantId")
    if not profile_id or not asset_id or not tenant_id:
        raise ApiError(
            f"product {product_id} is not synced: missing "
            "tbProfileId/tbAssetId/tenantId")
    tsl_version = info.get("tslVersion") or "1.0"
    tsl_schema = find_tsl_schema(
        client.get_asset_attributes(token, asset_id))
    profile_name = ""
    try:
        response = client.session.get(
            f"{client.tb_url}/api/deviceProfile/{profile_id}",
            headers=client._auth_headers(token),
            timeout=client.timeout,
        )
        if response.ok:
            profile_name = response.json().get("name") or ""
    except Exception:
        profile_name = ""
    return {
        "product_id": product_id,
        "profile_id": profile_id,
        "profile_name": profile_name,
        "tenant_id": tenant_id,
        "tsl_version": tsl_version,
        "tsl_schema": tsl_schema,
    }


def ensure_device(
        client: ProductImportClient,
        token: str,
        spec: Dict[str, str],
        context: Dict[str, Any],
        site_code: str,
        dry_run: bool) -> Tuple[str, str, str]:
    device_name = spec["device_name"]
    existing = client.find_device_by_name(token, device_name)
    if existing:
        device_id = (existing.get("id") or {}).get("id", "")
        if not device_id:
            raise ApiError(f"device {device_name} has no id")
        status = "exists"
    elif dry_run:
        return "<new>", "", "dry-run"
    else:
        device = client.create_device(
            token, context["profile_id"], device_name)
        device_id = (device.get("id") or {}).get("id", "")
        if not device_id:
            raise ApiError(f"ThingsBoard did not return a device id for {device_name}")
        status = "created"

    if not dry_run:
        client.set_server_attributes(token, device_id, {
            "product_id": spec["product_id"],
            "scene_role": spec["scene_role"],
            "site_code": site_code,
            "tenant_id": context["tenant_id"],
            "device_uuid": device_id,
            "tsl_version": context["tsl_version"],
            "tsl_schema": context["tsl_schema"],
        })
        credentials = client.get_credentials(token, device_id)
        access_token = credentials.get("credentialsId", "")
        if not access_token:
            raise ApiError(f"ThingsBoard did not return an access token for {device_name}")
    else:
        access_token = ""
    return device_id, access_token, status


def base_row(spec: Dict[str, str], context: Dict[str, Any],
             site_code: str) -> Dict[str, Any]:
    return {
        "product_id": spec["product_id"],
        "device_name": spec["device_name"],
        "device_id": "",
        "access_token": "",
        "scene_role": spec["scene_role"],
        "site_code": site_code,
        "profile_id": context["profile_id"],
        "profile_name": context["profile_name"],
        "tsl_version": context["tsl_version"],
        "status": "",
        "error": "",
        "created_at": now_iso(),
    }


def write_rows(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    client = ProductImportClient(args.tb_url, args.thingmodel_url, args.timeout)
    try:
        token = authenticate(client, args)
    except Exception as exc:
        print(f"error: ThingsBoard authentication failed: {exc}", file=sys.stderr)
        return 1

    contexts: Dict[str, Dict[str, Any]] = {}
    for product_id in sorted({spec["product_id"] for spec in SCENE_DEVICES}):
        try:
            contexts[product_id] = load_product_context(
                client, token, product_id)
        except Exception as exc:
            print(f"error: product {product_id}: {exc}", file=sys.stderr)
            return 1

    rows: List[Dict[str, Any]] = []
    device_ids: Dict[str, str] = {}
    failures = 0
    for spec in SCENE_DEVICES:
        context = contexts[spec["product_id"]]
        row = base_row(spec, context, args.site_code)
        try:
            device_id, access_token, status = ensure_device(
                client, token, spec, context, args.site_code, args.dry_run)
            row["device_id"] = device_id
            row["access_token"] = access_token
            row["status"] = status
            device_ids[spec["device_name"]] = device_id
            print(
                f"{spec['device_name']}: {status} "
                f"product={spec['product_id']} profile={context['profile_id']}")
        except Exception as exc:
            row["status"] = "failed"
            row["error"] = str(exc)
            failures += 1
            print(f"failed {spec['device_name']}: {exc}", file=sys.stderr)
        rows.append(row)

    relation_failures = 0
    for from_name, to_name, relation_type in SCENE_RELATIONS:
        from_id = device_ids.get(from_name)
        to_id = device_ids.get(to_name)
        if not from_id or not to_id:
            print(
                f"skip relation {from_name} -{relation_type}-> {to_name}: "
                "device missing", file=sys.stderr)
            relation_failures += 1
            continue
        if args.dry_run and ("<new>" in (from_id, to_id)):
            print(
                f"relation {from_name} -{relation_type}-> {to_name}: dry-run")
            continue
        try:
            status = ensure_relation(
                client, token, from_id, to_id, relation_type, args.dry_run)
            print(
                f"relation {from_name} -{relation_type}-> {to_name}: {status}")
        except Exception as exc:
            relation_failures += 1
            print(
                f"failed relation {from_name} -{relation_type}-> {to_name}: {exc}",
                file=sys.stderr)

    output_path = Path(args.output_dir) / "scene-devices.csv"
    write_rows(output_path, rows)
    print(
        f"summary devices={len(rows)} failed={failures} "
        f"relation_failures={relation_failures}")
    print(f"devices CSV: {output_path}")
    print("warning: the CSV contains Access Tokens; keep it secure", file=sys.stderr)
    return 0 if failures == 0 and relation_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
