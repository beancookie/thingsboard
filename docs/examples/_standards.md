# Python 示例代码规范

本目录下的示例代码面向平台用户，要求可直接复制运行、参数清晰、便于长期维护。
新增或修改示例时请遵循以下约定。

## 1. 目录结构

```text
docs/examples/<example-slug>/
├── README.md                 # 使用说明（必需）
├── requirements.txt          # 第三方依赖（必需）
├── <example_module>.py       # 入口脚本（必需）
└── <supporting-files>        # 物模型、示例数据等（可选）
```

- 目录使用 `kebab-case`，例如 `dlt645-meter-simulator`。
- Python 文件使用 `snake_case`，并与目录语义对应，例如 `dlt645_meter_simulator.py`。
- 每个示例必须能独立运行，不依赖本仓库其他 Python 文件。

## 2. 脚本结构

```python
#!/usr/bin/env python3
"""一句话说明示例用途。

补充运行方式和注意事项。
"""
from __future__ import annotations

import ...  # 标准库、第三方库

LOGGER = logging.getLogger("<example-name>")
CONSTANT = ...


@dataclass
class ExampleConfig:
    ...


def pure_helper(...) -> ...:
    ...


class ExampleClient:
    ...


def build_arg_parser() -> argparse.ArgumentParser:
    ...


def main() -> int:
    ...


if __name__ == "__main__":
    raise SystemExit(main())
```

要求：

- 使用 `from __future__ import annotations`。
- 模块级只放常量、类型和函数/类定义，不在导入时执行副作用。
- 入口统一为 `main() -> int`，使用 `raise SystemExit(main())`。
- 对可配置项使用 `dataclass` 承载，避免长参数列表。
- 代码注释保持最少，优先用清晰的命名表达意图。

## 3. 命令行参数

- 只使用命令行参数配置，不读取环境变量，不内置密钥。
- 参数统一使用 `--kebab-case`，按用途分组：`连接`、`认证`、`行为`、`输出`。
- 使用 `argparse.ArgumentParser`，并设置 `formatter_class=argparse.ArgumentDefaultsHelpFormatter`。
- 必填项在 `main()` 中显式校验，错误通过 `parser.error()` 输出（退出码 `2`）。
- 密码、Access Token、API Key 等敏感信息：
  - 不设默认值；
  - 只允许通过命令行传入；
  - 密码可在缺省时使用 `getpass.getpass()` 交互输入；
  - 日志中必须脱敏。
- 通用参数命名：

| 参数 | 说明 |
| --- | --- |
| `--log-level` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `--timeout` | HTTP 超时秒数 |
| `--dry-run` | 只生成/打印报文，不产生外部副作用 |

## 4. 输出与退出码

- 日志统一输出到 `stderr`，格式为 `%(asctime)s %(levelname)s %(message)s`。
- 机器可读结果输出到标准输出或文件。
- JSON 使用 `ensure_ascii=False`；CSV 使用 `utf-8-sig`，便于 Excel 打开。
- 退出码：

| 退出码 | 含义 |
| --- | --- |
| `0` | 成功 |
| `1` | 运行错误（连接失败、导出失败等） |
| `2` | 参数错误（argparse） |

## 5. 安全

- 仓库中不得出现任何真实 Token、API Key 或密码。
- 示例文档中的连接信息使用占位符，例如 `<ACCESS_TOKEN>`、`<API_KEY>`。
- 保存到文件的敏感信息需在 README 中明确提示用户妥善保管。

## 6. README 结构

每份示例 README 固定包含：

```text
# 示例名称
> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述
## 2. 环境要求
## 3. 安装依赖
## 4. 快速开始
## 5. 参数说明
## 6. 输出说明
## 7. 常见问题
## 8. 安全说明
```

- 参数说明必须使用表格：`参数 | 默认值 | 必填 | 说明`。
- 命令示例使用 `powershell` 或 `bash` 代码块，可直接复制。
- 示例中的地址、令牌、产品 ID 使用占位符。

## 7. 验证

提交前至少完成：

```powershell
python -m py_compile <example_module>.py
python <example_module>.py --help
```

如示例支持 `--dry-run`，应额外验证：

```powershell
python <example_module>.py --dry-run ...
```
