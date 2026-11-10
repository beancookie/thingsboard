#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from simulate_telemetry import ApiError, ThingsBoardClient

CSV_FIELDS = [
    "product_id",
    "name",
    "model",
    "category_id",
    "tsl_version",
    "status",
    "property_count",
    "event_count",
    "action_count",
    "tb_profile_id",
    "tb_asset_id",
    "tb_rule_chain_id",
    "updated_at",
    "tsl_file",
    "error",
]

DEFAULT_TB_URL = "https://thingsboard.zhgcloud.com"
DEFAULT_THINGMODEL_URL = "https://thingsboard.zhgcloud.com/api/thing-model"
_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class ProductExportClient(ThingsBoardClient):

    def list_products(self, token: str) -> List[Dict[str, Any]]:
        response = self.session.get(
            self.product_api_base,
            headers=self._auth_headers(token),
            timeout=self.timeout,
        )
        self._check(response)
        return response.json() or []

    def get_product_detail(
            self, token: str, product_id: str) -> Dict[str, Any]:
        response = self.session.get(
            f"{self.product_api_base}/{quote(product_id, safe='')}",
            headers=self._auth_headers(token),
            timeout=self.timeout,
        )
        self._check(response)
        return response.json()

    def get_thing_model(
            self, token: str, product_id: str) -> Dict[str, Any]:
        response = self.session.get(
            f"{self.product_api_base}/"
            f"{quote(product_id, safe='')}/thing-model",
            headers=self._auth_headers(token),
            timeout=self.timeout,
        )
        self._check(response)
        return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export thing-model products and their TSL from a running platform.")
    parser.add_argument(
        "--tb-url",
        default=os.getenv("TB_URL", DEFAULT_TB_URL),
        help="ThingsBoard base URL",
    )
    parser.add_argument(
        "--thingmodel-url",
        default=os.getenv("THINGMODEL_URL", DEFAULT_THINGMODEL_URL),
        help="thing-model base URL; for a gateway proxy use <host>/api/thing-model",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("TB_API_KEY"),
        help="ThingsBoard API key; defaults to TB_API_KEY",
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
        "--product-id",
        action="append",
        default=[],
        help="product id to export; repeatable; default exports all products",
    )
    parser.add_argument(
        "--output-dir",
        default="product-export",
        help="directory for CSV, JSON and TSL files",
    )
    parser.add_argument(
        "--no-detail",
        action="store_true",
        help="skip fetching the per-product detail document",
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


def sanitize_filename(value: str, fallback: str = "product") -> str:
    name = _INVALID_FILENAME.sub("_", value.strip()).strip(" .")
    return name or fallback


def base_row(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "product_id": item.get("productId") or "",
        "name": item.get("name") or "",
        "model": item.get("model") or "",
        "category_id": item.get("categoryId") or "",
        "tsl_version": item.get("tslVersion") or "",
        "status": item.get("status") or "",
        "property_count": item.get("propertyCount"),
        "event_count": item.get("eventCount"),
        "action_count": item.get("actionCount"),
        "tb_profile_id": item.get("tbProfileId") or "",
        "tb_asset_id": item.get("tbAssetId") or "",
        "tb_rule_chain_id": item.get("tbRuleChainId") or "",
        "updated_at": item.get("updatedAt") or "",
        "tsl_file": "",
        "error": "",
    }


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def authenticate(client: ProductExportClient,
                 args: argparse.Namespace) -> str:
    if args.api_key:
        return client.exchange_api_key_for_token(args.api_key)
    password = args.password
    if not password:
        password = getpass.getpass(
            f"ThingsBoard password for {args.username}: ")
    return client.login(args.username, password)


def export_product(
        client: ProductExportClient,
        token: str,
        item: Dict[str, Any],
        tsl_dir: Path,
        include_detail: bool) -> Dict[str, Any]:
    row = base_row(item)
    product_id = row["product_id"]
    if not product_id:
        row["error"] = "product has no productId"
        return row

    try:
        thing_model = client.get_thing_model(token, product_id)
    except Exception as exc:
        row["error"] = str(exc)
        return row

    tsl = thing_model.get("tsl") if isinstance(thing_model, dict) else None
    if not isinstance(tsl, dict):
        tsl = thing_model
    tsl_name = f"{sanitize_filename(product_id)}.tsl.json"
    write_json(tsl_dir / tsl_name, tsl)
    row["tsl_file"] = f"tsl/{tsl_name}"

    if include_detail:
        try:
            row["_detail"] = client.get_product_detail(token, product_id)
        except Exception as exc:
            row["error"] = f"detail: {exc}"
    return row


def main() -> int:
    args = parse_args()
    client = ProductExportClient(args.tb_url, args.thingmodel_url, args.timeout)

    try:
        token = authenticate(client, args)
        products = client.list_products(token)
    except Exception as exc:
        print(f"error: ThingsBoard authentication or product list failed: {exc}",
              file=sys.stderr)
        if args.api_key and "HTTP 401" in str(exc):
            print(
                "hint: the target thing-model service rejected the API key; "
                "verify the key is valid or use --username/--password",
                file=sys.stderr)
        return 1

    wanted = [pid.strip() for pid in args.product_id if pid.strip()]
    if wanted:
        by_id = {item.get("productId"): item for item in products}
        selected = [item for item in products
                    if item.get("productId") in wanted]
        missing = [pid for pid in wanted if pid not in by_id]
    else:
        selected = products
        missing = []

    output_dir = Path(args.output_dir)
    tsl_dir = output_dir / "tsl"
    rows: List[Dict[str, Any]] = []
    exported: List[Dict[str, Any]] = []
    failures = 0

    for item in selected:
        row = export_product(
            client, token, item, tsl_dir, not args.no_detail)
        detail = row.pop("_detail", None)
        if row["error"]:
            failures += 1
            print(f"failed {row['product_id']}: {row['error']}",
                  file=sys.stderr)
        else:
            print(f"exported {row['product_id']} ({row['name']}) "
                  f"-> {row['tsl_file']}")
        rows.append(row)
        exported.append({
            "meta": item,
            "detail": detail,
            "tslFile": row["tsl_file"],
            "error": row["error"],
        })

    for pid in missing:
        failures += 1
        row = base_row({"productId": pid})
        row["error"] = "product not found"
        rows.append(row)
        exported.append({
            "meta": {},
            "detail": None,
            "tslFile": "",
            "error": row["error"],
        })
        print(f"failed {pid}: product not found", file=sys.stderr)

    write_csv(output_dir / "products.csv", rows)
    write_json(output_dir / "products.json", {
        "exportedAt": now_iso(),
        "tbUrl": client.tb_url,
        "thingmodelUrl": client.thingmodel_url,
        "count": len(exported),
        "products": exported,
    })

    print(
        f"summary products={len(rows)} exported={len(rows) - failures} "
        f"failed={failures} output={output_dir}")
    print(f"csv: {output_dir / 'products.csv'}")
    print(f"json: {output_dir / 'products.json'}")
    print(f"tsl: {tsl_dir}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
