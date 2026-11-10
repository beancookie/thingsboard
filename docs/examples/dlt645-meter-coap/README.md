# DLT645 电表 CoAP 模拟器

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`dlt645_meter_coap.py` 通过设备 Access Token 使用 ThingsBoard CoAP 传输（UDP），
按 `dlt645_meter_thing_model.tsl.json` 物模型周期性上报遥测和事件，并通过 Observe 接收共享属性与 RPC 下发。

适用场景：

- 设备接入前验证产品物模型、设备配置与 CoAP 通道。
- 没有真实电表时用于仪表板、告警规则、规则链联调。
- 验证共享属性下发和 RPC 控制。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。

## 2. 环境要求

- Python 3.9+
- 可访问平台 CoAP 端口（默认 `5683/UDP`）
- 已创建产品、设备，并获取设备 Access Token

## 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 4. 快速开始

先打印示例报文，不访问平台（无需安装 aiocoap 也可运行）：

```powershell
python dlt645_meter_coap.py --dry-run
```

持续上报遥测和事件：

```powershell
python dlt645_meter_coap.py `
  --coap-host 129.211.239.15 `
  --coap-port 5683 `
  --token <ACCESS_TOKEN> `
  --interval 5 `
  --event-interval 30
```

只发送 3 轮遥测后退出：

```powershell
python dlt645_meter_coap.py `
  --coap-host 129.211.239.15 `
  --token <ACCESS_TOKEN> `
  --count 3 --interval 5
```

开启共享属性和 RPC Observe：

```powershell
python dlt645_meter_coap.py `
  --coap-host 129.211.239.15 `
  --token <ACCESS_TOKEN> `
  --observe
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--coap-host` | `129.211.239.15` | 否 | CoAP 服务地址 |
| `--coap-port` | `5683` | 否 | CoAP 服务端口（UDP） |
| `--token` | 无 | 连接是 | 设备 Access Token；`--dry-run` 时可省略 |
| `--timeout` | `30` | 否 | 请求超时秒数 |
| `--tsl` | `dlt645_meter_thing_model.tsl.json` | 否 | 物模型 TSL 文件 |
| `--interval` | `5` | 否 | 遥测上报间隔（秒，最小 5） |
| `--event-interval` | `30` | 否 | 事件上报间隔（秒，`0` 表示关闭） |
| `--count` | `0` | 否 | 遥测轮次，`0` 表示持续运行 |
| `--seed` | 无 | 否 | 随机数种子，便于复现 |
| `--relay-off` | 关闭 | 否 | 启动时继电器为断开状态 |
| `--observe` | 关闭 | 否 | 开启共享属性和 RPC Observe |
| `--dry-run` | 关闭 | 否 | 只打印示例报文，不访问平台 |
| `--log-level` | `INFO` | 否 | 日志级别 |

## 6. CoAP 接口

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| POST | `/api/v1/{token}/telemetry` | 上报遥测和事件 |
| GET Observe | `/api/v1/{token}/attributes` | 订阅共享属性 |
| GET Observe | `/api/v1/{token}/rpc` | 订阅 RPC 请求 |
| POST | `/api/v1/{token}/rpc/{requestId}` | 返回 RPC 响应 |

> CoAP 遥测和属性使用 Content-Format 50（application/json）。

支持的共享属性：

- `reportInterval`：上报周期，范围 5～3600 秒。
- `relay` / `relayState`：继电器状态。

支持的 RPC：

- `setRelay`：`{"on": true}`
- `applyConfig`：`{"reportInterval": 30}`
- `syncTime`：`{"time": 1700000000000}`
- `set`：直接应用共享属性

RPC 响应使用下行报文中的 `id` 作为 `requestId`。

## 7. 输出说明

- 日志输出到标准错误，包含连接信息、上行报文、共享属性和 RPC 请求与响应。
- 退出时输出汇总：`telemetry`、`event`、`rpc` 计数。
- 设备令牌在日志中自动脱敏。

## 8. 常见问题

| 问题 | 排查 |
| --- | --- |
| 请求超时 | 检查 UDP 端口、网络和防火墙是否放行 `5683/UDP` |
| `4.01 Unauthorized` | 确认 `--token` 是设备 Access Token |
| 平台看不到遥测 | 确认设备已关联正确的设备配置 |
| 收不到共享属性/RPC | 需要加 `--observe`，并确认服务端支持 Observe |
| 未安装 aiocoap | 执行 `python -m pip install -r requirements.txt` |

## 9. 安全说明

- 仓库不保存任何真实设备 Token。
- 请勿将包含 Access Token 的命令或日志提交到代码仓库。
- CoAP 默认基于 UDP 且无传输加密，生产环境建议使用 DTLS 或网关代理。

## Java 运行方式

本示例提供独立的 Java Maven 工程，位于 `java/` 目录。

```powershell
cd java
mvn -q compile
mvn -q exec:java -Dexec.args="--coap-host 129.211.239.15 --token <ACCESS_TOKEN> --count 3"
```

- 需要 JDK 17+ 和 Maven。
- Java 版参数与 Python 版保持一致。
- `pom.xml` 已配置 `exec-maven-plugin`，可通过 `-Dexec.args` 传入参数。
