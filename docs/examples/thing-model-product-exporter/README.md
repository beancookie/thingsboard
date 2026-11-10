# 物模型产品导出工具

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`thing_model_product_exporter.py` 从运行中的 ThingsBoard / thing-model 平台导出产品列表和完整 TSL 物模型，
适合产品备份、迁移和交付。

输出内容：

```text
product-export/
├── products.csv              # 产品元数据汇总（utf-8-sig，Excel 可直接打开）
├── products.json             # 产品列表、详情与导出结果
└── tsl/
    └── <productId>.tsl.json  # 每个产品的完整 TSL
```

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。

## 2. 环境要求

- Python 3.9+
- 可访问 ThingsBoard 与 thing-model 服务
- 具备租户管理员权限的账号，或有效的 API Key

## 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 4. 快速开始

使用账号密码导出全部产品（未提供密码时交互输入）：

```powershell
python thing_model_product_exporter.py `
  --tb-url http://localhost:8080 `
  --thingmodel-url http://localhost:8080/api/thing-model `
  --username tenant@thingsboard.org `
  --output-dir .\product-export
```

使用 API Key 导出：

```powershell
python thing_model_product_exporter.py `
  --tb-url <TB_URL> `
  --thingmodel-url <THINGMODEL_URL> `
  --api-key <API_KEY> `
  --output-dir .\product-export
```

只导出指定产品（`--product-id` 可重复）：

```powershell
python thing_model_product_exporter.py `
  --tb-url <TB_URL> `
  --thingmodel-url <THINGMODEL_URL> `
  --api-key <API_KEY> `
  --product-id <PRODUCT_ID_1> `
  --product-id <PRODUCT_ID_2> `
  --output-dir .\product-export
```

只导出列表和 TSL，跳过产品详情：

```powershell
python thing_model_product_exporter.py `
  --tb-url <TB_URL> `
  --thingmodel-url <THINGMODEL_URL> `
  --api-key <API_KEY> `
  --no-detail
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--tb-url` | `http://localhost:8080` | 否 | ThingsBoard 地址 |
| `--thingmodel-url` | `http://localhost:8080/api/thing-model` | 否 | thing-model 地址；网关代理使用 `<host>/api/thing-model` |
| `--timeout` | `30` | 否 | HTTP 超时秒数 |
| `--api-key` | 无 | 二选一 | ThingsBoard API Key |
| `--username` | `tenant@thingsboard.org` | 否 | 账号密码登录用户名 |
| `--password` | 无 | 二选一 | 账号密码登录密码；缺省时交互输入 |
| `--product-id` | 空 = 全部 | 否 | 指定产品 ID，可重复 |
| `--output-dir` | `product-export` | 否 | 输出目录 |
| `--no-detail` | 关闭 | 否 | 跳过产品详情请求 |
| `--log-level` | `INFO` | 否 | 日志级别 |

认证方式：

- `--api-key`：先换取 JWT，再调用产品接口。
- `--username` / `--password`：直接登录获取 JWT。
- `--api-key` 与 `--password` 不能同时使用。

## 6. 输出说明

`products.csv` 列：

```text
product_id, name, model, category_id, tsl_version, status,
property_count, event_count, action_count,
tb_profile_id, tb_asset_id, tb_rule_chain_id,
updated_at, tsl_file, error
```

`products.json` 结构：

```json
{
  "exportedAt": "2026-01-01T00:00:00+00:00",
  "tbUrl": "http://localhost:8080",
  "thingmodelUrl": "http://localhost:8080/api/thing-model",
  "count": 2,
  "products": [
    {
      "meta": {},
      "detail": {},
      "tslFile": "tsl/<productId>.tsl.json",
      "error": ""
    }
  ]
}
```

单个产品失败会写入 `error` 列并继续导出其余产品，最终以非 0 退出码结束。

## 7. 常见问题

| 问题 | 排查 |
| --- | --- |
| `HTTP 401` | API Key 无效或无权限；改用 `--username/--password` 验证 |
| 产品列表为空 | 确认当前账号租户下有产品，或检查 `--thingmodel-url` |
| TSL 缺失 | 产品可能未同步物模型，先在产品管理中完成同步 |
| 证书或代理错误 | 检查 HTTPS 证书与系统代理设置 |
| 导出部分产品失败 | 查看 `products.csv` 的 `error` 列定位原因 |

## 8. 安全说明

- 仓库不保存任何真实 API Key 或密码。
- API Key、密码只通过命令行传入，不会写入日志。
- 导出的 TSL 属于平台业务数据，请按需妥善保管。
- 如需分享命令，请先替换或删除 `--api-key` / `--password` 的值。

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
