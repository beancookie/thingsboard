from app.agent.models import ACTION_MODELS
from app.agent.tools import (
    CATALOG_TOOL_SPECS,
    READ_TOOLS,
    TOOL_SPECS,
    WRITE_TOOLS,
)


def test_tool_names_are_unique() -> None:
    names = [tool["function"]["name"] for tool in TOOL_SPECS]

    assert len(names) == len(set(names))


def test_read_and_write_tools_are_declared() -> None:
    assert READ_TOOLS == {"list_tenants", "list_products", "list_devices"}
    assert WRITE_TOOLS == {
        "create_tenant",
        "create_tenant_admin",
        "create_product",
        "update_thing_model",
        "create_device",
        "create_user",
    }


def test_action_models_cover_all_tools() -> None:
    tool_names = {tool["function"]["name"] for tool in TOOL_SPECS}

    assert set(ACTION_MODELS) == tool_names


def test_catalog_tool_names_are_declared() -> None:
    names = [tool["function"]["name"] for tool in CATALOG_TOOL_SPECS]

    assert names == ["search_api_operations", "call_api_operation"]


def test_create_product_tool_accepts_tsl() -> None:
    tool = next(
        item for item in TOOL_SPECS
        if item["function"]["name"] == "create_product"
    )

    assert tool["function"]["parameters"]["properties"]["tsl"]["type"] == "object"


def test_tool_parameters_are_valid_object_schemas() -> None:
    for tool in TOOL_SPECS:
        parameters = tool["function"]["parameters"]
        assert parameters["type"] == "object"
        assert "properties" in parameters
        assert "required" in parameters
