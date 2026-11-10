#!/usr/bin/env python3
"""物模型 TSL 校验工具示例。

按中国中铁物联网平台《物模型定义规范使用手册》校验一个或多个 TSL 文件，
输出错误和警告，并可选生成 JSON 报告。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger("tsl-validator")

ID_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,49}$")
SUPPORTED_TYPES = {
    "int",
    "float",
    "bool",
    "string",
    "enum",
    "enum_string",
    "timestamp",
    "struct",
}
NUMERIC_TYPES = {"int", "float"}
EVENT_TYPES = {"info", "alert", "fault"}
RESERVED_IDS = {"ts", "event_id", "event_type", "event_ts"}
MAX_FEATURES = 100
INT32_MIN = -(2 ** 31)
INT32_MAX = 2 ** 31 - 1


@dataclass
class Issue:
    level: str
    path: str
    message: str


@dataclass
class FileResult:
    path: str
    valid: bool = True
    issues: List[Issue] = field(default_factory=list)

    @property
    def errors(self) -> List[Issue]:
        return [issue for issue in self.issues if issue.level == "error"]

    @property
    def warnings(self) -> List[Issue]:
        return [issue for issue in self.issues if issue.level == "warning"]


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )


class TslValidator:
    def __init__(self, strict: bool = False) -> None:
        self.strict = strict
        self.issues: List[Issue] = []

    def error(self, path: str, message: str) -> None:
        self.issues.append(Issue("error", path, message))

    def warning(self, path: str, message: str) -> None:
        self.issues.append(Issue("warning", path, message))

    def validate(self, tsl: Any) -> List[Issue]:
        self.issues = []
        if not isinstance(tsl, dict):
            self.error("$", "TSL 根节点必须是 JSON 对象")
            return self.issues

        self._check_version(tsl)
        self._check_profile(tsl)
        properties = self._check_list(tsl, "properties")
        events = self._check_list(tsl, "events")
        actions = self._check_list(tsl, "actions")

        self._check_properties(properties)
        self._check_events(events)
        self._check_actions(actions)

        total = len(properties) + len(events) + len(actions)
        if total > MAX_FEATURES:
            self.error(
                "$",
                f"属性、事件、行为总数 {total} 超过上限 {MAX_FEATURES}",
            )
        return self.issues

    def _check_version(self, tsl: Dict[str, Any]) -> None:
        version = tsl.get("version")
        if not isinstance(version, str) or not version.strip():
            self.error("$.version", "version 必须是非空字符串")
        elif len(version) > 32:
            self.error("$.version", "version 长度不能超过 32")

    def _check_profile(self, tsl: Dict[str, Any]) -> None:
        profile = tsl.get("profile")
        if not isinstance(profile, dict):
            self.error("$.profile", "profile 必须是 JSON 对象")
            return
        product_id = profile.get("ProductId") or profile.get("productId")
        if not isinstance(product_id, str) or not product_id.strip():
            self.error(
                "$.profile",
                "profile.ProductId 或 profile.productId 不能为空")

    def _check_list(
            self, tsl: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
        value = tsl.get(key)
        if value is None:
            if key == "properties":
                self.error("$", "properties 必须存在（可以是空数组）")
            return []
        if not isinstance(value, list):
            self.error(f"$.{key}", f"{key} 必须是数组")
            return []
        items = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                self.error(f"$.{key}[{index}]", "条目必须是 JSON 对象")
                continue
            items.append(item)
        return items

    def _check_properties(self, properties: List[Dict[str, Any]]) -> None:
        seen = set()
        for index, prop in enumerate(properties):
            path = f"$.properties[{index}]"
            self._check_id(prop, path, "属性")
            feature_id = prop.get("id")
            if isinstance(feature_id, str):
                if feature_id in seen:
                    self.error(path, f"属性 id 重复: {feature_id}")
                seen.add(feature_id)
                if feature_id in RESERVED_IDS:
                    self.warning(
                        path,
                        f"属性 id 使用了保留字段: {feature_id}",
                    )

            name = prop.get("name")
            if not isinstance(name, str) or not name.strip():
                self.error(path, "属性 name 不能为空")

            mode = prop.get("mode")
            if mode not in ("r", "rw"):
                self.error(path, "属性 mode 必须是 r 或 rw")

            if "mapping" in prop:
                self.warning(path, "属性级 mapping 建议移到 define.mapping")

            self._check_define(prop.get("define"), f"{path}.define")
            self._check_legacy_fields(prop, path)

    def _check_events(self, events: List[Dict[str, Any]]) -> None:
        seen = set()
        for index, event in enumerate(events):
            path = f"$.events[{index}]"
            self._check_id(event, path, "事件")
            event_id = event.get("id")
            if isinstance(event_id, str):
                if event_id in seen:
                    self.error(path, f"事件 id 重复: {event_id}")
                seen.add(event_id)

            name = event.get("name")
            if not isinstance(name, str) or not name.strip():
                self.error(path, "事件 name 不能为空")

            event_type = event.get("type")
            if event_type not in EVENT_TYPES:
                self.error(
                    path,
                    f"事件 type 必须是 info、alert 或 fault，当前为 {event_type!r}",
                )

            params = event.get("params")
            if params is not None:
                self._check_params(params, f"{path}.params", allow_struct=False)
            self._check_legacy_fields(event, path)

    def _check_actions(self, actions: List[Dict[str, Any]]) -> None:
        seen = set()
        for index, action in enumerate(actions):
            path = f"$.actions[{index}]"
            self._check_id(action, path, "行为")
            action_id = action.get("id")
            if isinstance(action_id, str):
                if action_id in seen:
                    self.error(path, f"行为 id 重复: {action_id}")
                seen.add(action_id)

            name = action.get("name")
            if not isinstance(name, str) or not name.strip():
                self.error(path, "行为 name 不能为空")

            for key in ("input", "output"):
                params = action.get(key)
                if params is not None:
                    self._check_params(
                        params, f"{path}.{key}", allow_struct=True)

    def _check_params(
            self,
            params: Any,
            path: str,
            allow_struct: bool) -> None:
        if not isinstance(params, list):
            self.error(path, "参数列表必须是数组")
            return
        seen = set()
        for index, param in enumerate(params):
            param_path = f"{path}[{index}]"
            if not isinstance(param, dict):
                self.error(param_path, "参数必须是 JSON 对象")
                continue
            self._check_id(param, param_path, "参数")
            param_id = param.get("id")
            if isinstance(param_id, str):
                if param_id in seen:
                    self.error(param_path, f"参数 id 重复: {param_id}")
                seen.add(param_id)

            name = param.get("name")
            if not isinstance(name, str) or not name.strip():
                self.error(param_path, "参数 name 不能为空")

            define = param.get("define")
            self._check_define(
                define, f"{param_path}.define", allow_struct=allow_struct)
            self._check_legacy_fields(param, param_path)

    def _check_define(
            self,
            define: Any,
            path: str,
            allow_struct: bool = True) -> None:
        if not isinstance(define, dict):
            self.error(path, "define 必须是 JSON 对象")
            return

        data_type = define.get("type")
        if not isinstance(data_type, str) or not data_type:
            self.error(path, "define.type 不能为空")
            return
        if data_type not in SUPPORTED_TYPES:
            self.error(path, f"不支持的数据类型: {data_type}")
            return

        if data_type == "struct":
            if not allow_struct:
                self.error(path, "此处不允许使用 struct")
                return
            self._check_struct(define, path)
            return

        if data_type in NUMERIC_TYPES:
            self._check_numeric(define, path, data_type)
        elif data_type in ("enum", "enum_string"):
            self._check_enum(define, path, data_type)
        else:
            for key in ("min", "max", "start", "step"):
                if key in define:
                    self.warning(path, f"非数值类型不应配置 {key}")

        if data_type not in ("enum", "enum_string") and "mapping" in define:
            self.warning(path, "非枚举类型不建议配置 mapping")

    def _check_numeric(
            self, define: Dict[str, Any], path: str, data_type: str) -> None:
        minimum = self._number(define.get("min"), path, "min")
        maximum = self._number(define.get("max"), path, "max")
        start = self._number(define.get("start"), path, "start")
        step = self._number(define.get("step"), path, "step")

        if minimum is not None and maximum is not None and minimum > maximum:
            self.error(path, f"min ({minimum}) 不能大于 max ({maximum})")
        if (start is not None and minimum is not None and start < minimum):
            self.error(path, f"start ({start}) 不能小于 min ({minimum})")
        if (start is not None and maximum is not None and start > maximum):
            self.error(path, f"start ({start}) 不能大于 max ({maximum})")
        if step is not None and step < 0:
            self.error(path, "step 不能为负数")

        if data_type == "int":
            for key, value in (
                    ("min", minimum), ("max", maximum), ("start", start)):
                if value is None:
                    continue
                if value < INT32_MIN or value > INT32_MAX:
                    self.error(
                        path,
                        f"{key} ({value}) 超出 int32 范围",
                    )
            for key in ("min", "max", "start"):
                value = define.get(key)
                if isinstance(value, float) and not value.is_integer():
                    self.warning(path, f"int 类型的 {key} 不是整数")

    def _check_enum(
            self, define: Dict[str, Any], path: str, data_type: str) -> None:
        mapping = define.get("mapping")
        if not isinstance(mapping, dict) or len(mapping) < 2:
            self.error(path, "enum/enum_string 的 mapping 至少需要 2 项")
            return
        if data_type == "enum":
            for key in mapping:
                if not str(key).lstrip("-").isdigit():
                    self.error(path, f"enum 的 mapping 键必须是数字: {key!r}")

    def _check_struct(self, define: Dict[str, Any], path: str) -> None:
        specs = define.get("specs")
        if isinstance(specs, list):
            self.warning(path, "specs 建议使用对象写法")
            specs = {
                str(item.get("id")): item
                for item in specs
                if isinstance(item, dict) and item.get("id")
            }
        if not isinstance(specs, dict) or not specs:
            self.error(path, "struct 的 specs 不能为空")
            return
        for key, spec in specs.items():
            spec_path = f"{path}.specs.{key}"
            if not isinstance(spec, dict):
                self.error(spec_path, "结构体字段必须是 JSON 对象")
                continue
            legacy = spec.get("dataType")
            if isinstance(legacy, dict):
                legacy_type = legacy.get("type")
            elif isinstance(legacy, str):
                legacy_type = legacy
            else:
                legacy_type = None
            field_type = spec.get("type") or legacy_type
            if field_type == "struct":
                self.error(spec_path, "结构体字段不能再次使用 struct")
                continue
            if field_type is None:
                self.error(spec_path, "结构体字段缺少 type")
                continue
            field_define = dict(spec)
            field_define["type"] = field_type
            self._check_define(field_define, spec_path, allow_struct=False)

    def _check_legacy_fields(
            self, item: Dict[str, Any], path: str) -> None:
        if "dataType" in item:
            self.warning(
                path,
                "检测到旧版 dataType，请转换为 define.type 后重新校验",
            )
        define = item.get("define")
        if isinstance(define, dict) and define.get("type") == "stringenum":
            self.warning(path, "stringenum 建议转换为 enum_string")

    def _check_id(
            self, item: Dict[str, Any], path: str, label: str) -> None:
        value = item.get("id")
        if not isinstance(value, str) or not value.strip():
            self.error(path, f"{label} id 不能为空")
            return
        if not ID_PATTERN.match(value):
            self.error(
                path,
                f"{label} id 不符合 ^[A-Za-z_][A-Za-z0-9_]{{0,49}}$: {value!r}",
            )

    def _number(
            self, value: Any, path: str, key: str) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            self.error(path, f"{key} 必须是数字")
            return None
        return float(value)


def collect_files(args: argparse.Namespace) -> List[Path]:
    files: List[Path] = []
    for value in args.tsl:
        files.append(Path(value))
    for value in args.dir:
        directory = Path(value)
        if not directory.is_dir():
            raise RuntimeError(f"目录不存在: {directory}")
        files.extend(sorted(directory.glob("*.json")))
    unique: List[Path] = []
    seen = set()
    for path in files:
        key = str(path.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def validate_file(path: Path, strict: bool) -> FileResult:
    result = FileResult(path=str(path))
    try:
        with path.open(encoding="utf-8-sig") as stream:
            tsl = json.load(stream)
    except FileNotFoundError:
        result.issues.append(Issue("error", "$", f"文件不存在: {path}"))
        result.valid = False
        return result
    except json.JSONDecodeError as exc:
        result.issues.append(
            Issue("error", "$", f"JSON 解析失败: {exc}"))
        result.valid = False
        return result

    validator = TslValidator(strict=strict)
    result.issues = validator.validate(tsl)
    has_error = any(issue.level == "error" for issue in result.issues)
    has_warning = any(issue.level == "warning" for issue in result.issues)
    result.valid = not has_error and not (strict and has_warning)
    return result


def write_report(path: Path, results: List[FileResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "valid": all(result.valid for result in results),
        "files": [
            {
                "path": result.path,
                "valid": result.valid,
                "errors": [
                    {"path": issue.path, "message": issue.message}
                    for issue in result.errors
                ],
                "warnings": [
                    {"path": issue.path, "message": issue.message}
                    for issue in result.warnings
                ],
            }
            for result in results
        ],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="按物模型定义规范校验 TSL JSON 文件。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    inputs = parser.add_argument_group("输入")
    inputs.add_argument(
        "--tsl",
        action="append",
        default=[],
        metavar="FILE",
        help="要校验的 TSL 文件，可重复",
    )
    inputs.add_argument(
        "--dir",
        action="append",
        default=[],
        metavar="DIR",
        help="批量校验目录下的 *.json 文件，可重复",
    )

    behavior = parser.add_argument_group("行为")
    behavior.add_argument(
        "--strict",
        action="store_true",
        help="将警告也视为校验失败",
    )

    output = parser.add_argument_group("输出")
    output.add_argument(
        "--report",
        default=None,
        help="JSON 报告输出路径",
    )
    output.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)

    try:
        files = collect_files(args)
    except RuntimeError as exc:
        parser.error(str(exc))
    if not files:
        parser.error("请通过 --tsl 或 --dir 指定至少一个文件")

    results: List[FileResult] = []
    for path in files:
        result = validate_file(path, args.strict)
        results.append(result)
        status = "OK" if result.valid else "FAIL"
        print(
            f"[{status}] {path} "
            f"errors={len(result.errors)} warnings={len(result.warnings)}")
        for issue in result.errors:
            print(f"  error {issue.path}: {issue.message}")
        for issue in result.warnings:
            print(f"  warning {issue.path}: {issue.message}")

    if args.report:
        write_report(Path(args.report), results)
        print(f"report: {args.report}")

    failed = sum(1 for result in results if not result.valid)
    passed = len(results) - failed
    print(f"summary files={len(results)} passed={passed} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
