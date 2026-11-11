from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agent.api_catalog import ApiOperation, ApiParameter
from app.auth.thingsboard import CurrentUser
from app.clients.thing_model import ThingModelClient
from app.clients.thingsboard import ThingsBoardClient
from app.common.errors import AgentError, AgentForbidden


@dataclass(frozen=True)
class PreparedRequest:
    path: str
    query: dict[str, Any]
    body: Any | None


class ApiExecutor:
    def __init__(
        self,
        thingsboard: ThingsBoardClient,
        thing_model: ThingModelClient,
    ):
        self._thingsboard = thingsboard
        self._thing_model = thing_model

    def prepare(
        self,
        operation: ApiOperation,
        params: dict[str, Any],
        user: CurrentUser,
    ) -> PreparedRequest:
        if not operation.enabled:
            raise AgentError(
                f"接口未启用: {operation.id}",
                status_code=403,
                code="API_DISABLED",
            )

        check_permission(operation, user)
        values = dict(params or {})
        _apply_tenant_scope(operation, values, user)
        _reject_unknown_params(operation, values)

        path = operation.path
        query: dict[str, Any] = {}
        body: dict[str, Any] = {}
        raw_body: Any | None = None

        for key, parameter in operation.params.items():
            if key in values:
                value = values[key]
            elif parameter.default is not None:
                value = parameter.default
            elif parameter.required:
                raise AgentError(
                    f"缺少参数: {key}",
                    status_code=400,
                    code="API_PARAMETER_REQUIRED",
                )
            else:
                continue

            _validate_value(key, parameter, value)

            if parameter.location == "path":
                path = path.replace(f"{{{key}}}", str(value))
            elif parameter.location == "query":
                query[parameter.name or key] = value
            elif key == "$body":
                raw_body = value
            else:
                body[parameter.name or key] = value

        if raw_body is not None and body:
            raise AgentError(
                f"接口 {operation.id} 不能同时使用 $body 和普通 body 参数",
                status_code=500,
                code="API_CATALOG_INVALID",
            )

        request_body: Any | None = raw_body if raw_body is not None else (body or None)
        return PreparedRequest(path=path, query=query, body=request_body)

    async def execute(
        self,
        operation: ApiOperation,
        token: str,
        user: CurrentUser,
        params: dict[str, Any],
    ) -> Any:
        prepared = self.prepare(operation, params, user)
        client = (
            self._thingsboard
            if operation.service == "thingsboard"
            else self._thing_model
        )
        return await client.request(
            operation.method,
            prepared.path,
            token,
            params=prepared.query or None,
            json=prepared.body,
        )


def check_permission(operation: ApiOperation, user: CurrentUser) -> None:
    if operation.permission == "SYS_ADMIN" and not user.is_sys_admin:
        raise AgentForbidden("只有 SYS_ADMIN 可以执行该操作")
    if operation.permission == "TENANT_ADMIN" and not user.is_tenant_admin:
        raise AgentForbidden("只有 TENANT_ADMIN 可以执行该操作")


def _apply_tenant_scope(
    operation: ApiOperation,
    values: dict[str, Any],
    user: CurrentUser,
) -> None:
    tenant_param = operation.tenant_param
    if not tenant_param:
        return

    parameter = operation.params.get(tenant_param)
    if parameter is None:
        raise AgentError(
            f"接口 {operation.id} 的 tenant_param 未在 params 中声明",
            status_code=500,
            code="API_CATALOG_INVALID",
        )

    if user.is_sys_admin:
        return
    if not user.tenant_id:
        raise AgentForbidden("当前用户不属于任何租户")

    requested = values.get(tenant_param)
    if requested is None:
        values[tenant_param] = user.tenant_id
        return
    if str(requested) != str(user.tenant_id):
        raise AgentForbidden("不能操作其他租户")


def _reject_unknown_params(operation: ApiOperation, values: dict[str, Any]) -> None:
    unknown = set(values) - set(operation.params)
    if unknown:
        raise AgentError(
            f"未知参数: {', '.join(sorted(unknown))}",
            status_code=400,
            code="API_PARAMETER_UNKNOWN",
        )


def _validate_value(key: str, parameter: ApiParameter, value: Any) -> None:
    if value is None:
        if parameter.required:
            raise AgentError(
                f"参数不能为空: {key}",
                status_code=400,
                code="API_PARAMETER_INVALID",
            )
        return

    if parameter.enum is not None and value not in parameter.enum:
        raise AgentError(
            f"参数 {key} 必须是 {parameter.enum} 之一",
            status_code=400,
            code="API_PARAMETER_INVALID",
        )

    expected = parameter.type
    if expected == "integer":
        valid = isinstance(value, int) and not isinstance(value, bool)
    elif expected == "number":
        valid = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif expected == "boolean":
        valid = isinstance(value, bool)
    elif expected == "array":
        valid = isinstance(value, list)
    elif expected == "object":
        valid = isinstance(value, dict)
    elif expected == "string":
        valid = isinstance(value, str)
    else:
        valid = True

    if not valid:
        raise AgentError(
            f"参数 {key} 类型应为 {expected}",
            status_code=400,
            code="API_PARAMETER_INVALID",
        )
