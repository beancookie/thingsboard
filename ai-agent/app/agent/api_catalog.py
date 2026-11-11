from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

ServiceName = Literal["thingsboard", "thing_model"]
OperationMode = Literal["read", "write"]
Permission = Literal["ANY", "TENANT_ADMIN", "SYS_ADMIN"]
RiskLevel = Literal["low", "medium", "high"]
CodeAccess = Literal["none", "read", "write"]

_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
_PATH_PARAMETER = re.compile(r"\{([^{}]+)\}")
_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
logger = logging.getLogger(__name__)


class ApiParameter(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    location: Literal["path", "query", "body"] = Field(alias="in")
    name: str | None = None
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str | None = None
    enum: list[Any] | None = None

    @property
    def target_name(self) -> str:
        return self.name or ""


class ApiOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    service: ServiceName
    method: str
    path: str
    summary: str
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    mode: OperationMode
    code_access: CodeAccess | None = None
    permission: Permission = "ANY"
    tenant_param: str | None = None
    risk: RiskLevel = "low"
    enabled: bool = True
    handler: str | None = None
    params: dict[str, ApiParameter] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate(self) -> ApiOperation:
        self.id = self.id.strip()
        if not self.id:
            raise ValueError("operation id 不能为空")

        self.method = self.method.upper()
        if self.method not in _HTTP_METHODS:
            raise ValueError(f"不支持的 HTTP 方法: {self.method}")

        if not self.path.startswith("/"):
            raise ValueError("path 必须以 / 开头")

        if self.code_access is None:
            self.code_access = "read" if self.mode == "read" else "write"

        placeholders = set(_PATH_PARAMETER.findall(self.path))
        declared_path_params = {
            key for key, parameter in self.params.items() if parameter.location == "path"
        }
        missing = placeholders - declared_path_params
        if missing:
            raise ValueError(f"path 参数未在 params 中声明: {', '.join(sorted(missing))}")
        extra = declared_path_params - placeholders
        if extra:
            raise ValueError(f"params 中的 path 参数未出现在 path 中: {', '.join(sorted(extra))}")

        for key, parameter in self.params.items():
            if parameter.location == "path" and not parameter.required:
                raise ValueError(f"path 参数必须 required: {key}")
            if parameter.location == "body" and not parameter.name and key != "$body":
                parameter.name = key

        return self


class ApiCatalog:
    def __init__(self, operations: list[ApiOperation]):
        self._operations: dict[str, ApiOperation] = {}
        for operation in operations:
            if operation.id in self._operations:
                raise ValueError(f"重复的 operation id: {operation.id}")
            self._operations[operation.id] = operation

    @classmethod
    def load(cls, directory: str | Path) -> ApiCatalog:
        root = Path(directory)
        overrides = _load_overrides(root / "overrides.yaml")
        operations: list[ApiOperation] = []
        seen: set[str] = set()

        if not root.is_dir():
            logger.warning("API 目录不存在，已跳过加载: %s", root)
            return cls(operations)

        if root.is_dir():
            for path in sorted(root.glob("*.yaml")):
                if path.name == "overrides.yaml":
                    continue
                for raw in _load_operation_file(path):
                    operation_id = str(raw.get("id") or "")
                    if operation_id:
                        _deep_merge(raw, overrides.get(operation_id, {}))
                        seen.add(operation_id)
                    operations.append(ApiOperation.model_validate(raw))

            for operation_id, override in overrides.items():
                if operation_id not in seen:
                    raise ValueError(
                        f"overrides.yaml 中的 {operation_id} 在目录文件中不存在"
                    )

        return cls(operations)

    def get(self, operation_id: str) -> ApiOperation | None:
        return self._operations.get(operation_id)

    def require(self, operation_id: str) -> ApiOperation:
        operation = self.get(operation_id)
        if operation is None:
            raise KeyError(operation_id)
        return operation

    def all(self) -> list[ApiOperation]:
        return list(self._operations.values())

    def search(
        self,
        query: str,
        *,
        service: ServiceName | None = None,
        limit: int = 5,
    ) -> list[ApiOperation]:
        normalized = query.strip().lower()
        if not normalized:
            return []

        scored: list[tuple[int, ApiOperation]] = []
        for operation in self._operations.values():
            if not operation.enabled:
                continue
            if service is not None and operation.service != service:
                continue
            score = _score(operation, normalized)
            if score:
                scored.append((score, operation))

        scored.sort(
            key=lambda item: (
                -item[0],
                _RISK_ORDER[item[1].risk],
                item[1].id,
            )
        )
        return [operation for _, operation in scored[: max(1, min(limit, 10))]]

    def search_result(self, operation: ApiOperation) -> dict[str, Any]:
        return {
            "id": operation.id,
            "service": operation.service,
            "summary": operation.summary,
            "mode": operation.mode,
            "risk": operation.risk,
            "code_access": operation.code_access,
            "params": {
                key: _parameter_schema(parameter)
                for key, parameter in operation.params.items()
            },
        }


def _parameter_schema(parameter: ApiParameter) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "in": parameter.location,
        "type": parameter.type,
        "required": parameter.required,
    }
    if parameter.name:
        schema["name"] = parameter.name
    if parameter.description:
        schema["description"] = parameter.description
    if parameter.enum:
        schema["enum"] = parameter.enum
    if parameter.default is not None:
        schema["default"] = parameter.default
    return schema


def _score(operation: ApiOperation, query: str) -> int:
    operation_id = operation.id.lower()
    summary = operation.summary.lower()
    aliases = [alias.lower() for alias in operation.aliases]
    tags = [tag.lower() for tag in operation.tags]

    if operation_id == query:
        return 100
    if query in aliases:
        return 90
    if query in summary:
        return 50
    if query in tags:
        return 40
    if query in operation_id:
        return 30
    if any(query in alias for alias in aliases):
        return 20
    return 0


def _load_operation_file(path: Path) -> list[dict[str, Any]]:
    data = _read_yaml(path)
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError(f"{path.name} 必须是 operation 列表")
    return [dict(item) for item in data]


def _load_overrides(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = _read_yaml(path)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("overrides.yaml 必须是 id 到配置的映射")
    return {
        str(key): dict(value)
        for key, value in data.items()
        if isinstance(value, dict)
    }


def _read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"无法解析 {path.name}: {exc}") from exc


def _deep_merge(target: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value
