from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


AgentMode = Literal["chat", "execute"]
AgentActionStatus = Literal["PROPOSED", "EXECUTED", "FAILED"]
AgentActionRisk = Literal["low", "medium", "high"]
AgentAuthority = Literal["TENANT_ADMIN", "CUSTOMER_USER"]


class AgentFile(BaseModel):
    id: str
    name: str
    mime_type: str
    size: int


class AgentMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)
    files: list[AgentFile] = Field(default_factory=list)


class AgentContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    route: str | None = None
    product_id: str | None = None
    tenant_id: str | None = None


class AgentAction(BaseModel):
    id: str
    type: str
    summary: str = ""
    params: dict[str, Any] = Field(default_factory=dict)
    status: AgentActionStatus = "PROPOSED"
    risk: AgentActionRisk = "low"


class AgentChatRequest(BaseModel):
    mode: AgentMode = "chat"
    messages: list[AgentMessage] = Field(default_factory=list)
    tsl: Any | None = None
    files: list[AgentFile] = Field(default_factory=list)
    actions: list[AgentAction] = Field(default_factory=list)
    context: AgentContext | None = None


class AgentActionResult(BaseModel):
    action_id: str
    type: str
    success: bool
    message: str
    data: dict[str, Any] | None = None


class AgentChatResponse(BaseModel):
    reply: str
    actions: list[AgentAction] = Field(default_factory=list)
    executed: list[AgentActionResult] = Field(default_factory=list)


class CreateTenantArgs(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=1024)


class CreateTenantAdminArgs(BaseModel):
    tenant_id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None


class CreateProductArgs(BaseModel):
    product_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    model: str | None = Field(default=None, max_length=64)
    category_id: str | None = Field(default=None, max_length=64)
    tsl_version: str | None = Field(default=None, max_length=32)
    strict_unknown: bool = False


class CreateDeviceArgs(BaseModel):
    product_id: str = Field(min_length=1, max_length=64)
    device_name: str = Field(min_length=1, max_length=48)
    label: str | None = Field(default=None, max_length=255)
    site_code: str | None = Field(default=None, max_length=64)


class CreateUserArgs(BaseModel):
    tenant_id: str | None = None
    email: str
    authority: AgentAuthority = "CUSTOMER_USER"
    first_name: str | None = None
    last_name: str | None = None


class ListTenantsArgs(BaseModel):
    pass


class ListProductsArgs(BaseModel):
    keyword: str | None = None


class ListDevicesArgs(BaseModel):
    page_size: int = Field(default=100, ge=1, le=1000)
    page: int = Field(default=0, ge=0)


ACTION_MODELS = {
    "list_tenants": ListTenantsArgs,
    "create_tenant": CreateTenantArgs,
    "create_tenant_admin": CreateTenantAdminArgs,
    "create_product": CreateProductArgs,
    "create_device": CreateDeviceArgs,
    "create_user": CreateUserArgs,
    "list_products": ListProductsArgs,
    "list_devices": ListDevicesArgs,
}
