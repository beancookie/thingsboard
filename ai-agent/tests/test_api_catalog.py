from pathlib import Path

import pytest

from app.agent.api_catalog import ApiCatalog


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_loads_catalog_and_overrides(tmp_path: Path) -> None:
    _write(
        tmp_path / "thingsboard.yaml",
        """
- id: thingsboard.listTenants
  service: thingsboard
  method: GET
  path: /api/tenants
  summary: 查询租户列表
  aliases: [租户]
  tags: [tenant]
  mode: read
  code_access: read
  permission: SYS_ADMIN
  params:
    pageSize:
      in: query
      type: integer
      default: 100
""",
    )
    _write(
        tmp_path / "overrides.yaml",
        """
thingsboard.listTenants:
  summary: 查询所有厂商
  aliases: [厂商, tenant]
""",
    )

    catalog = ApiCatalog.load(tmp_path)
    operation = catalog.require("thingsboard.listTenants")

    assert operation.summary == "查询所有厂商"
    assert operation.aliases == ["厂商", "tenant"]
    assert catalog.search("厂商")[0].id == "thingsboard.listTenants"


def test_rejects_duplicate_operation_ids(tmp_path: Path) -> None:
    content = """
- id: thingsboard.same
  service: thingsboard
  method: GET
  path: /api/a
  summary: A
  mode: read
- id: thingsboard.same
  service: thingsboard
  method: GET
  path: /api/b
  summary: B
  mode: read
"""
    _write(tmp_path / "a.yaml", content)

    with pytest.raises(ValueError, match="重复的 operation id"):
        ApiCatalog.load(tmp_path)


def test_rejects_undeclared_path_parameter(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.yaml",
        """
- id: thingsboard.get
  service: thingsboard
  method: GET
  path: /api/tenants/{tenantId}
  summary: 查询租户
  mode: read
""",
    )

    with pytest.raises(ValueError, match="path 参数未在 params 中声明"):
        ApiCatalog.load(tmp_path)


def test_real_catalog_loads() -> None:
    root = Path(__file__).resolve().parents[1] / "config" / "api"
    catalog = ApiCatalog.load(root)

    assert catalog.get("thingsboard.listTenants") is not None
    assert catalog.get("thing_model.listProducts") is not None
    assert catalog.get("thing_model.createProduct").handler == "create_product"
    update = catalog.require("thing_model.updateThingModel")
    assert update.handler == "update_thing_model"
    assert update.enabled is True
    assert update.params["tsl"].required is True

    assert catalog.get("thing_model.put.products_by_productid_thing_model") is None
    assert catalog.search("更新物模型")[0].id == "thing_model.updateThingModel"
