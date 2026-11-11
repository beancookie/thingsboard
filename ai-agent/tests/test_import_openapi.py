from scripts.import_openapi import convert_openapi, render_catalog


def _spec() -> dict:
    return {
        "paths": {
            "/api/tenants": {
                "get": {
                    "operationId": "listTenants",
                    "summary": "List tenants",
                    "tags": ["tenant"],
                    "parameters": [
                        {
                            "name": "pageSize",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"},
                        }
                    ],
                }
            },
            "/api/tenant/{tenantId}": {
                "delete": {
                    "operationId": "deleteTenant",
                    "summary": "Delete tenant",
                    "tags": ["tenant"],
                    "parameters": [
                        {
                            "name": "tenantId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                }
            },
            "/api/products": {
                "post": {
                    "operationId": "createProduct",
                    "summary": "Create product",
                    "tags": ["product"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["productId"],
                                    "properties": {
                                        "productId": {"type": "string"},
                                        "name": {"type": "string"},
                                        "enabled": {"type": "boolean", "default": True},
                                    },
                                }
                            }
                        },
                    },
                }
            },
            "/api/files": {
                "post": {
                    "operationId": "uploadFile",
                    "requestBody": {
                        "content": {"multipart/form-data": {"schema": {"type": "object"}}}
                    },
                }
            },
            "/api/auth/login": {
                "post": {"operationId": "login"}
            },
        }
    }


def test_convert_openapi_builds_catalog_entries() -> None:
    operations = {item["id"]: item for item in convert_openapi(_spec(), "thingsboard")}

    assert "thingsboard.listTenants" in operations
    assert "thingsboard.deleteTenant" in operations
    assert "thingsboard.createProduct" in operations
    assert "thingsboard.uploadFile" not in operations
    assert "thingsboard.login" not in operations

    tenants = operations["thingsboard.listTenants"]
    assert tenants["mode"] == "read"
    assert tenants["code_access"] == "read"
    assert tenants["permission"] == "SYS_ADMIN"
    assert tenants["risk"] == "low"
    assert tenants["params"]["pageSize"]["required"] is False

    delete = operations["thingsboard.deleteTenant"]
    assert delete["mode"] == "write"
    assert delete["risk"] == "high"
    assert delete["tenant_param"] == "tenantId"
    assert delete["params"]["tenantId"]["required"] is True

    product = operations["thingsboard.createProduct"]
    assert product["mode"] == "write"
    assert product["code_access"] == "write"
    assert product["params"]["productId"]["required"] is True
    assert product["params"]["name"]["required"] is False
    assert product["params"]["enabled"]["default"] is True


def test_render_catalog_applies_overrides() -> None:
    operations = convert_openapi(_spec(), "thingsboard")
    content = render_catalog(
        operations,
        {
            "thingsboard.listTenants": {
                "summary": "查询租户列表",
                "aliases": ["租户", "厂商"],
            }
        },
    )

    assert "summary: 查询租户列表" in content
    assert "aliases:\n  - 租户" in content
    assert "id: thingsboard.listTenants" in content
