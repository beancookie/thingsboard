# 物模型 TSL 校验工具

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`tsl_validator.py` 在导入或提交物模型前，按《物模型定义规范使用手册》对 TSL JSON 做离线校验，
提前发现字段缺失、类型错误、范围越界、结构体嵌套等问题。

本示例仅使用 Python 标准库，不访问平台、不需要认证，也不内置任何密钥。

## 2. 环境要求

- Python 3.9+

## 3. 安装依赖

无需安装第三方依赖。

## 4. 快速开始

校验单个文件：

```powershell
python tsl_validator.py --tsl .\standard-thing-model.tsl.json
```

批量校验目录：

```powershell
python tsl_validator.py --dir .\tsl
```

严格模式（警告也视为失败）并输出 JSON 报告：

```powershell
python tsl_validator.py `
  --tsl .\standard-thing-model.tsl.json `
  --strict `
  --report .\tsl-report.json
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--tsl` | 无 | 二选一 | 要校验的 TSL 文件，可重复 |
| `--dir` | 无 | 二选一 | 批量校验目录下的 `*.json`，可重复 |
| `--strict` | 关闭 | 否 | 将警告也视为校验失败 |
| `--report` | 无 | 否 | 输出 JSON 报告路径 |
| `--log-level` | `INFO` | 否 | 日志级别 |

## 6. 校验内容

### 6.1 顶层结构

- `version` 非空且长度不超过 32；
- `profile.ProductId` 或 `profile.productId` 非空；
- `properties` 存在，可以是空数组。

### 6.2 标识符与数量

- 所有 `id` 符合 `^[A-Za-z_][A-Za-z0-9_]{0,49}$`；
- 属性、事件、行为 `id` 分别唯一；
- 同一事件或行为的参数 `id` 唯一；
- 属性 + 事件 + 行为总数不超过 100。

### 6.3 属性

- `name` 非空；
- `mode` 为 `r` 或 `rw`；
- `define.type` 合法；
- 建议将属性级 `mapping` 放入 `define.mapping`。

### 6.4 数据类型

- `int` 在 int32 范围内；
- `min <= max`，`start` 在范围内，`step >= 0`；
- `enum` 至少 2 项且键为数字；
- `enum_string` 至少 2 项；
- 非数值类型不建议配置 `min/max/start/step`；
- 非枚举类型不建议配置 `mapping`。

### 6.5 结构体

- `specs` 非空；
- 结构体字段不能再使用 `struct`；
- 事件参数不允许使用 `struct`。

### 6.6 事件与行为

- 事件 `type` 为 `info`、`alert` 或 `fault`；
- 事件参数和行为参数必须有合法 `id` 和非空 `name`。

### 6.7 提示项

- 属性 `id` 使用 `ts`、`event_id`、`event_type`、`event_ts` 时告警；
- 检测到旧版 `dataType`、`stringenum`、数组形式 `specs` 时提示转换。

## 7. 输出说明

控制台逐文件输出：

```text
[OK] standard-thing-model.tsl.json errors=0 warnings=0
summary files=1 passed=1 failed=0
```

存在错误时：

```text
[FAIL] bad.tsl.json errors=2 warnings=0
  error $.properties[0].define: min (10) 不能大于 max (1)
  error $.events[0].type: 事件 type 必须是 info、alert 或 fault，当前为 'unknown'
summary files=1 passed=0 failed=1
```

`--report` 生成的 JSON：

```json
{
  "valid": false,
  "files": [
    {
      "path": "bad.tsl.json",
      "valid": false,
      "errors": [
        {"path": "$.properties[0].define", "message": "min (10) 不能大于 max (1)"}
      ],
      "warnings": []
    }
  ]
}
```

退出码：全部通过 `0`，存在失败 `1`，参数错误 `2`。

## 8. 常见问题

| 问题 | 排查 |
| --- | --- |
| 提示缺少 `mode` | 属性必须显式填写 `r` 或 `rw` |
| enum 映射正确但校验失败 | 确认映射写在 `define.mapping` |
| 结构体字段报错 | 当前仅支持一层结构体，字段不能再用 `struct` |
| 事件参数报错 | 事件参数不能使用 `struct`，请拆成简单类型 |
| 旧文件大量提示 | 先按平台规则转换为标准写法再校验 |

## 9. 安全说明

- 工具完全离线运行，不会上传或修改物模型文件。
- 报告可能包含物模型字段信息，请按需妥善保管。

## Java 运行方式

本示例提供独立的 Java Maven 工程，位于 `java/` 目录。

```powershell
cd java
mvn -q compile
mvn -q exec:java -Dexec.args="--help"
```

- 需要 JDK 17+ 和 Maven。
- Java 版参数与 Python 版保持一致。
- `pom.xml` 已配置 `exec-maven-plugin`，可通过 `-Dexec.args` 传入参数。
