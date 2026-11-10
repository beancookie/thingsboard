# 产品增删改查工具

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`product_crud_tool.py` 通过 thing-model REST API 完成产品查询、创建、更新、TSL 提交、校验和删除。

- 协议：**REST**
- 覆盖手册：产品管理
- 默认地址：`http://localhost:8080`、`http://localhost:8080/api/thing-model`

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。

## 2. 环境要求

- Python 3.9+
- 可访问 ThingsBoard 与 thing-model 服务
- 租户管理员账号或有效 API Key

## 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 4. 快速开始

查询产品列表：

```powershell
python product_crud_tool.py --action list
```

按关键字搜索：

```powershell
python product_crud_tool.py --action list --keyword DEMO
```

查询产品详情：

```powershell
python product_crud_tool.py --action get --product-id DEMO_TSL_001
```

创建或更新产品：

```powershell
python product_crud_tool.py `
  --action create `
  --product-id DEMO_TSL_001 `
  --name "标准环境监测设备" `
  --model DEMO-ENV-01 `
  --category-id 1 `
  --tsl-version 1.0 `
  --tsl .\standard-thing-model.tsl.json
```

使用完整 JSON 配置创建：

```powershell
python product_crud_tool.py `
  --action create `
  --config .\product.json
```

提交新的 TSL 版本：

```powershell
python product_crud_tool.py `
  --action update-tsl `
  --product-id DEMO_TSL_001 `
  --tsl .\standard-thing-model.tsl.json `
  --tsl-version 1.1
```

只校验 TSL：

```powershell
python product_crud_tool.py `
  --action validate `
  --product-id DEMO_TSL_001 `
  --tsl .\standard-thing-model.tsl.json
```

删除产品：

```powershell
python product_crud_tool.py --action delete --product-id DEMO_TSL_001
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--tb-url` | `http://localhost:8080` | 否 | ThingsBoard 地址 |
| `--thingmodel-url` | `http://localhost:8080/api/thing-model` | 否 | thing-model 地址 |
| `--timeout` | `30` | 否 | HTTP 超时秒数 |
| `--api-key` | 无 | 二选一 | ThingsBoard API Key |
| `--username` | `tenant@thingsboard.org` | 否 | 账号登录用户名 |
| `--password` | 无 | 二选一 | 账号登录密码；缺省时交互输入 |
| `--action` | 无 | 是 | `list` / `get` / `create` / `update` / `update-tsl` / `validate` / `catalog` / `delete` |
| `--product-id` | 无 | 视操作 | 产品 ID |
| `--keyword` | 无 | 否 | 列表搜索关键字 |
| `--page-size` | `100` | 否 | 分页大小 |
| `--page` | `0` | 否 | 页码 |
| `--config` | 无 | 否 | 创建/更新的 JSON 配置文件 |
| `--tsl` | 无 | 视操作 | TSL JSON 文件 |
| `--tsl-version` | 无 | 否 | TSL 版本 |
| `--name` | 无 | 否 | 产品名称 |
| `--model` | 无 | 否 | 产品型号 |
| `--category-id` | 无 | 否 | 产品分类 ID |
| `--strict-unknown` | 关闭 | 否 | 开启严格未知字段校验 |
| `--dry-run` | 关闭 | 否 | 只打印请求，不访问平台 |
| `--log-level` | `INFO` | 否 | 日志级别 |

## 6. 接口说明

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| GET | `/api/thing-model/products` | 查询产品列表 |
| POST | `/api/thing-model/products` | 创建或更新产品 |
| GET | `/api/thing-model/products/{productId}` | 查询产品详情 |
| PUT | `/api/thing-model/products/{productId}/thing-model` | 提交新 TSL 版本 |
| POST | `/api/thing-model/products/{productId}/thing-model/validate` | 只校验 TSL |
| GET | `/api/thing-model/products/{productId}/catalog` | 查询属性/事件/行为目录 |
| DELETE | `/api/thing-model/products/{productId}` | 删除产品 |

创建/更新请求体示例：

```json
{
  "productId": "DEMO_TSL_001",
  "name": "标准环境监测设备",
  "model": "DEMO-ENV-01",
  "categoryId": "1",
  "tslVersion": "1.0",
  "tsl": {},
  "strictUnknown": false
}
```

## 7. 常见问题

| 问题 | 排查 |
| --- | --- |
| `HTTP 401` | API Key 或账号密码无效 |
| `HTTP 409` | 产品 ID 已存在或 TSL 版本重复 |
| 删除返回 409 | 产品下仍有设备，先删除设备再删除产品 |
| TSL 校验失败 | 使用 `tsl-validator` 示例先离线校验 |
| 查不到产品 | 确认当前账号租户范围与 `--thingmodel-url` |

## 8. 安全说明

- 仓库不保存任何真实 API Key 或密码。
- 删除产品前请确认没有关联设备，并做好备份。

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
