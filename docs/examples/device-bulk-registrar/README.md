# 设备批量注册工具

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`device_bulk_registrar.py` 在 ThingsBoard 中为指定产品批量创建设备，自动获取设备 Access Token、
写入服务端属性，并可选把设备挂到网关设备下。

适用于：

- 交付时按编号批量创建 `device-01`、`device-02` 等设备；
- 为测试环境快速准备设备与凭证；
- 批量创建设备后统一绑定到网关。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。

## 2. 环境要求

- Python 3.9+
- 可访问 ThingsBoard 与 thing-model 服务
- 产品已完成同步（包含 `tbProfileId`、`tbAssetId`、`tenantId`）

## 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 4. 快速开始

先打印计划，不访问平台：

```powershell
python device_bulk_registrar.py `
  --product-id <PRODUCT_ID> `
  --prefix device --count 3 `
  --dry-run
```

使用账号密码批量创建 10 台设备：

```powershell
python device_bulk_registrar.py `
  --tb-url http://localhost:8080 `
  --thingmodel-url http://localhost:8080/api/thing-model `
  --username tenant@thingsboard.org `
  --product-id <PRODUCT_ID> `
  --prefix device --count 10 `
  --site-code SIM `
  --output-dir .\device-output
```

使用 API Key 并挂到网关下：

```powershell
python device_bulk_registrar.py `
  --tb-url <TB_URL> `
  --thingmodel-url <THINGMODEL_URL> `
  --api-key <API_KEY> `
  --product-id <PRODUCT_ID> `
  --prefix sub-device --count 5 `
  --gateway-device gateway-01 `
  --relation-type Contains `
  --output-dir .\device-output
```

指定设备名称：

```powershell
python device_bulk_registrar.py `
  --product-id <PRODUCT_ID> `
  --name device-01 --name device-02
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--tb-url` | `http://localhost:8080` | 否 | ThingsBoard 地址 |
| `--thingmodel-url` | `http://localhost:8080/api/thing-model` | 否 | thing-model 地址 |
| `--timeout` | `30` | 否 | HTTP 超时秒数 |
| `--api-key` | 无 | 二选一 | ThingsBoard API Key |
| `--username` | `tenant@thingsboard.org` | 否 | 账号密码登录用户名 |
| `--password` | 无 | 二选一 | 账号密码登录密码；缺省时交互输入 |
| `--product-id` | 无 | 是 | 产品 ID |
| `--profile-id` | 从产品读取 | 否 | 设备配置 ID |
| `--name` | 无 | 二选一 | 设备名称，可重复 |
| `--prefix` | 无 | 二选一 | 批量设备名称前缀 |
| `--count` | `0` | 二选一 | 批量设备数量 |
| `--start-index` | `1` | 否 | 批量起始序号 |
| `--site-code` | 无 | 否 | 写入 `site_code` 服务端属性 |
| `--gateway` | 关闭 | 否 | 把新设备标记为网关设备 |
| `--gateway-device` | 无 | 否 | 将新设备挂到该网关设备下 |
| `--relation-type` | `Contains` | 否 | 网关关系类型 |
| `--output-dir` | `.` | 否 | CSV 输出目录 |
| `--dry-run` | 关闭 | 否 | 只打印计划，不访问平台 |
| `--log-level` | `INFO` | 否 | 日志级别 |

设备名称规则：

- 使用 `--name` 时按给定名称创建；
- 使用 `--prefix` + `--count` 时生成 `prefix-0001`、`prefix-0002`……

## 6. 输出说明

输出 `device-credentials.csv`（若已存在则追加时间戳）：

```text
product_id, device_name, device_id, access_token, tsl_version,
profile_id, site_code, gateway, status, error, created_at
```

- `status` 取值：`created`、`skipped`、`failed`。
- 已存在的同名设备会跳过，不会重复创建。
- 单个设备失败会写入 `error` 列并继续处理其余设备。
- 存在失败时退出码为 `1`。

## 7. 关联接口

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| GET | `/api/tenant/devices?deviceName={name}` | 按名称查询设备 |
| POST | `/api/device` | 创建设备 |
| GET | `/api/device/{deviceId}/credentials` | 查询设备凭证 |
| POST | `/api/plugins/telemetry/DEVICE/{deviceId}/attributes/SERVER_SCOPE` | 写入服务端属性 |
| POST | `/api/relation` | 创建网关关系 |

## 8. 常见问题

| 问题 | 排查 |
| --- | --- |
| 产品未同步 | 确认产品存在 `tbProfileId`、`tbAssetId`、`tenantId` |
| `HTTP 401` | API Key 无效；改用 `--username/--password` 验证 |
| 设备已存在 | 同名设备会被跳过，如需重建请先在平台删除 |
| 网关不存在 | 确认 `--gateway-device` 名称正确 |
| CSV 无 Access Token | 检查设备凭证是否创建成功 |

## 9. 安全说明

- 仓库不保存任何真实 API Key、密码或设备 Token。
- `device-credentials.csv` 包含设备 Access Token，请妥善保管，不要提交到代码仓库。
- 建议在测试环境先使用 `--dry-run` 检查名称与数量。

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
