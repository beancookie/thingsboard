import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.agent.api_catalog import ApiCatalog, ApiOperation
from app.agent.api_executor import ApiExecutor
from app.agent.models import (
    ACTION_MODELS,
    AgentAction,
    AgentActionResult,
    CreateDeviceArgs,
    CreateProductArgs,
    CreateTenantAdminArgs,
    CreateTenantArgs,
    CreateUserArgs,
    ListDevicesArgs,
    ListProductsArgs,
    UpdateThingModelArgs,
)
from app.auth.thingsboard import CurrentUser
from app.clients.thing_model import ThingModelClient
from app.clients.thingsboard import ThingsBoardClient
from app.common.errors import AgentError, AgentForbidden

logger = logging.getLogger(__name__)
DEVICE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,48}$")


class AgentActionExecutor:
    def __init__(
        self,
        thingsboard: ThingsBoardClient,
        thing_model: ThingModelClient,
        catalog: ApiCatalog | None = None,
        api_executor: ApiExecutor | None = None,
        max_tsl_bytes: int = 2_000_000,
    ):
        self._thingsboard = thingsboard
        self._thing_model = thing_model
        self._catalog = catalog
        self._api_executor = api_executor
        self._max_tsl_bytes = max(1, max_tsl_bytes)

    async def execute(
        self,
        action: AgentAction,
        user: CurrentUser,
        token: str,
        tsl: Any | None,
    ) -> AgentActionResult:
        operation = self._catalog.get(action.type) if self._catalog else None
        if operation is not None:
            return await self._execute_operation(action, operation, user, token, tsl)

        model = ACTION_MODELS.get(action.type)
        if model is None:
            return _failed(action, f"不支持的动作: {action.type}")
        try:
            params = model.model_validate(action.params)
            data = await self._dispatch(action.type, params, user, token, tsl)
            return AgentActionResult(
                action_id=action.id,
                type=action.type,
                success=True,
                message="执行成功",
                data=data,
            )
        except ValidationError as exc:
            return _failed(action, f"动作参数不合法: {exc.errors()}")
        except AgentError as exc:
            return _failed(action, exc.message)
        except Exception:
            logger.exception("Agent action failed: type=%s", action.type)
            return _failed(action, "执行失败，请查看服务日志")

    async def _execute_operation(
        self,
        action: AgentAction,
        operation: ApiOperation,
        user: CurrentUser,
        token: str,
        tsl: Any | None,
    ) -> AgentActionResult:
        if not operation.enabled:
            return _failed(action, f"接口未启用: {operation.id}")

        try:
            if operation.handler:
                model = ACTION_MODELS.get(operation.handler)
                if model is None:
                    return _failed(action, f"不支持的动作: {operation.handler}")
                params = model.model_validate(action.params)
                data = await self._dispatch(
                    operation.handler, params, user, token, tsl
                )
            else:
                if self._api_executor is None:
                    return _failed(action, "通用 API 执行器未初始化")
                data = await self._api_executor.execute(
                    operation, token, user, action.params
                )
            return AgentActionResult(
                action_id=action.id,
                type=action.type,
                success=True,
                message="执行成功",
                data=data,
            )
        except ValidationError as exc:
            return _failed(action, f"动作参数不合法: {exc.errors()}")
        except AgentError as exc:
            return _failed(action, exc.message)
        except Exception:
            logger.exception("Agent operation failed: type=%s", action.type)
            return _failed(action, "执行失败，请查看服务日志")

    async def _dispatch(
        self,
        action_type: str,
        params,
        user: CurrentUser,
        token: str,
        tsl: Any | None,
    ) -> dict[str, Any]:
        if action_type == "list_tenants":
            return await self._list_tenants(user, token)
        if action_type == "list_products":
            return await self._list_products(params, user, token)
        if action_type == "list_devices":
            return await self._list_devices(params, user, token)
        if action_type == "create_tenant":
            return await self._create_tenant(params, user, token)
        if action_type == "create_tenant_admin":
            return await self._create_tenant_admin(params, user, token)
        if action_type == "create_product":
            return await self._create_product(params, user, token, tsl)
        if action_type == "update_thing_model":
            return await self._update_thing_model(params, user, token, tsl)
        if action_type == "create_device":
            return await self._create_device(params, user, token)
        if action_type == "create_user":
            return await self._create_user(params, user, token)
        raise AgentError(f"不支持的动作: {action_type}")

    async def _list_tenants(self, user: CurrentUser, token: str) -> dict[str, Any]:
        _require_sys_admin(user)
        return await self._thingsboard.list_tenants(token)

    async def _list_products(
        self, params: ListProductsArgs, user: CurrentUser, token: str
    ) -> list[dict[str, Any]]:
        _require_tenant_admin(user)
        return await self._thing_model.list_products(token, params.keyword)

    async def _list_devices(
        self, params: ListDevicesArgs, user: CurrentUser, token: str
    ) -> dict[str, Any]:
        _require_tenant_admin(user)
        return await self._thingsboard.list_tenant_devices(
            token, params.page_size, params.page
        )

    async def _create_tenant(
        self, params: CreateTenantArgs, user: CurrentUser, token: str
    ) -> dict[str, Any]:
        _require_sys_admin(user)
        tenant = await self._thingsboard.create_tenant(
            token, params.title, params.description
        )
        tenant_id = _entity_id(tenant.get("id"))
        if not tenant_id:
            raise AgentError("ThingsBoard 未返回租户 ID", status_code=502)
        try:
            await self._thing_model.provision_auto(token, tenant_id)
            return {"tenantId": tenant_id, "provisioned": True}
        except AgentError as exc:
            return {
                "tenantId": tenant_id,
                "provisioned": False,
                "warning": exc.message,
            }

    async def _create_tenant_admin(
        self, params: CreateTenantAdminArgs, user: CurrentUser, token: str
    ) -> dict[str, Any]:
        _require_sys_admin(user)
        created = await self._thingsboard.create_user(
            token,
            tenant_id=params.tenant_id,
            email=params.email,
            authority="TENANT_ADMIN",
            first_name=params.first_name,
            last_name=params.last_name,
        )
        return {"userId": _entity_id(created.get("id")), "email": params.email}

    async def _create_product(
        self,
        params: CreateProductArgs,
        user: CurrentUser,
        token: str,
        tsl: Any | None,
    ) -> dict[str, Any]:
        _require_tenant_admin(user)
        tsl_source: Any = params.tsl if params.tsl is not None else tsl
        if tsl_source is None:
            tsl_source = {
                "version": "1.0",
                "profile": {"ProductId": params.product_id},
                "properties": [],
            }
        if not isinstance(tsl_source, dict):
            raise AgentError("物模型 TSL 必须是 JSON 对象")

        tsl_source = dict(tsl_source)
        tsl_source.setdefault("version", "1.0")
        profile = tsl_source.get("profile")
        profile = dict(profile) if isinstance(profile, dict) else {}
        product_id = profile.get("ProductId", profile.get("productId"))
        if product_id is None:
            profile["ProductId"] = params.product_id
        elif str(product_id) != params.product_id:
            raise AgentError("物模型 TSL 的 ProductId 与产品 ID 不一致")
        tsl_source["profile"] = profile
        tsl_source.setdefault("properties", [])
        if not isinstance(tsl_source["properties"], list):
            raise AgentError("物模型 TSL 的 properties 必须是数组")

        size = len(json.dumps(tsl_source, ensure_ascii=False).encode("utf-8"))
        if size > self._max_tsl_bytes:
            raise AgentError(
                f"物模型 TSL 不能超过 {self._max_tsl_bytes} 字节"
            )

        body: dict[str, Any] = {
            "productId": params.product_id,
            "name": params.name,
            "tsl": tsl_source,
            "strictUnknown": params.strict_unknown,
        }
        if params.model is not None:
            body["model"] = params.model
        if params.category_id is not None:
            body["categoryId"] = params.category_id
        if params.tsl_version is not None:
            body["tslVersion"] = params.tsl_version
        result = await self._thing_model.create_product(token, body)
        return {
            "productId": result.get("productId", params.product_id),
            "tbProfileId": result.get("tbProfileId"),
            "tbAssetId": result.get("tbAssetId"),
            "tbRuleChainId": result.get("tbRuleChainId"),
            "status": result.get("status"),
        }

    async def _update_thing_model(
        self,
        params: UpdateThingModelArgs,
        user: CurrentUser,
        token: str,
        tsl: Any | None,
    ) -> dict[str, Any]:
        _require_tenant_admin(user)
        tsl_source: Any = params.tsl if params.tsl is not None else tsl
        if tsl_source is None:
            raise AgentError("缺少物模型 TSL：请生成完整 TSL 后传入 tsl 参数")
        if not isinstance(tsl_source, dict):
            raise AgentError("物模型 TSL 必须是 JSON 对象")

        tsl_source = dict(tsl_source)
        if params.tsl_version is not None:
            tsl_source.setdefault("version", params.tsl_version)
        else:
            tsl_source.setdefault("version", "1.0")

        profile = tsl_source.get("profile")
        profile = dict(profile) if isinstance(profile, dict) else {}
        product_id = profile.get("ProductId", profile.get("productId"))
        if product_id is None:
            profile["ProductId"] = params.product_id
        elif str(product_id) != params.product_id:
            raise AgentError("物模型 TSL 的 ProductId 与产品 ID 不一致")
        tsl_source["profile"] = profile

        properties = tsl_source.setdefault("properties", [])
        if not isinstance(properties, list):
            raise AgentError("物模型 TSL 的 properties 必须是数组")

        size = len(json.dumps(tsl_source, ensure_ascii=False).encode("utf-8"))
        if size > self._max_tsl_bytes:
            raise AgentError(f"物模型 TSL 不能超过 {self._max_tsl_bytes} 字节")

        body: dict[str, Any] = {
            "tsl": tsl_source,
            "strictUnknown": params.strict_unknown,
        }
        if params.tsl_version is not None:
            body["tslVersion"] = params.tsl_version
        result = await self._thing_model.update_thing_model(
            token, params.product_id, body
        )
        return {
            "productId": result.get("productId", params.product_id),
            "tslVersion": result.get("tslVersion", params.tsl_version),
            "tbProfileId": result.get("tbProfileId"),
            "tbAssetId": result.get("tbAssetId"),
            "tbRuleChainId": result.get("tbRuleChainId"),
            "status": result.get("status"),
        }

    async def _create_device(
        self, params: CreateDeviceArgs, user: CurrentUser, token: str
    ) -> dict[str, Any]:
        _require_tenant_admin(user)
        if not DEVICE_NAME_PATTERN.fullmatch(params.device_name):
            raise AgentError("设备名称只能包含英文、数字和下划线，最长 48 个字符")
        product_detail = await self._thing_model.get_product(token, params.product_id)
        product = product_detail.get("product", product_detail)
        profile_id = product.get("tbProfileId")
        if not profile_id:
            raise AgentError("产品尚未同步设备配置，请先完成产品同步")
        device = await self._thingsboard.create_device(
            token,
            name=params.device_name,
            device_profile_id=profile_id,
            label=params.label,
        )
        device_id = _entity_id(device.get("id"))
        if device_id:
            attributes = {
                "product_id": params.product_id,
                "tsl_version": product.get("tslVersion"),
            }
            if params.site_code:
                attributes["site_code"] = params.site_code
            await self._thingsboard.save_device_attributes(token, device_id, attributes)
        return {"deviceId": device_id, "deviceName": params.device_name}

    async def _create_user(
        self, params: CreateUserArgs, user: CurrentUser, token: str
    ) -> dict[str, Any]:
        tenant_id = _resolve_tenant(user, params.tenant_id)
        if params.authority == "TENANT_ADMIN" and not user.is_sys_admin:
            raise AgentForbidden("只有 SYS_ADMIN 可以创建租户管理员")
        created = await self._thingsboard.create_user(
            token,
            tenant_id=tenant_id,
            email=params.email,
            authority=params.authority,
            first_name=params.first_name,
            last_name=params.last_name,
        )
        return {"userId": _entity_id(created.get("id")), "email": params.email}


def _resolve_tenant(user: CurrentUser, requested_tenant_id: str | None) -> str:
    if user.is_sys_admin:
        if not requested_tenant_id:
            raise AgentError("SYS_ADMIN 创建用户时必须指定 tenantId")
        return requested_tenant_id
    if not user.tenant_id:
        raise AgentForbidden("当前用户不属于任何租户")
    if requested_tenant_id and requested_tenant_id != user.tenant_id:
        raise AgentForbidden("不能操作其他租户")
    return user.tenant_id


def _require_sys_admin(user: CurrentUser) -> None:
    if not user.is_sys_admin:
        raise AgentForbidden("只有 SYS_ADMIN 可以执行该操作")


def _require_tenant_admin(user: CurrentUser) -> None:
    if not user.is_tenant_admin:
        raise AgentForbidden("只有 TENANT_ADMIN 可以执行该操作")


def _entity_id(value: Any) -> str | None:
    if isinstance(value, dict):
        entity_id = value.get("id")
        return str(entity_id) if entity_id else None
    return str(value) if value else None


def _failed(action: AgentAction, message: str) -> AgentActionResult:
    return AgentActionResult(
        action_id=action.id,
        type=action.type,
        success=False,
        message=message,
    )
