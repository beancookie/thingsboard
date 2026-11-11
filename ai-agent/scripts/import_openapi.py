from __future__ import annotations

import argparse
import copy
import difflib
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.api_catalog import ApiOperation

HTTP_METHODS = ("get", "post", "put", "patch", "delete")
EXCLUDED_PREFIXES = (
    "/api/auth",
    "/api/noauth",
    "/actuator",
    "/swagger",
    "/v3/api-docs",
)
SENSITIVE_MARKERS = (
    "/auth",
    "/password",
    "/token",
    "/secret",
    "/credential",
)
_WORD = re.compile(r"[^A-Za-z0-9]+")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="从 OpenAPI 生成 API 目录")
    parser.add_argument("--service", required=True, choices=["thingsboard", "thing_model"])
    parser.add_argument("--spec", required=True, help="OpenAPI JSON 文件路径或 URL")
    parser.add_argument("--out", required=True, help="输出 YAML 文件")
    parser.add_argument("--overrides", default=None, help="overrides.yaml 路径")
    parser.add_argument("--check", action="store_true", help="只检查输出是否最新")
    args = parser.parse_args(argv)

    spec = _load_spec(args.spec)
    operations = convert_openapi(spec, args.service)
    overrides = _load_overrides(Path(args.overrides)) if args.overrides else {}
    content = render_catalog(operations, overrides)

    out = Path(args.out)
    if args.check:
        return _check(out, content)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"已生成 {out}，共 {len(operations)} 个接口")
    return 0


def convert_openapi(spec: dict[str, Any], service: str) -> list[dict[str, Any]]:
    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        raise ValueError("OpenAPI paths 必须是对象")

    operations: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    for path in sorted(paths):
        path_item = paths[path]
        if not isinstance(path_item, dict):
            continue
        if _is_excluded(path):
            continue
        path_parameters = _resolve_parameters(spec, path_item.get("parameters") or [])

        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            if _has_unsupported_body(spec, operation):
                continue

            operation_id = _operation_id(service, method, path, operation, used_ids)
            used_ids.add(operation_id)
            parameters = _merge_parameters(
                path_parameters,
                _resolve_parameters(spec, operation.get("parameters") or []),
            )
            params = _parameters_to_catalog(spec, parameters)
            body_params = _request_body_to_catalog(spec, operation.get("requestBody"))
            params.update(body_params)

            item: dict[str, Any] = {
                "id": operation_id,
                "service": service,
                "method": method.upper(),
                "path": path,
                "summary": _summary(operation, operation_id),
                "aliases": _aliases(operation, operation_id),
                "tags": _tags(operation),
                "mode": "read" if method == "get" else "write",
                "code_access": _code_access(path, method),
                "permission": _permission(service, path),
                "risk": _risk(method),
                "enabled": not _is_sensitive(path),
                "params": params,
            }
            tenant_param = _tenant_param(path)
            if tenant_param:
                item["tenant_param"] = tenant_param
            operations.append(item)

    operations.sort(key=lambda item: item["id"])
    _validate(operations)
    return operations


def render_catalog(
    operations: list[dict[str, Any]],
    overrides: dict[str, dict[str, Any]] | None = None,
) -> str:
    overrides = overrides or {}
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for operation in operations:
        item = copy.deepcopy(operation)
        operation_id = item["id"]
        seen.add(operation_id)
        _deep_merge(item, overrides.get(operation_id, {}))
        merged.append(item)

    for operation_id, override in overrides.items():
        if operation_id in seen:
            continue
        item = copy.deepcopy(override)
        item.setdefault("id", operation_id)
        merged.append(item)

    merged.sort(key=lambda item: item.get("id", ""))
    return yaml.safe_dump(
        merged,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


def _load_spec(location: str) -> dict[str, Any]:
    parsed = urlparse(location)
    if parsed.scheme in {"http", "https"}:
        response = httpx.get(location, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        return response.json()

    data = yaml.safe_load(Path(location).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("OpenAPI 文件必须是对象")
    return data


def _load_overrides(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("overrides.yaml 必须是 id 到配置的映射")
    return {
        str(key): dict(value) for key, value in data.items() if isinstance(value, dict)
    }


def _check(path: Path, content: str) -> int:
    if not path.exists():
        print(f"{path} 不存在，需要生成", file=sys.stderr)
        return 1
    current = path.read_text(encoding="utf-8")
    if current == content:
        print(f"{path} 已是最新")
        return 0

    diff = difflib.unified_diff(
        current.splitlines(),
        content.splitlines(),
        fromfile=str(path),
        tofile="generated",
        lineterm="",
    )
    print("\n".join(diff), file=sys.stderr)
    return 1


def _validate(operations: list[dict[str, Any]]) -> None:
    for operation in operations:
        ApiOperation.model_validate(operation)


def _resolve(spec: dict[str, Any], node: Any) -> Any:
    if not isinstance(node, dict):
        return node
    ref = node.get("$ref")
    if not isinstance(ref, str):
        return node
    if not ref.startswith("#/"):
        return node
    target: Any = spec
    for part in ref[2:].split("/"):
        if not isinstance(target, dict):
            return node
        target = target.get(part.replace("~1", "/").replace("~0", "~"))
    return target


def _resolve_parameters(spec: dict[str, Any], parameters: list[Any]) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for parameter in parameters:
        item = _resolve(spec, parameter)
        if isinstance(item, dict):
            resolved.append(item)
    return resolved


def _merge_parameters(
    path_parameters: list[dict[str, Any]],
    operation_parameters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    keyed: dict[tuple[str, str], dict[str, Any]] = {}
    for parameter in path_parameters + operation_parameters:
        name = str(parameter.get("name") or "")
        location = str(parameter.get("in") or "")
        if name and location in {"path", "query"}:
            keyed[(name, location)] = parameter
    return list(keyed.values())


def _parameters_to_catalog(
    spec: dict[str, Any],
    parameters: list[dict[str, Any]],
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for parameter in parameters:
        name = str(parameter.get("name") or "")
        location = str(parameter.get("in") or "")
        if not name or location not in {"path", "query"}:
            continue
        schema = _resolve(spec, parameter.get("schema") or {})
        item = _schema_to_parameter(schema, location, str(parameter.get("description") or ""))
        item["required"] = bool(parameter.get("required")) or location == "path"
        params[name] = item
    return params


def _request_body_to_catalog(
    spec: dict[str, Any],
    request_body: Any,
) -> dict[str, Any]:
    body = _resolve(spec, request_body)
    if not isinstance(body, dict):
        return {}
    content = body.get("content") or {}
    if not isinstance(content, dict):
        return {}
    media = content.get("application/json") or content.get("*/*")
    if not isinstance(media, dict):
        return {}
    schema = _resolve(spec, media.get("schema") or {})
    if not isinstance(schema, dict):
        return {}

    if schema.get("type") == "object" or "properties" in schema:
        properties = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        if not isinstance(properties, dict):
            return {}
        params: dict[str, Any] = {}
        for name, raw_property in properties.items():
            resolved = _resolve(spec, raw_property)
            if not isinstance(resolved, dict):
                continue
            item = _schema_to_parameter(resolved, "body", str(resolved.get("description") or ""))
            item["required"] = str(name) in required
            params[str(name)] = item
        return params

    item = _schema_to_parameter(schema, "body", str(body.get("description") or ""))
    item["required"] = bool(body.get("required"))
    return {"$body": item}


def _schema_to_parameter(schema: dict[str, Any], location: str, description: str) -> dict[str, Any]:
    schema = schema or {}
    item: dict[str, Any] = {
        "in": location,
        "type": _schema_type(schema),
        "required": False,
    }
    if description:
        item["description"] = description
    if "default" in schema:
        item["default"] = schema["default"]
    if isinstance(schema.get("enum"), list):
        item["enum"] = schema["enum"]
    return item


def _schema_type(schema: dict[str, Any]) -> str:
    schema_type = schema.get("type")
    if schema_type in {"integer", "number", "boolean", "array", "object"}:
        return str(schema_type)
    if "properties" in schema:
        return "object"
    if "items" in schema:
        return "array"
    return "string"


def _has_unsupported_body(spec: dict[str, Any], operation: dict[str, Any]) -> bool:
    body = _resolve(spec, operation.get("requestBody"))
    if not isinstance(body, dict):
        return False
    content = body.get("content") or {}
    if not isinstance(content, dict) or not content:
        return False
    json_types = {"application/json", "*/*"}
    if any(name in content for name in json_types):
        return False
    return True


def _operation_id(
    service: str,
    method: str,
    path: str,
    operation: dict[str, Any],
    used: set[str],
) -> str:
    raw = str(operation.get("operationId") or "").strip()
    if raw:
        candidate = f"{service}.{raw}"
    else:
        slug = _slug(path)
        candidate = f"{service}.{method.lower()}.{slug}"
    if candidate in used:
        candidate = f"{candidate}.{method.lower()}.{_slug(path)}"
    suffix = 2
    base = candidate
    while candidate in used:
        candidate = f"{base}.{suffix}"
        suffix += 1
    return candidate


def _slug(value: str) -> str:
    return _WORD.sub("_", value).strip("_").lower() or "root"


def _summary(operation: dict[str, Any], operation_id: str) -> str:
    summary = str(operation.get("summary") or "").strip()
    if summary:
        return summary
    description = str(operation.get("description") or "").strip()
    if description:
        return description.splitlines()[0][:200]
    return operation_id


def _aliases(operation: dict[str, Any], operation_id: str) -> list[str]:
    aliases = [operation_id.rsplit(".", 1)[-1]]
    tags = _tags(operation)
    aliases.extend(tag for tag in tags if tag not in aliases)
    return aliases


def _tags(operation: dict[str, Any]) -> list[str]:
    tags = operation.get("tags")
    if not isinstance(tags, list):
        return []
    return [str(tag) for tag in tags if str(tag).strip()]


def _permission(service: str, path: str) -> str:
    if path.startswith("/api/auth") or path == "/api/auth/me":
        return "ANY"
    if path.startswith("/api/admin"):
        return "SYS_ADMIN"
    if service == "thing_model":
        return "TENANT_ADMIN"
    if path in {"/api/tenants", "/api/tenant"}:
        return "SYS_ADMIN"
    if path.startswith("/api/tenant/{"):
        return "SYS_ADMIN"
    if path.startswith("/api/user"):
        return "ANY"
    return "TENANT_ADMIN"


def _code_access(path: str, method: str) -> str:
    if _is_sensitive(path):
        return "none"
    return "read" if method == "get" else "write"


def _risk(method: str) -> str:
    if method == "delete":
        return "high"
    if method in {"post", "put", "patch"}:
        return "medium"
    return "low"


def _tenant_param(path: str) -> str | None:
    for name in ("tenantId", "tenant_id"):
        if f"{{{name}}}" in path:
            return name
    return None


def _is_excluded(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def _is_sensitive(path: str) -> bool:
    return any(marker in path.lower() for marker in SENSITIVE_MARKERS)


def _deep_merge(target: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value


if __name__ == "__main__":
    raise SystemExit(main())
