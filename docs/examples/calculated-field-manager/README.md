# 计算字段管理工具

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`calculated_field_manager.py` 通过 ThingsBoard REST API 查询、创建、更新、删除计算字段，
并支持脚本测试和调试事件查询。

- 协议：**REST**
- 覆盖手册：计算字段
- 默认地址：`http://localhost:8080`

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。

## 2. 环境要求

- Python 3.9+
- 租户管理员账号或有效 API Key
- 可访问 ThingsBoard 服务

## 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 4. 快速开始

查询计算字段：

```powershell
python calculated_field_manager.py --action list
```

查询详情：

```powershell
python calculated_field_manager.py `
  --action get `
  --calculated-field-id <CALCULATED_FIELD_ID>
```

创建计算字段：

```powershell
python calculated_field_manager.py `
  --action create `
  --config .\calculated-field.json
```

测试脚本：

```powershell
python calculated_field_manager.py `
  --action test-script `
  --config .\calculated-field-test.json
```

查看调试事件：

```powershell
python calculated_field_manager.py `
  --action debug `
  --calculated-field-id <CALCULATED_FIELD_ID>
```

删除计算字段：

```powershell
python calculated_field_manager.py `
  --action delete `
  --calculated-field-id <CALCULATED_FIELD_ID>
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--tb-url` | `http://localhost:8080` | 否 | ThingsBoard 地址 |
| `--api-key` | 无 | 二选一 | ThingsBoard API Key |
| `--username` | `tenant@thingsboard.org` | 否 | 账号登录用户名 |
| `--password` | 无 | 二选一 | 密码；缺省时交互输入 |
| `--action` | 无 | 是 | `list` / `get` / `create` / `update` / `delete` / `test-script` / `debug` |
| `--calculated-field-id` | 无 | 视操作 | 计算字段 ID |
| `--config` | 无 | 创建/测试时 | 计算字段或测试脚本 JSON 文件 |
| `--page-size` | `100` | 否 | 分页大小 |
| `--page` | `0` | 否 | 页码 |
| `--dry-run` | 关闭 | 否 | 只打印请求，不访问平台 |
| `--log-level` | `INFO` | 否 | 日志级别 |

## 6. 接口说明

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| GET | `/api/calculatedFields` | 查询计算字段列表 |
| GET | `/api/calculatedField/{id}` | 查询计算字段详情 |
| POST | `/api/calculatedField` | 创建或更新计算字段 |
| DELETE | `/api/calculatedField/{id}` | 删除计算字段 |
| POST | `/api/calculatedField/testScript` | 测试计算字段脚本 |
| GET | `/api/calculatedField/{id}/debug` | 查询最近调试事件 |

计算字段请求体以平台页面或 Swagger 为准，建议从页面导出或复制一份 `calculated-field.json`。

## 7. 常见问题

| 问题 | 排查 |
| --- | --- |
| `HTTP 401` | 需要租户管理员权限 |
| 创建失败 | 检查配置 JSON 的实体、输出和参数 |
| 测试脚本失败 | 检查输入参数和脚本语法 |
| 没有调试事件 | 先开启调试并让实体产生数据 |
| 删除失败 | 计算字段可能被告警规则或其他配置引用 |

## 8. 安全说明

- 仓库不保存任何真实 API Key 或密码。
- 计算字段配置可能包含业务逻辑，请妥善保管配置文件。

## Java 运行方式

本示例提供独立的 Java Maven 工程，位于 `java/` 目录。

```powershell
cd java
mvn -q compile
mvn -q exec:java -Dexec.args="--action list"
```

- 需要 JDK 17+ 和 Maven。
- Java 版参数与 Python 版保持一致。
- `pom.xml` 已配置 `exec-maven-plugin`，可通过 `-Dexec.args` 传入参数。
