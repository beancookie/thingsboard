from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.api_catalog import ApiOperation

MANUALS_DIR = Path("..") / "docs" / "manuals"
OUTPUT = Path("config/api/manual_apis.yaml")
TABLE_ROW = re.compile(
    r"^\|\s*(GET|POST|PUT|DELETE|PATCH)\s*\|\s*`?([^`|]+?)`?\s*\|\s*(.*?)\s*\|"
)
CODE_LINE = re.compile(r"^(GET|POST|PUT|DELETE|PATCH)\s+(/api/[^\s|`]+)")
_PATH_PARAM = re.compile(r"\{([^{}]+)\}")
_EXCLUDED_PATHS = {
    "/api/ai-agent/chat",
    "/api/auth/login",
    "/api/auth/token",
}
_ENTITY_SUFFIX = ("/assign", "/ack", "/clear", "/read", "/root", "/default")
_SENSITIVE_MARKERS = (
    "credentials",
    "activationlink",
    "apikeys",
    "bulk_import",
    "testscript",
    "/rpc/",
    "/public/",
    "usercredentialsenabled",
    "sendactivationmail",
)


@dataclass
class ManualEndpoint:
    method: str
    path: str
    summary: str = ""
    source: str = ""


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="从使用手册生成 API 目录")
    parser.add_argument("--manuals", default=str(MANUALS_DIR))
    parser.add_argument("--catalog", default="config/api")
    parser.add_argument("--out", default=str(OUTPUT))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    operations = build_manual_operations(Path(args.manuals), Path(args.catalog))
    content = yaml.safe_dump(
        operations,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )

    out = Path(args.out)
    if args.check:
        if not out.exists() or out.read_text(encoding="utf-8") != content:
            print(f"{out} 已过期，请重新生成", file=sys.stderr)
            return 1
        print(f"{out} 已是最新")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"已生成 {out}，共 {len(operations)} 个接口")
    return 0


def build_manual_operations(manuals_dir: Path, catalog_dir: Path) -> list[dict[str, Any]]:
    endpoints = extract_manual_endpoints(manuals_dir)
    existing = load_existing_keys(catalog_dir)
    operations: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    for endpoint in endpoints:
        service, method, path = normalize_endpoint(endpoint.method, endpoint.path)
        key = (service, method, path)
        if key in existing:
            continue
        operation = build_operation(service, method, path, endpoint.summary)
        if operation["id"] in used_ids:
            operation["id"] = f"{operation['id']}.{method.lower()}.{_slug(path)}"
        used_ids.add(operation["id"])
        ApiOperation.model_validate(operation)
        operations.append(operation)

    operations.sort(key=lambda item: item["id"])
    return operations


def extract_manual_endpoints(manuals_dir: Path) -> list[ManualEndpoint]:
    found: list[ManualEndpoint] = []
    for file in sorted(manuals_dir.glob("*.md")):
        if file.name in {"README.md", "_template.md"}:
            continue
        for raw_line in file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            match = TABLE_ROW.match(line)
            if match:
                found.append(
                    ManualEndpoint(
                        method=match.group(1).upper(),
                        path=match.group(2).strip(),
                        summary=match.group(3).strip(),
                        source=file.name,
                    )
                )
                continue
            match = CODE_LINE.match(line)
            if match:
                found.append(
                    ManualEndpoint(
                        method=match.group(1).upper(),
                        path=match.group(2).strip(),
                        source=file.name,
                    )
                )

    deduped: OrderedDict[tuple[str, str], ManualEndpoint] = OrderedDict()
    for endpoint in found:
        service, method, path = normalize_endpoint(endpoint.method, endpoint.path)
        if path in _EXCLUDED_PATHS:
            continue
        if not path.startswith("/api/"):
            continue
        key = (method, f"{service}:{path}")
        current = deduped.get(key)
        if current is None:
            endpoint.method = method
            endpoint.path = path
            deduped[key] = endpoint
        elif not current.summary and endpoint.summary:
            current.summary = endpoint.summary
    return list(deduped.values())


def normalize_endpoint(method: str, raw_path: str) -> tuple[str, str, str]:
    path = raw_path.split("?", 1)[0].rstrip("/")
    service = "thingsboard"

    if path.startswith("/api/thing-model/"):
        service = "thing_model"
        path = "/api/" + path[len("/api/thing-model/") :]
    elif path == "/api/thing-model":
        service = "thing_model"
        path = "/api"
    elif path.startswith("/api/products") or path.startswith("/api/admin/tenants"):
        service = "thing_model"

    path = re.sub(
        r"/api/plugins/telemetry/(?:DEVICE|ASSET)/\{[^}]+\}",
        "/api/plugins/telemetry/{entityType}/{entityId}",
        path,
    )
    path = re.sub(
        r"/api/alarm/(?:DEVICE|ASSET)/\{[^}]+\}",
        "/api/alarm/{entityType}/{entityId}",
        path,
    )
    path = path.replace("/{gatewayId}", "/{deviceId}")
    path = path.replace("/{subDeviceId}", "/{deviceId}")
    return service, method.upper(), path


def load_existing_keys(catalog_dir: Path) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    if not catalog_dir.is_dir():
        return keys
    for file in catalog_dir.glob("*.yaml"):
        if file.name in {"overrides.yaml", "manual_apis.yaml"}:
            continue
        data = yaml.safe_load(file.read_text(encoding="utf-8")) or []
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            service = str(item.get("service") or "")
            method = str(item.get("method") or "").upper()
            path = str(item.get("path") or "").rstrip("/")
            if service and method and path:
                keys.add((service, method, path))
    return keys


def build_operation(service: str, method: str, path: str, summary: str) -> dict[str, Any]:
    action = _action(path, method)
    item: dict[str, Any] = {
        "id": f"{service}.{method.lower()}.{_slug(path)}",
        "service": service,
        "method": method,
        "path": path,
        "summary": _summary(service, method, path, action, summary),
        "aliases": _aliases(service, path, action),
        "tags": _tags(service, path),
        "mode": "read" if method == "GET" else "write",
        "code_access": _code_access(path, method),
        "permission": _permission(service, path),
        "risk": _risk(path, method, action),
        "enabled": not _is_sensitive(path),
        "params": _params(path, method, action),
    }
    tenant_param = _tenant_param(path)
    if tenant_param:
        item["tenant_param"] = tenant_param
    return item


def _params(path: str, method: str, action: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name in _PATH_PARAM.findall(path):
        param: dict[str, Any] = {
            "in": "path",
            "type": "string",
            "required": True,
        }
        if name == "entityType":
            param["default"] = "DEVICE"
            param["enum"] = ["DEVICE", "ASSET"]
        params[name] = param

    if method == "GET":
        params.update(
            {
                "pageSize": {"in": "query", "type": "integer", "default": 100},
                "page": {"in": "query", "type": "integer", "default": 0},
            }
        )
        if not _PATH_PARAM.search(path):
            params["textSearch"] = {"in": "query", "type": "string"}

    if "/plugins/telemetry/" in path:
        params.update(
            {
                "keys": {"in": "query", "type": "string"},
                "startTs": {"in": "query", "type": "integer"},
                "endTs": {"in": "query", "type": "integer"},
                "interval": {"in": "query", "type": "integer"},
                "limit": {"in": "query", "type": "integer"},
                "agg": {"in": "query", "type": "string"},
                "useStrictDataTypes": {"in": "query", "type": "boolean"},
            }
        )

    if path == "/api/tenant/devices":
        params["deviceName"] = {"in": "query", "type": "string"}
    if path == "/api/tenant/assets":
        params["assetName"] = {"in": "query", "type": "string"}
    if path == "/api/events":
        params.update(
            {
                "entityType": {"in": "query", "type": "string", "default": "DEVICE"},
                "entityId": {"in": "query", "type": "string", "required": True},
            }
        )
    if path == "/api/relations":
        params.update(
            {
                "fromId": {"in": "query", "type": "string", "required": True},
                "fromType": {"in": "query", "type": "string", "required": True},
                "relationType": {"in": "query", "type": "string"},
                "toId": {"in": "query", "type": "string"},
                "toType": {"in": "query", "type": "string"},
            }
        )

    if method != "GET" and action not in _ENTITY_SUFFIX:
        params["$body"] = {"in": "body", "type": "object"}
    return params


def _summary(
    service: str,
    method: str,
    path: str,
    action: str,
    manual_summary: str,
) -> str:
    if "/plugins/telemetry/" in path:
        if path.endswith("/keys/timeseries"):
            return "查询遥测键"
        if path.endswith("/values/timeseries"):
            if method == "GET":
                return "查询最新或历史遥测数据"
        if "/values/attributes" in path:
            return "查询实体属性数据"
        if "/attributes/" in path:
            return "写入实体属性数据"
    return manual_summary or _default_summary(service, method, path, action)


def _default_summary(service: str, method: str, path: str, action: str) -> str:
    resource = _resource_name(path)
    prefix = {
        "GET": "查询",
        "POST": "执行" if action else "创建",
        "PUT": "更新",
        "PATCH": "更新",
        "DELETE": "删除",
    }.get(method, method)
    if action == "ack":
        prefix = "确认"
    elif action == "clear":
        prefix = "清除"
    elif action == "assign":
        prefix = "分配"
    elif action == "read":
        prefix = "标记已读"
    elif action == "testScript":
        prefix = "测试脚本"
    elif action == "preview":
        prefix = "预览"
    elif action == "bulk_import":
        prefix = "批量导入"
    return f"{prefix}{resource}"


def _resource_name(path: str) -> str:
    lower = path.lower()
    mapping = (
        ("plugins/telemetry", "遥测数据"),
        ("calculatedfield", "计算字段"),
        ("notification", "通知"),
        ("alarm", "告警"),
        ("customer", "客户"),
        ("assetprofile", "资产配置"),
        ("asset", "资产"),
        ("deviceprofile", "设备配置"),
        ("device", "设备"),
        ("rulechain", "规则链"),
        ("rulenode", "规则节点"),
        ("tenantprofile", "租户配置"),
        ("tenant", "租户"),
        ("apiKey".lower(), "API 密钥"),
        ("user", "用户"),
        ("relation", "实体关系"),
        ("rpc", "RPC"),
        ("event", "事件"),
        ("product", "产品"),
        ("calculated", "计算字段"),
        ("notification", "通知"),
        ("admin", "管理"),
        ("auth", "认证"),
    )
    for marker, name in mapping:
        if marker in lower:
            return name
    return "接口"


def _aliases(service: str, path: str, action: str) -> list[str]:
    resource = _resource_name(path)
    aliases = [resource]
    for segment in path.split("/"):
        if segment in {"api", ""} or segment.startswith("{"):
            continue
        aliases.append(segment)
    if action:
        aliases.append(action)
    return sorted(set(aliases), key=aliases.index)


def _tags(service: str, path: str) -> list[str]:
    parts = [part for part in path.split("/") if part and not part.startswith("{")]
    domain = parts[1] if len(parts) > 1 else service
    return [domain, _resource_name(path)]


def _permission(service: str, path: str) -> str:
    lower = path.lower()
    if service == "thing_model":
        return "SYS_ADMIN" if lower.startswith("/api/admin") else "TENANT_ADMIN"
    if lower.startswith("/api/admin") or lower.startswith("/api/tenantprofile"):
        return "SYS_ADMIN"
    if lower in {"/api/tenant", "/api/tenants", "/api/tenantinfos"}:
        return "SYS_ADMIN"
    if lower.startswith("/api/tenant/{") and not lower.startswith("/api/tenant/devices"):
        return "SYS_ADMIN"
    if lower.startswith("/api/auth"):
        return "ANY"
    if any(
        marker in lower
        for marker in (
            "/plugins/telemetry",
            "/api/alarm",
            "/api/notifications",
            "/api/notification",
            "/api/events",
            "/api/relations",
            "/api/device-connectivity",
        )
    ):
        return "ANY"
    return "TENANT_ADMIN"


def _code_access(path: str, method: str) -> str:
    if _is_sensitive(path):
        return "none"
    return "read" if method == "GET" else "write"


def _risk(path: str, method: str, action: str) -> str:
    lower = path.lower()
    if method == "DELETE":
        return "high"
    if _is_sensitive(path) or lower.startswith("/api/rpc/") or "/public/" in lower:
        return "high"
    if method in {"POST", "PUT", "PATCH"}:
        return "medium"
    return "low"


def _is_sensitive(path: str) -> bool:
    lower = path.lower()
    return any(marker in lower for marker in _SENSITIVE_MARKERS)


def _tenant_param(path: str) -> str | None:
    for name in ("tenantId", "tenant_id"):
        if f"{{{name}}}" in path:
            return name
    return None


def _slug(path: str) -> str:
    value = path.removeprefix("/api/")
    value = _PATH_PARAM.sub(lambda match: f"by_{match.group(1)}", value)
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return value or "root"


def _action(path: str, method: str) -> str:
    if method == "GET":
        return ""
    tail = path.rstrip("/").rsplit("/", 1)[-1]
    if tail in {"ack", "clear", "assign", "read", "root", "default"}:
        return tail
    if tail in {"testScript", "testscript"}:
        return "testScript"
    if tail == "preview":
        return "preview"
    if tail == "bulk_import":
        return "bulk_import"
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
