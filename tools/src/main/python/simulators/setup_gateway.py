#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from simulate_telemetry import ApiError, ThingsBoardClient, find_tsl_schema

CSV_FIELDS = [
    "product_id",
    "device_name",
    "device_id",
    "access_token",
    "tsl_version",
    "profile_id",
    "profile_name",
    "site_code",
    "relation_type",
    "relation_status",
    "status",
    "error",
    "created_at",
]

DEFAULT_RELATION_TYPE = "Contains"
DEFAULT_PRODUCTS_DIR = Path(__file__).resolve().parents[5] / "thing-model" / "migrate" / "integrated"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a ThingsBoard gateway and sub-devices for thing-model products.")
    parser.add_argument(
        "--tb-url",
        default=os.getenv("TB_URL", "http://localhost:18080"),
        help="ThingsBoard base URL",
    )
    parser.add_argument(
        "--thingmodel-url",
        default=os.getenv("THINGMODEL_URL", "http://localhost:8090"),
        help="thing-model base URL",
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
        "--gateway-name",
        default="gateway-01",
        help="gateway device name",
    )
    parser.add_argument(
        "--products-dir",
        default=str(DEFAULT_PRODUCTS_DIR),
        help="directory with Tencent thing model JSON files",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="sub-devices per product",
    )
    parser.add_argument(
        "--site-code",
        default=os.getenv("SITE_CODE", "SIM"),
        help="site_code server attribute",
    )
    parser.add_argument(
        "--relation-type",
        default=DEFAULT_RELATION_TYPE,
        help="relation type from gateway to sub-device",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="directory for gateway and sub-device CSV files",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print planned operations without creating entities",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_products(products_dir: Path) -> List[Dict[str, Any]]:
    if not products_dir.is_dir():
        raise ApiError(f"products directory not found: {products_dir}")
    products: List[Dict[str, Any]] = []
    for path in sorted(products_dir.glob("*.json")):
        try:
            data = json.loads(path.read_bytes().decode("utf-8-sig"))
        except UnicodeDecodeError as exc:
            raise ApiError(f"thing model is not valid UTF-8: {path.name}: {exc}")
        except json.JSONDecodeError as exc:
            raise ApiError(f"thing model is not valid JSON: {path.name}: {exc}")
        profile = data.get("profile") or {}
        product_id = str(profile.get("ProductId") or profile.get("productId") or "").strip()
        if not product_id:
            raise ApiError(f"thing model has no ProductId: {path.name}")
        products.append({"file": path, "product_id": product_id})
    if not products:
        raise ApiError(f"no thing models found in {products_dir}")
    ids = [product["product_id"] for product in products]
    if len(set(ids)) != len(ids):
        raise ApiError("duplicate ProductId found in product directory")
    return products


def load_product_context(
        client: ThingsBoardClient,
        token: str,
        product_id: str) -> Dict[str, Any]:
    product = client.get_product(token, product_id)
    info = product.get("product") or {}
    profile_id = info.get("tbProfileId")
    asset_id = info.get("tbAssetId")
    tenant_id = info.get("tenantId")
    if not profile_id or not asset_id or not tenant_id:
        raise ApiError(
            f"product {product_id} is not synced: missing tbProfileId/tbAssetId/tenantId; "
            "run product sync first")
    tsl_version = info.get("tslVersion") or "1.0"
    tsl_schema = find_tsl_schema(client.get_asset_attributes(token, asset_id))
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


def ensure_gateway(
        client: ThingsBoardClient,
        token: str,
        name: str,
        dry_run: bool) -> Tuple[Dict[str, Any], str]:
    existing = client.find_device_by_name(token, name)
    if existing:
        device_id = (existing.get("id") or {}).get("id", "")
        if not device_id:
            raise ApiError(f"gateway {name} has no id")
        additional_info = existing.get("additionalInfo")
        if not isinstance(additional_info, dict):
            additional_info = {}
        if not additional_info.get("gateway"):
            additional_info["gateway"] = True
            existing["additionalInfo"] = additional_info
            if not dry_run:
                response = client.session.post(
                    f"{client.tb_url}/api/device",
                    headers=client._auth_headers(token),
                    json=existing,
                    timeout=client.timeout,
                )
                client._check(response)
                existing = response.json()
        return existing, "exists"
    if dry_run:
        return {"id": {"id": "<new>"}, "name": name}, "dry-run"
    response = client.session.post(
        f"{client.tb_url}/api/device",
        headers=client._auth_headers(token),
        json={"name": name, "additionalInfo": {"gateway": True}},
        timeout=client.timeout,
    )
    client._check(response)
    return response.json(), "created"


def ensure_device(
        client: ThingsBoardClient,
        token: str,
        profile_id: str,
        name: str,
        attributes: Dict[str, Any],
        dry_run: bool) -> Tuple[str, str, str]:
    existing = client.find_device_by_name(token, name)
    if existing:
        device_id = (existing.get("id") or {}).get("id", "")
        if not device_id:
            raise ApiError(f"device {name} has no id")
        if not dry_run:
            client.set_server_attributes(
                token, device_id, {**attributes, "device_uuid": device_id})
        access_token = ""
        if not dry_run:
            credentials = client.get_credentials(token, device_id)
            access_token = credentials.get("credentialsId", "")
        return device_id, access_token, "exists"
    if dry_run:
        return "<new>", "", "dry-run"
    device = client.create_device(token, profile_id, name)
    device_id = (device.get("id") or {}).get("id")
    if not device_id:
        raise ApiError(f"ThingsBoard did not return a device id for {name}")
    client.set_server_attributes(
        token, device_id, {**attributes, "device_uuid": device_id})
    credentials = client.get_credentials(token, device_id)
    access_token = credentials.get("credentialsId")
    if not access_token:
        raise ApiError(f"ThingsBoard did not return an access token for {name}")
    return device_id, access_token, "created"


def relation_exists(
        client: ThingsBoardClient,
        token: str,
        from_id: str,
        to_id: str,
        relation_type: str) -> bool:
    response = client.session.get(
        f"{client.tb_url}/api/relation",
        params={
            "fromId": from_id,
            "fromType": "DEVICE",
            "relationType": relation_type,
            "toId": to_id,
            "toType": "DEVICE",
        },
        headers=client._auth_headers(token),
        timeout=client.timeout,
    )
    if response.status_code == 404:
        return False
    client._check(response)
    return True


def ensure_relation(
        client: ThingsBoardClient,
        token: str,
        from_id: str,
        to_id: str,
        relation_type: str,
        dry_run: bool) -> str:
    if relation_exists(client, token, from_id, to_id, relation_type):
        return "exists"
    if dry_run:
        return "dry-run"
    response = client.session.post(
        f"{client.tb_url}/api/relation",
        headers=client._auth_headers(token),
        json={
            "from": {"entityType": "DEVICE", "id": from_id},
            "to": {"entityType": "DEVICE", "id": to_id},
            "type": relation_type,
            "typeGroup": "COMMON",
        },
        timeout=client.timeout,
    )
    client._check(response)
    return "created"


def resolve_output_path(output_dir: str, name: str) -> Path:
    path = Path(output_dir) / name
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        path = path.with_name(f"{path.stem}-{stamp}{path.suffix}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_rows(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    if args.count <= 0:
        print("error: --count must be greater than 0", file=sys.stderr)
        return 1

    password = args.password
    if not password:
        password = getpass.getpass(f"ThingsBoard password for {args.username}: ")

    try:
        products = load_products(Path(args.products_dir))
    except ApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    client = ThingsBoardClient(args.tb_url, args.thingmodel_url, args.timeout)
    try:
        token = client.login(args.username, password)
    except Exception as exc:
        print(f"error: ThingsBoard login failed: {exc}", file=sys.stderr)
        return 1

    contexts: List[Dict[str, Any]] = []
    missing = []
    for product in products:
        try:
            contexts.append(load_product_context(client, token, product["product_id"]))
        except Exception as exc:
            missing.append(f"{product['product_id']}: {exc}")
    if missing:
        print("error: products are not ready; nothing was created", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        return 1

    gateway_rows: List[Dict[str, Any]] = []
    sub_device_rows: List[Dict[str, Any]] = []
    failures = 0

    try:
        gateway_device, gateway_status = ensure_gateway(
            client, token, args.gateway_name, args.dry_run)
        gateway_id = (gateway_device.get("id") or {}).get("id")
        if not gateway_id:
            raise ApiError("gateway device id is missing")
        gateway_token = ""
        if not args.dry_run:
            gateway_credentials = client.get_credentials(token, gateway_id)
            gateway_token = gateway_credentials.get("credentialsId", "")
        gateway_profile_id = (gateway_device.get("deviceProfileId") or {}).get("id", "")
        gateway_rows.append({
            "product_id": "",
            "device_name": gateway_device.get("name", args.gateway_name),
            "device_id": gateway_id,
            "access_token": gateway_token,
            "tsl_version": "",
            "profile_id": gateway_profile_id,
            "profile_name": "",
            "site_code": args.site_code,
            "relation_type": args.relation_type,
            "relation_status": "",
            "status": gateway_status,
            "error": "",
            "created_at": now_iso(),
        })
        print(f"gateway {args.gateway_name}: {gateway_status} ({gateway_id})")

        for context in contexts:
            product_id = context["product_id"]
            attributes = {
                "tsl_schema": context["tsl_schema"],
                "tsl_version": context["tsl_version"],
                "tenant_id": context["tenant_id"],
                "site_code": args.site_code,
                "product_id": product_id,
            }
            for index in range(1, args.count + 1):
                device_name = f"{product_id}-{index:02d}"
                device_id = ""
                access_token = ""
                status = ""
                error = ""
                relation_status = ""
                try:
                    device_id, access_token, status = ensure_device(
                        client,
                        token,
                        context["profile_id"],
                        device_name,
                        attributes,
                        args.dry_run,
                    )
                    if gateway_id and gateway_id != "<new>" and device_id and device_id != "<new>":
                        relation_status = ensure_relation(
                            client,
                            token,
                            gateway_id,
                            device_id,
                            args.relation_type,
                            args.dry_run,
                        )
                    elif args.dry_run:
                        relation_status = "dry-run"
                except Exception as exc:
                    status = status or "failed"
                    error = str(exc)
                    failures += 1
                sub_device_rows.append({
                    "product_id": product_id,
                    "device_name": device_name,
                    "device_id": device_id,
                    "access_token": access_token,
                    "tsl_version": context["tsl_version"],
                    "profile_id": context["profile_id"],
                    "profile_name": context["profile_name"],
                    "site_code": args.site_code,
                    "relation_type": args.relation_type,
                    "relation_status": relation_status,
                    "status": status if not error else "failed",
                    "error": error,
                    "created_at": now_iso(),
                })
                relation_label = relation_status or "-"
                outcome = "failed" if error else status
                print(f"{device_name}: device={outcome}, relation={relation_label}"
                      + (f", error={error}" if error else ""))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    gateway_csv = resolve_output_path(args.output_dir, "gateway-credentials.csv")
    sub_devices_csv = resolve_output_path(args.output_dir, "sub-devices.csv")
    write_rows(gateway_csv, gateway_rows)
    write_rows(sub_devices_csv, sub_device_rows)

    created = sum(1 for row in sub_device_rows if row["status"] == "created")
    existing = sum(1 for row in sub_device_rows if row["status"] == "exists")
    print(
        f"summary gateways={len(gateway_rows)} sub_devices={len(sub_device_rows)} "
        f"created={created} existing={existing} failed={failures}")
    print(f"gateway CSV: {gateway_csv}")
    print(f"sub-device CSV: {sub_devices_csv}")
    print("warning: the CSV files contain Access Tokens; keep them secure", file=sys.stderr)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
