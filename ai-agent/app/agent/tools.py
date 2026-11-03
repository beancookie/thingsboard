from typing import Any


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


TOOL_SPECS: list[dict[str, Any]] = [
    _tool(
        "list_tenants",
        "查询平台租户列表，仅 SYS_ADMIN 可用。",
        {},
        [],
    ),
    _tool(
        "list_products",
        "查询当前租户的产品列表。",
        {"keyword": {"type": "string", "description": "产品 ID 或名称关键字"}},
        [],
    ),
    _tool(
        "list_devices",
        "查询当前租户的设备列表。",
        {
            "page_size": {"type": "integer", "minimum": 1, "maximum": 1000},
            "page": {"type": "integer", "minimum": 0},
        },
        [],
    ),
    _tool(
        "create_tenant",
        "创建厂商租户。创建后平台会初始化厂商服务账号。",
        {
            "title": {"type": "string", "description": "租户名称"},
            "description": {"type": "string", "description": "租户说明"},
        },
        ["title"],
    ),
    _tool(
        "create_tenant_admin",
        "为指定租户创建可登录的租户管理员，并发送激活邮件。",
        {
            "tenant_id": {"type": "string", "description": "租户 UUID"},
            "email": {"type": "string", "description": "管理员邮箱"},
            "first_name": {"type": "string"},
            "last_name": {"type": "string"},
        },
        ["tenant_id", "email"],
    ),
    _tool(
        "create_product",
        "使用本次请求附带的 TSL 创建产品，并自动同步 ThingsBoard。TENANT_ADMIN 只能操作本租户。",
        {
            "product_id": {"type": "string", "description": "产品 ID，租户内唯一"},
            "name": {"type": "string", "description": "产品名称"},
            "model": {"type": "string", "description": "产品型号"},
            "category_id": {"type": "string", "description": "产品分类"},
            "tsl_version": {"type": "string", "description": "TSL 版本"},
            "strict_unknown": {"type": "boolean", "description": "是否拒绝未知字段"},
        },
        ["product_id", "name"],
    ),
    _tool(
        "create_device",
        "在当前租户下创建设备，并绑定产品对应的设备配置。",
        {
            "product_id": {"type": "string", "description": "产品 ID"},
            "device_name": {"type": "string", "description": "设备名称，英文数字下划线"},
            "label": {"type": "string", "description": "设备中文别名"},
            "site_code": {"type": "string", "description": "工点编码"},
        },
        ["product_id", "device_name"],
    ),
    _tool(
        "create_user",
        "在租户下创建用户并发送激活邮件。",
        {
            "tenant_id": {"type": "string", "description": "租户 UUID；TENANT_ADMIN 可省略"},
            "email": {"type": "string", "description": "用户邮箱"},
            "authority": {
                "type": "string",
                "enum": ["TENANT_ADMIN", "CUSTOMER_USER"],
                "description": "用户角色",
            },
            "first_name": {"type": "string"},
            "last_name": {"type": "string"},
        },
        ["email"],
    ),
]

READ_TOOLS = {"list_tenants", "list_products", "list_devices"}
WRITE_TOOLS = {
    "create_tenant",
    "create_tenant_admin",
    "create_product",
    "create_device",
    "create_user",
}

TOOL_SUMMARIES = {
    "create_tenant": "创建租户",
    "create_tenant_admin": "创建租户管理员",
    "create_product": "创建产品",
    "create_device": "创建设备",
    "create_user": "创建用户",
    "list_tenants": "查询租户",
    "list_products": "查询产品",
    "list_devices": "查询设备",
}
