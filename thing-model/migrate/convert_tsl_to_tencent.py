#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


TYPE_MAP = {"enum_string": "stringenum"}
RANGE_KEYS = ("min", "max", "start", "step")


def number_text(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(value, ".15g")
    return str(value)


def convert_define(define: Any) -> dict[str, Any]:
    if not isinstance(define, dict):
        return {}
    result: dict[str, Any] = {}
    type_name = define.get("type")
    if type_name is not None:
        result["type"] = TYPE_MAP.get(type_name, type_name)
    for key in RANGE_KEYS:
        if key in define and define[key] is not None:
            result[key] = number_text(define[key])
    if type_name == "string":
        result.setdefault("min", "0")
        result.setdefault("max", "2048")
    if type_name in ("int", "float"):
        result.setdefault("min", "0")
        result.setdefault("max", "99999999")
        result.setdefault("start", result["min"])
        result.setdefault("step", "1" if type_name == "int" else "0.01")
    if define.get("unit") is not None:
        result["unit"] = define["unit"]
    if define.get("mapping") is not None:
        result["mapping"] = define["mapping"]
    if type_name == "bool" and "mapping" not in result:
        result["mapping"] = {"0": "否", "1": "是"}
    specs = define.get("specs", define.get("fields"))
    if specs is not None:
        result["specs"] = convert_struct_fields(specs)
    return result


def convert_struct_fields(specs: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if isinstance(specs, dict):
        items = specs.items()
    elif isinstance(specs, list):
        items = (
            (item.get("id"), item)
            for item in specs
            if isinstance(item, dict) and item.get("id")
        )
    else:
        return result
    for field_id, field in items:
        if not isinstance(field, dict):
            continue
        item: dict[str, Any] = {
            "id": field_id,
            "name": field.get("name", field_id),
            "dataType": convert_define(field),
        }
        if field.get("desc"):
            item["desc"] = field["desc"]
        if "required" in field:
            item["required"] = field["required"]
        result.append(item)
    return result


def convert_property(prop: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("id", "name", "desc", "mode", "required"):
        if key in prop:
            result[key] = prop[key]
    result["define"] = convert_define(prop.get("define", {}))
    if "mapping" in prop:
        result["mapping"] = prop["mapping"]
    return result


def convert_param(param: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("id", "name", "desc"):
        if key in param:
            result[key] = param[key]
    result["define"] = convert_define(param.get("define", {}))
    return result


def convert_event(event: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("id", "name", "desc", "type"):
        if key in event:
            result[key] = event[key]
    result["params"] = [
        convert_param(param) for param in event.get("params", [])
    ]
    result["required"] = event.get("required", False)
    return result


def convert_action(action: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("id", "name", "desc"):
        if key in action:
            result[key] = action[key]
    for key in ("input", "output"):
        if key in action:
            result[key] = [
                convert_param(param) for param in action[key]
            ]
    return result


def convert_document(source: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise ValueError("TSL must be a JSON object")
    return {
        "version": source.get("version", "1.0"),
        "profile": source.get("profile", {}),
        "properties": [
            convert_property(prop) for prop in source.get("properties", [])
        ],
        "events": [
            convert_event(event) for event in source.get("events", [])
        ],
        "actions": [
            convert_action(action) for action in source.get("actions", [])
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert canonical thing-model TSL to Tencent IoT thing model format.")
    parser.add_argument("input", help="input canonical TSL JSON file")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="output file; defaults to <input>.tencent.json",
    )
    parser.add_argument("--indent", type=int, default=2, help="output indent")
    return parser.parse_args()


def default_output_path(input_path: Path) -> Path:
    name = input_path.name
    if name.endswith(".tsl.json"):
        return input_path.with_name(name[:-len(".tsl.json")] + ".tencent.json")
    return input_path.with_suffix(".tencent.json")


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = (
        Path(args.output)
        if args.output
        else default_output_path(input_path)
    )
    with input_path.open(encoding="utf-8") as stream:
        source = json.load(stream)
    converted = convert_document(source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(converted, stream, ensure_ascii=False, indent=args.indent)
        stream.write("\n")
    print(f"{input_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
