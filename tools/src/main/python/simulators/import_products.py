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
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from simulate_telemetry import ApiError, ThingsBoardClient

CSV_FIELDS = [
    "file",
    "product_id",
    "name",
    "model",
    "category_id",
    "tsl_version",
    "status",
    "tb_profile_id",
    "tb_asset_id",
    "tb_rule_chain_id",
    "error",
    "created_at",
]

DEFAULT_PRODUCTS_DIR = (
    Path(__file__).resolve().parents[5]
    / "thing-model"
    / "migrate"
    / "integrated"
)


class ProductImportClient(ThingsBoardClient):

    def list_products(self, token: str) -> List[Dict[str, Any]]:
        response = self.session.get(
            self.product_api_base,
            headers=self._auth_headers(token),
            timeout=self.timeout,
        )
        self._check(response)
        return response.json()

    def find_product(
            self, token: str, product_id: str) -> Optional[Dict[str, Any]]:
        response = self.session.get(
            f"{self.product_api_base}/{quote(product_id, safe='')}",
            headers=self._auth_headers(token),
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return None
        self._check(response)
        return response.json()

    def validate_thing_model(
            self, token: str, product_id: str, tsl: Any) -> Dict[str, Any]:
        response = self.session.post(
            f"{self.product_api_base}/"
            f"{quote(product_id, safe='')}/thing-model/validate",
            headers=self._auth_headers(token),
            json={"tsl": tsl},
            timeout=self.timeout,
        )
        self._check(response)
        return response.json()

    def create_product(
            self, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = self.session.post(
            self.product_api_base,
            headers=self._auth_headers(token),
            json=payload,
            timeout=self.timeout,
        )
        self._check(response)
        return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import thing-model product TSL files into a running thing-model service.")
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
        "--products-dir",
        default=str(DEFAULT_PRODUCTS_DIR),
        help="directory with thing model JSON files",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="directory for the import report CSV",
    )
    parser.add_argument(
        "--strict-unknown",
        action="store_true",
        help="reject unknown telemetry fields at runtime",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="submit existing products again instead of skipping them",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="skip the pre-import TSL validation call",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse files and print the import plan without calling the API",
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


def load_product_files(products_dir: Path) -> List[Dict[str, Any]]:
    if not products_dir.is_dir():
        raise ApiError(f"products directory not found: {products_dir}")
    paths = sorted(products_dir.glob("*.json"))
    if not paths:
        raise ApiError(f"no thing models found in {products_dir}")

    products: List[Dict[str, Any]] = []
    seen: Dict[str, str] = {}
    for path in paths:
        try:
            text = path.read_bytes().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ApiError(
                f"thing model is not valid UTF-8: {path.name}: {exc}") from exc
        try:
            document = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ApiError(
                f"thing model is not valid JSON: {path.name}: {exc}") from exc
        if not isinstance(document, dict):
            raise ApiError(f"thing model must be a JSON object: {path.name}")

        profile = document.get("profile")
        if not isinstance(profile, dict):
            profile = {}
        product_id = str(
            profile.get("ProductId") or profile.get("productId") or "").strip()
        if not product_id:
            raise ApiError(f"thing model has no ProductId: {path.name}")
        if product_id in seen:
            raise ApiError(
                f"duplicate ProductId {product_id}: "
                f"{seen[product_id]} and {path.name}")
        seen[product_id] = path.name

        category_id = str(
            profile.get("CategoryId") or profile.get("categoryId") or "").strip()
        tsl_version = str(document.get("version") or "1.0").strip() or "1.0"
        name = path.stem.strip() or product_id

        products.append({
            "file": path.name,
            "product_id": product_id,
            "name": name,
            "model": product_id,
            "category_id": category_id,
            "tsl_version": tsl_version,
            "tsl": document,
        })
    return products


def build_payload(
        product: Dict[str, Any], strict_unknown: bool = False) -> Dict[str, Any]:
    return {
        "productId": product["product_id"],
        "name": product["name"],
        "model": product["model"],
        "categoryId": product["category_id"] or None,
        "tslVersion": product["tsl_version"],
        "tsl": product["tsl"],
        "strictUnknown": strict_unknown,
    }


def base_row(product: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "file": product["file"],
        "product_id": product["product_id"],
        "name": product["name"],
        "model": product["model"],
        "category_id": product["category_id"],
        "tsl_version": product["tsl_version"],
        "status": "",
        "tb_profile_id": "",
        "tb_asset_id": "",
        "tb_rule_chain_id": "",
        "error": "",
        "created_at": now_iso(),
    }


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


def format_issues(issues: List[Dict[str, Any]]) -> str:
    parts = []
    for issue in issues:
        code = issue.get("code") or "INVALID"
        message = issue.get("message") or ""
        path = issue.get("path") or ""
        parts.append(f"{code}{'@' + path if path else ''}: {message}")
    return "; ".join(parts)


def print_plan(product: Dict[str, Any]) -> None:
    document = product["tsl"]
    properties = document.get("properties") or []
    events = document.get("events") or []
    actions = document.get("actions") or []
    print(
        f"[dry-run] {product['file']} -> "
        f"productId={product['product_id']} "
        f"name={product['name']} "
        f"model={product['model']} "
        f"categoryId={product['category_id'] or '-'} "
        f"tslVersion={product['tsl_version']} "
        f"properties={len(properties)} events={len(events)} actions={len(actions)}"
    )


def apply_response(row: Dict[str, Any], response: Dict[str, Any]) -> None:
    row["tb_profile_id"] = response.get("tbProfileId") or ""
    row["tb_asset_id"] = response.get("tbAssetId") or ""
    row["tb_rule_chain_id"] = response.get("tbRuleChainId") or ""
    row["tsl_version"] = response.get("tslVersion") or row["tsl_version"]


def apply_existing_item(row: Dict[str, Any], item: Dict[str, Any]) -> None:
    row["name"] = item.get("name") or row["name"]
    row["model"] = item.get("model") or row["model"]
    row["category_id"] = item.get("categoryId") or row["category_id"]
    row["tsl_version"] = item.get("tslVersion") or row["tsl_version"]
    row["tb_profile_id"] = item.get("tbProfileId") or ""
    row["tb_asset_id"] = item.get("tbAssetId") or ""
    row["tb_rule_chain_id"] = item.get("tbRuleChainId") or ""


def main() -> int:
    args = parse_args()

    try:
        products = load_product_files(Path(args.products_dir))
    except ApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    report_path = resolve_output_path(args.output_dir, "product-import-report.csv")
    rows: List[Dict[str, Any]] = []

    if args.dry_run:
        for product in products:
            print_plan(product)
            row = base_row(product)
            row["status"] = "dry-run"
            rows.append(row)
        write_rows(report_path, rows)
        print(
            f"summary products={len(products)} dry_run={len(products)} "
            f"report={report_path}")
        return 0

    client = ProductImportClient(args.tb_url, args.thingmodel_url, args.timeout)
    try:
        if args.api_key:
            try:
                token = client.exchange_api_key_for_token(args.api_key)
            except Exception as exc:
                print(
                    "warning: API key to JWT exchange failed; using API key "
                    f"directly: {exc}", file=sys.stderr)
                token = client.api_key_token(args.api_key)
        else:
            password = args.password
            if not password:
                password = getpass.getpass(
                    f"ThingsBoard password for {args.username}: ")
            token = client.login(args.username, password)
        existing = {
            item.get("productId"): item
            for item in client.list_products(token)
            if item.get("productId")
        }
    except Exception as exc:
        print(f"error: ThingsBoard authentication or product list failed: {exc}",
              file=sys.stderr)
        if args.api_key and "HTTP 401" in str(exc):
            print(
                "hint: the target thing-model service may not support API key "
                "authentication yet; redeploy it or use --password",
                file=sys.stderr)
        return 1

    counts: Dict[str, int] = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "invalid": 0,
        "conflict": 0,
        "failed": 0,
    }

    for product in products:
        product_id = product["product_id"]
        row = base_row(product)

        if product_id in existing and not args.update_existing:
            row["status"] = "skipped"
            apply_existing_item(row, existing[product_id])
            counts["skipped"] += 1
            rows.append(row)
            print(f"skipped {product_id} ({product['file']}): already exists")
            continue

        if not args.skip_validate:
            try:
                validation = client.validate_thing_model(
                    token, product_id, product["tsl"])
            except Exception as exc:
                row["status"] = "failed"
                row["error"] = str(exc)
                counts["failed"] += 1
                rows.append(row)
                print(f"failed {product_id}: validation request failed: {exc}",
                      file=sys.stderr)
                continue
            warnings = validation.get("warnings") or []
            if not validation.get("valid"):
                row["status"] = "invalid"
                row["error"] = format_issues(validation.get("errors") or [])
                counts["invalid"] += 1
                rows.append(row)
                print(f"invalid {product_id}: {row['error']}", file=sys.stderr)
                continue
            if warnings:
                print(
                    f"warning {product_id}: "
                    f"{format_issues(warnings[:5])}"
                    + (" ..." if len(warnings) > 5 else ""))

        try:
            response = client.create_product(
                token, build_payload(product, args.strict_unknown))
        except Exception as exc:
            text = str(exc)
            if "HTTP 409" in text:
                row["status"] = "conflict"
                counts["conflict"] += 1
            else:
                row["status"] = "failed"
                counts["failed"] += 1
            row["error"] = text
            rows.append(row)
            print(f"{row['status']} {product_id}: {text}", file=sys.stderr)
            if "TENANT_ACCOUNT_MISSING" in text:
                print(
                    "hint: tenant vendor service account is missing; run "
                    "POST /api/admin/tenants/<tenantId>/provision-auto as SYS_ADMIN",
                    file=sys.stderr)
            continue

        row["status"] = "updated" if product_id in existing else "created"
        apply_response(row, response)
        counts[row["status"]] += 1
        rows.append(row)
        print(
            f"{row['status']} {product_id} ({product['file']}) "
            f"profile={row['tb_profile_id']} asset={row['tb_asset_id']} "
            f"ruleChain={row['tb_rule_chain_id']}")

    write_rows(report_path, rows)
    total = len(products)
    print(
        f"summary products={total} created={counts['created']} "
        f"updated={counts['updated']} skipped={counts['skipped']} "
        f"invalid={counts['invalid']} conflict={counts['conflict']} "
        f"failed={counts['failed']}")
    print(f"report: {report_path}")
    return 0 if counts["invalid"] == 0 and counts["conflict"] == 0 \
        and counts["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
