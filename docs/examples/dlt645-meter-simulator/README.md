# DLT645 电表 MQTT 模拟器

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`dlt645_meter_simulator.py` 通过设备 Access Token 连接 ThingsBoard MQTT，
按 `dlt645_meter_thing_model.tsl.json` 物模型周期性上报遥测和事件，并处理共享属性与 RPC 下发。

适用场景：

- 设备接入前验证产品物模型、设备配置与 MQTT 通道。
- 没有真实电表时用于仪表板、告警规则、规则链联调。
- 验证共享属性下发和 RPC 控制。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。

## 2. 环境要求

- Python 3.9+
- 可访问 ThingsBoard MQTT 端口（默认 `1883`，TLS 通常为 `8883`）
- 已创建产品、设备，并获取设备 Access Token

## 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 4. 快速开始

先打印示例报文，不连接 MQTT：

```powershell
python dlt645_meter_simulator.py --dry-run
```

连接平台并持续上报：

```powershell
python dlt645_meter_simulator.py `
  --mqtt-host <MQTT_HOST> `
  --mqtt-port 1883 `
  --token <ACCESS_TOKEN> `
  --interval 5 `
  --event-interval 30
```

只发送 3 轮遥测后退出：

```powershell
python dlt645_meter_simulator.py `
  --mqtt-host <MQTT_HOST> `
  --token <ACCESS_TOKEN> `
  --count 3 --interval 5
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--mqtt-host` | `127.0.0.1` | 否 | MQTT 服务地址 |
| `--mqtt-port` | `1883` | 否 | MQTT 服务端口 |
| `--token` | 无 | 连接是 | 设备 Access Token；`--dry-run` 时可省略 |
| `--client-id` | 自动生成 | 否 | MQTT Client ID |
| `--keepalive` | `60` | 否 | MQTT Keepalive 秒数 |
| `--qos` | `1` | 否 | MQTT QoS，可选 `0` / `1` / `2` |
| `--tls` | 关闭 | 否 | 启用 TLS |
| `--ca-cert` | 无 | 否 | TLS CA 证书路径 |
| `--tsl` | `dlt645_meter_thing_model.tsl.json` | 否 | 物模型 TSL 文件 |
| `--interval` | `5` | 否 | 遥测上报间隔（秒，最小 5） |
| `--event-interval` | `30` | 否 | 事件上报间隔（秒，`0` 表示关闭） |
| `--count` | `0` | 否 | 遥测轮次，`0` 表示持续运行 |
| `--seed` | 无 | 否 | 随机数种子，便于复现 |
| `--relay-off` | 关闭 | 否 | 启动时继电器为断开状态 |
| `--dry-run` | 关闭 | 否 | 只打印示例报文，不连接 MQTT |
| `--log-level` | `INFO` | 否 | 日志级别 |

## 6. MQTT 主题

| 方向 | 主题 | 说明 |
| --- | --- | --- |
| 上报 | `v1/devices/me/telemetry` | 遥测与事件 |
| 订阅 | `v1/devices/me/attributes` | 共享属性 |
| 订阅 | `v1/devices/me/rpc/request/+` | RPC 请求 |
| 上报 | `v1/devices/me/rpc/response/{requestId}` | RPC 响应 |

支持的共享属性：

- `reportInterval`：上报周期，范围 5～3600 秒。
- `relay` / `relayState`：继电器状态。

支持的 RPC：

- `setRelay`：`{"on": true}`
- `applyConfig`：`{"reportInterval": 30}`
- `syncTime`：`{"time": 1700000000000}`
- `set`：直接应用共享属性

## 7. 输出说明

- 日志输出到标准错误，包含连接信息、上行报文、RPC 请求与响应。
- 退出时输出汇总：`telemetry`、`event`、`rpc` 计数。
- 设备令牌在日志中自动脱敏。

## 8. 常见问题

| 问题 | 排查 |
| --- | --- |
| `MQTT 连接超时` | 检查 `--mqtt-host` / `--mqtt-port`、网络与防火墙 |
| 认证失败或立即断开 | 确认 `--token` 是设备 Access Token，而非产品 ID |
| 平台看不到遥测 | 确认设备已关联正确的设备配置（Device Profile） |
| RPC 无响应 | 确认设备已连接且订阅了 `v1/devices/me/rpc/request/+` |
| 物模型加载失败 | 检查 `--tsl` 路径是否指向有效 JSON 文件 |

## 9. 安全说明

- 仓库不保存任何真实设备 Token。
- 请勿将包含 Access Token 的命令或日志提交到代码仓库。
- 生产环境建议启用 TLS（`--tls` / `--ca-cert`）。

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
