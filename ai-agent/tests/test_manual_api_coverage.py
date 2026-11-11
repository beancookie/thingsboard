from pathlib import Path

import yaml

from app.agent.api_catalog import ApiCatalog
from scripts.import_manual_apis import (
    build_manual_operations,
    extract_manual_endpoints,
    normalize_endpoint,
)


def _paths() -> tuple[Path, Path, Path]:
    root = Path(__file__).resolve().parents[2]
    return (
        root / "docs" / "manuals",
        root / "ai-agent" / "config" / "api",
        root / "ai-agent" / "config" / "api" / "manual_apis.yaml",
    )


def test_all_manual_apis_are_in_catalog() -> None:
    manuals, catalog_dir, _ = _paths()
    catalog = ApiCatalog.load(catalog_dir)
    keys = {
        (operation.service, operation.method, operation.path)
        for operation in catalog.all()
    }

    missing: list[str] = []
    for endpoint in extract_manual_endpoints(manuals):
        service, method, path = normalize_endpoint(endpoint.method, endpoint.path)
        if (service, method, path) not in keys:
            missing.append(f"{method} {service}:{path} ({endpoint.source})")

    assert not missing, "\n".join(missing)


def test_manual_catalog_is_current() -> None:
    manuals, catalog_dir, output = _paths()
    operations = build_manual_operations(manuals, catalog_dir)
    generated = yaml.safe_dump(
        operations,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )

    assert output.read_text(encoding="utf-8") == generated


def test_telemetry_and_device_name_operations_exist() -> None:
    _, catalog_dir, _ = _paths()
    catalog = ApiCatalog.load(catalog_dir)

    telemetry = catalog.search("遥测", limit=10)
    assert any(
        "/plugins/telemetry/" in operation.path for operation in telemetry
    )

    device = catalog.require("thingsboard.listTenantDevices")
    assert "deviceName" in device.params
