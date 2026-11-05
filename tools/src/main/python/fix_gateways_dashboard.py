#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlparse

import requests

DEFAULT_TB_URL = "http://localhost:18080"
DEFAULT_USERNAME = "sysadmin@thingsboard.org"
DEFAULT_RESOURCE_TYPE = "dashboard"
DEFAULT_SCOPE = "system"
DEFAULT_RESOURCE_KEY = "gateways_dashboard.json"
DEFAULT_WIDGET_ID = "79f59106-758f-c428-8b93-4341faea705d"
DEFAULT_RELATION_ALIAS_ID = "a75d9031-ba51-8da4-81be-de65061b72f4"
OLD_RELATION_TYPES = {"创建d", "Created"}
NEW_RELATION_TYPE = "Contains"

OLD_STATUS_MARKER = "data[0].Status === 'true'"
INTERMEDIATE_STATUS_MARKER = (
    "(data[0].active === true || String(data[0].active) === 'true')")
FINAL_STATUS_MARKER = (
    "(data[0].Status === true || String(data[0].Status) === 'true')")
OLD_NAME_MARKER = "data[0].Name"
INTERMEDIATE_NAME_MARKER = "data[0].name"
FINAL_NAME_MARKER = "data[0].entityName"
OLD_TYPE_MARKER = "data[0].Type"
NEW_TYPE_MARKER = "data[0].type"


class DashboardFixError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fix the gateway status card in a ThingsBoard gateway dashboard resource.")
    parser.add_argument(
        "--tb-url",
        default=None,
        help="ThingsBoard base URL; defaults to TB_URL or http://localhost:18080",
    )
    parser.add_argument(
        "--username",
        default=None,
        help="SYS_ADMIN username; defaults to TB_SYSADMIN_USERNAME or sysadmin@thingsboard.org",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="SYS_ADMIN password; defaults to TB_SYSADMIN_PASSWORD or prompt",
    )
    parser.add_argument(
        "--resource-type",
        default=DEFAULT_RESOURCE_TYPE,
        help="Resource type (default: dashboard)",
    )
    parser.add_argument(
        "--scope",
        default=DEFAULT_SCOPE,
        choices=["system", "tenant"],
        help="Resource scope (default: system)",
    )
    parser.add_argument(
        "--resource-key",
        default=DEFAULT_RESOURCE_KEY,
        help="Resource key (default: gateways_dashboard.json)",
    )
    parser.add_argument(
        "--resource-id",
        default=None,
        help="Resource UUID; when omitted, resolved from resource type/scope/key",
    )
    parser.add_argument(
        "--widget-id",
        default=DEFAULT_WIDGET_ID,
        help="Gateway status widget id",
    )
    parser.add_argument(
        "--type-mode",
        default="attribute",
        choices=["attribute", "entity", "none"],
        help="attribute displays the mock Type attribute; entity displays the device profile type",
    )
    parser.add_argument(
        "--backup-dir",
        default="tb-dashboard-backups",
        help="Directory for backup files",
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
        "--no-backup",
        action="store_true",
        help="Do not write a backup file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Upload even if the dashboard is already fixed",
    )
    parser.add_argument(
        "--rollback",
        default=None,
        metavar="FILE",
        help="Restore the given backup file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print additional details",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Upload the fixed dashboard; without this flag the script only prints a dry run",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicitly request a dry run (the default)",
    )
    return parser.parse_args()


def load_json(content: bytes, source: str) -> Dict[str, Any]:
    try:
        data = json.loads(content.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise DashboardFixError(f"{source} is not valid UTF-8: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DashboardFixError(f"{source} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise DashboardFixError(f"{source} must be a JSON object")
    return data


def dump_json(data: Dict[str, Any]) -> bytes:
    return json.dumps(
        data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def find_widget(data: Dict[str, Any], widget_id: str) -> Dict[str, Any]:
    widgets = data.get("configuration", {}).get("widgets")
    if not isinstance(widgets, dict):
        raise DashboardFixError("dashboard has no configuration.widgets")
    widget = widgets.get(widget_id)
    if not isinstance(widget, dict):
        raise DashboardFixError(f"widget not found: {widget_id}")
    return widget


def widget_markdown(widget: Dict[str, Any]) -> str:
    config = widget.get("config")
    if not isinstance(config, dict):
        raise DashboardFixError("widget has no config")
    settings = config.get("settings")
    if not isinstance(settings, dict):
        raise DashboardFixError("widget has no config.settings")
    markdown = settings.get("markdownTextFunction")
    if not isinstance(markdown, str):
        raise DashboardFixError("widget has no markdownTextFunction")
    return markdown


def widget_datasources(widget: Dict[str, Any]) -> List[Dict[str, Any]]:
    config = widget.get("config")
    if not isinstance(config, dict):
        raise DashboardFixError("widget has no config")
    datasources = config.get("datasources")
    if not isinstance(datasources, list):
        raise DashboardFixError("widget has no config.datasources")
    return datasources


def iter_data_keys(widget: Dict[str, Any]):
    for datasource in widget_datasources(widget):
        data_keys = datasource.get("dataKeys")
        if isinstance(data_keys, list):
            for data_key in data_keys:
                if isinstance(data_key, dict):
                    yield data_key


def ensure_data_key_label(
        widget: Dict[str, Any],
        name: str,
        label: str,
        required: bool = False) -> bool:
    found = False
    changed = False
    for data_key in iter_data_keys(widget):
        if data_key.get("name") == name:
            found = True
            if data_key.get("label") != label:
                data_key["label"] = label
                changed = True
    if not found and required:
        raise DashboardFixError(
            f"widget has no data key named {name}; cannot fix status card")
    return changed


def ensure_type_attribute(widget: Dict[str, Any], markdown: str) -> tuple[str, bool]:
    changed = False
    found = False
    for data_key in iter_data_keys(widget):
        if data_key.get("name") == "Type" and data_key.get("type") == "attribute":
            found = True
        elif data_key.get("name") == "type" and data_key.get("type") == "entityField":
            data_key["name"] = "Type"
            data_key["type"] = "attribute"
            data_key["label"] = "Type"
            changed = True
            found = True
    if not found:
        datasources = widget_datasources(widget)
        if not datasources:
            raise DashboardFixError("widget has no datasource to add Type key")
        datasource = datasources[0]
        data_keys = datasource.setdefault("dataKeys", [])
        if not isinstance(data_keys, list):
            raise DashboardFixError("widget dataKeys is not a list")
        data_keys.append({
            "name": "Type",
            "type": "attribute",
            "label": "Type",
            "color": "#03a9f4",
            "settings": {},
        })
        changed = True
    if OLD_TYPE_MARKER in markdown:
        return markdown, changed
    if NEW_TYPE_MARKER in markdown:
        return markdown.replace(NEW_TYPE_MARKER, OLD_TYPE_MARKER), True
    raise DashboardFixError("widget markdown does not reference Type/type field")


def ensure_type_entity(widget: Dict[str, Any], markdown: str) -> tuple[str, bool]:
    changed = False
    found = False
    for data_key in iter_data_keys(widget):
        if data_key.get("name") == "type" and data_key.get("type") == "entityField":
            found = True
        elif data_key.get("name") == "Type" and data_key.get("type") == "attribute":
            data_key["name"] = "type"
            data_key["type"] = "entityField"
            data_key["label"] = "Type"
            changed = True
            found = True
    if not found:
        datasources = widget_datasources(widget)
        if not datasources:
            raise DashboardFixError("widget has no datasource to add type key")
        datasource = datasources[0]
        data_keys = datasource.setdefault("dataKeys", [])
        if not isinstance(data_keys, list):
            raise DashboardFixError("widget dataKeys is not a list")
        data_keys.append({
            "name": "type",
            "type": "entityField",
            "label": "Type",
            "color": "#4caf50",
            "settings": {},
        })
        changed = True
    if NEW_TYPE_MARKER in markdown:
        return markdown, changed
    if OLD_TYPE_MARKER in markdown:
        return markdown.replace(OLD_TYPE_MARKER, NEW_TYPE_MARKER), True
    raise DashboardFixError("widget markdown does not reference Type/type field")


def ensure_relation_type(data: Dict[str, Any]) -> bool:
    aliases = data.get("configuration", {}).get("entityAliases")
    if not isinstance(aliases, dict):
        raise DashboardFixError("dashboard has no configuration.entityAliases")
    alias = aliases.get(DEFAULT_RELATION_ALIAS_ID)
    if not isinstance(alias, dict):
        raise DashboardFixError(
            f"gateway devices alias not found: {DEFAULT_RELATION_ALIAS_ID}")
    filter_config = alias.get("filter")
    if not isinstance(filter_config, dict):
        raise DashboardFixError("gateway devices alias has no filter")
    filters = filter_config.get("filters")
    if not isinstance(filters, list):
        raise DashboardFixError("gateway devices alias has no filters")
    changed = False
    for item in filters:
        if isinstance(item, dict) and item.get("relationType") in OLD_RELATION_TYPES:
            item["relationType"] = NEW_RELATION_TYPE
            changed = True
    return changed


def apply_gateway_fix(
        data: Dict[str, Any],
        widget_id: str,
        type_mode: str) -> Dict[str, Any]:
    widget = find_widget(data, widget_id)
    markdown = widget_markdown(widget)
    changes: List[str] = []

    if ensure_relation_type(data):
        changes.append("relation-type")

    if ensure_data_key_label(widget, "active", "Status", required=True):
        changes.append("status-label")
    if ensure_data_key_label(widget, "Version", "Version"):
        changes.append("version-label")

    if OLD_STATUS_MARKER in markdown:
        markdown = markdown.replace(OLD_STATUS_MARKER, FINAL_STATUS_MARKER)
        changes.append("status")
    elif INTERMEDIATE_STATUS_MARKER in markdown:
        markdown = markdown.replace(
            INTERMEDIATE_STATUS_MARKER, FINAL_STATUS_MARKER)
        changes.append("status")
    else:
        new_markdown = re.sub(
            r"data\[0\]\.active(?!\w)", "data[0].Status", markdown)
        if new_markdown != markdown:
            markdown = new_markdown
            changes.append("status")
        if "data[0].Status" not in markdown:
            raise DashboardFixError(
                "unsupported dashboard: status logic not found in widget markdown")

    new_markdown = re.sub(
        r"data\[0\]\.(?:Name|name)(?!\w)",
        FINAL_NAME_MARKER,
        markdown,
    )
    if new_markdown != markdown:
        markdown = new_markdown
        changes.append("name")
    if FINAL_NAME_MARKER not in markdown:
        raise DashboardFixError(
            "unsupported dashboard: gateway name logic not found in widget markdown")

    if type_mode == "attribute":
        markdown, changed = ensure_type_attribute(widget, markdown)
        if changed:
            changes.append("type")
    elif type_mode == "entity":
        markdown, changed = ensure_type_entity(widget, markdown)
        if changed:
            changes.append("type")

    widget["config"]["settings"]["markdownTextFunction"] = markdown
    return {
        "changes": changes,
        "markdown": markdown,
        "type_mode": type_mode,
    }


def save_backup(
        backup_dir: str,
        resource_key: str,
        content: bytes) -> Path:
    directory = Path(backup_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = directory / f"{Path(resource_key).stem}.{stamp}.json"
    path.write_bytes(content)
    return path


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
            raise DashboardFixError(
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
            raise DashboardFixError("login response did not contain a token")
        return token

    def get_resource_info(
            self,
            token: str,
            resource_type: str,
            scope: str,
            resource_key: str) -> Dict[str, Any]:
        url = (
            f"{self.base_url}/api/resource/{resource_type}/{scope}/"
            f"{quote(resource_key, safe='')}/info"
        )
        response = self.session.get(
            url, headers=self._headers(token), timeout=self.timeout)
        self._check(response, "resource info")
        return response.json()

    def get_resource_data(
            self,
            token: str,
            resource_type: str,
            scope: str,
            resource_key: str) -> tuple[bytes, str]:
        url = (
            f"{self.base_url}/api/resource/{resource_type}/{scope}/"
            f"{quote(resource_key, safe='')}"
        )
        response = self.session.get(
            url, headers=self._headers(token), timeout=self.timeout)
        self._check(response, "resource download")
        return response.content, response.headers.get("ETag", "").strip('"')

    def put_resource_data(
            self,
            token: str,
            resource_id: str,
            file_name: str,
            content: bytes) -> Dict[str, Any]:
        response = self.session.put(
            f"{self.base_url}/api/resource/{resource_id}/data",
            headers=self._headers(token),
            files={"file": (file_name, content, "application/json")},
            timeout=self.timeout,
        )
        self._check(response, "resource upload")
        return response.json()


def print_summary(
        resource_id: str,
        resource_key: str,
        old_etag: str,
        new_etag: str,
        changes: List[str],
        backup_path: Optional[Path],
        applied: bool,
        verbose: bool,
        report: Dict[str, Any]) -> None:
    print(f"resource: {resource_key} ({resource_id})")
    print(f"old etag: {old_etag or '<none>'}")
    print(f"changes: {', '.join(changes) if changes else 'none'}")
    print(f"new etag: {new_etag}")
    if backup_path is not None:
        print(f"backup: {backup_path}")
    if not applied:
        print("dry run: no changes uploaded; use --apply to upload")
    if verbose:
        print("markdown:")
        print(report["markdown"])


def main() -> int:
    args = parse_args()

    tb_url = args.tb_url or os.environ.get("TB_URL", DEFAULT_TB_URL)
    username = args.username or os.environ.get(
        "TB_SYSADMIN_USERNAME", DEFAULT_USERNAME)
    password = args.password or os.environ.get("TB_SYSADMIN_PASSWORD")
    if not password:
        password = getpass.getpass(
            f"ThingsBoard SYS_ADMIN password for {username}: ")

    client = TbClient(
        tb_url, args.timeout, verify=not args.insecure)

    try:
        token = client.login(username, password)
        info = client.get_resource_info(
            token, args.resource_type, args.scope, args.resource_key)
        resource_id = args.resource_id or info.get("id", {}).get("id")
        if not resource_id:
            raise DashboardFixError("resource id is missing")
        file_name = info.get("fileName") or args.resource_key

        if args.rollback:
            rollback_path = Path(args.rollback)
            if not rollback_path.is_file():
                raise DashboardFixError(
                    f"rollback file not found: {rollback_path}")
            rollback_content = rollback_path.read_bytes()
            load_json(rollback_content, str(rollback_path))

            if not args.apply:
                print_summary(
                    resource_id, args.resource_key, info.get("etag", ""),
                    hashlib.sha256(rollback_content).hexdigest(),
                    ["rollback"], None, False, args.verbose,
                    {"markdown": ""})
                print(f"dry run: would restore {rollback_path}")
                return 0

            backup_path = None
            if not args.no_backup:
                current, _ = client.get_resource_data(
                    token, args.resource_type, args.scope, args.resource_key)
                backup_path = save_backup(
                    args.backup_dir, args.resource_key, current)

            result = client.put_resource_data(
                token, resource_id, file_name, rollback_content)
            print_summary(
                resource_id, args.resource_key, info.get("etag", ""),
                result.get("etag", hashlib.sha256(
                    rollback_content).hexdigest()),
                ["rollback"], backup_path, True, args.verbose,
                {"markdown": ""})
            return 0

        data_bytes, old_etag = client.get_resource_data(
            token, args.resource_type, args.scope, args.resource_key)
        data = load_json(data_bytes, args.resource_key)
        report = apply_gateway_fix(
            data, args.widget_id, args.type_mode)
        new_content = dump_json(data)
        new_etag = hashlib.sha256(new_content).hexdigest()

        if not report["changes"] and not args.force:
            print_summary(
                resource_id, args.resource_key, old_etag, new_etag,
                [], None, args.apply, args.verbose, report)
            print("already fixed")
            return 0

        if not args.apply:
            print_summary(
                resource_id, args.resource_key, old_etag, new_etag,
                report["changes"], None, False, args.verbose, report)
            return 0

        backup_path = None
        if not args.no_backup:
            backup_path = save_backup(
                args.backup_dir, args.resource_key, data_bytes)

        result = client.put_resource_data(
            token, resource_id, file_name, new_content)
        uploaded_etag = result.get("etag", new_etag)

        verify_bytes, verify_etag = client.get_resource_data(
            token, args.resource_type, args.scope, args.resource_key)
        verify_data = load_json(verify_bytes, args.resource_key)
        verify_report = apply_gateway_fix(
            verify_data, args.widget_id, args.type_mode)
        if verify_report["changes"]:
            raise DashboardFixError(
                "verification failed: dashboard still requires changes "
                f"{verify_report['changes']}")

        print_summary(
            resource_id, args.resource_key, old_etag, verify_etag,
            report["changes"], backup_path, True, args.verbose, report)
        print(f"uploaded etag: {uploaded_etag}")
        print("verification: ok")
        return 0
    except DashboardFixError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
