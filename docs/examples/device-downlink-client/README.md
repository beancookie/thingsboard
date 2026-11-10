# 设备下行接收示例

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`device_downlink_client.py` 使用设备 Access Token 连接 ThingsBoard MQTT，
订阅共享属性和 RPC 主题，演示设备端如何接收并处理平台下发。

对应手册：[MQTT推送数据到设备使用手册](../../manuals/MQTT推送数据到设备使用手册.md)。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。

## 2. 环境要求

- Python 3.9+
- 可访问 ThingsBoard MQTT 端口（默认 `1883`，TLS 通常为 `8883`）
- 已获取设备 Access Token

## 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 4. 快速开始

先打印示例报文，不连接 MQTT：

```powershell
python device_downlink_client.py --dry-run
```

连接平台并等待下发：

```powershell
python device_downlink_client.py `
  --mqtt-host <MQTT_HOST> `
  --mqtt-port 1883 `
  --token <ACCESS_TOKEN> `
  --client-id device-01
```

启用 RPC 成功后的确认遥测：

```powershell
python device_downlink_client.py `
  --mqtt-host <MQTT_HOST> `
  --token <ACCESS_TOKEN> `
  --ack-telemetry
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--mqtt-host` | `127.0.0.1` | 否 | MQTT 服务地址 |
| `--mqtt-port` | `1883` | 否 | MQTT 服务端口 |
| `--token` | 无 | 连接是 | 设备 Access Token；`--dry-run` 时可省略 |
| `--client-id` | `device-downlink-client` | 否 | MQTT Client ID |
| `--keepalive` | `60` | 否 | MQTT Keepalive 秒数 |
| `--qos` | `1` | 否 | MQTT QoS，可选 `0` / `1` / `2` |
| `--tls` | 关闭 | 否 | 启用 TLS |
| `--ca-cert` | 无 | 否 | TLS CA 证书路径 |
| `--ack-telemetry` | 关闭 | 否 | RPC 成功后上报确认遥测 |
| `--dry-run` | 关闭 | 否 | 只打印示例报文，不连接 MQTT |
| `--log-level` | `INFO` | 否 | 日志级别 |

## 6. 订阅主题与处理逻辑

| 主题 | 方向 | 处理 |
| --- | --- | --- |
| `v1/devices/me/attributes` | 下行 | 更新本地配置并打印 |
| `v1/devices/me/rpc/request/+` | 下行 | 处理 RPC 并发布响应 |
| `v1/devices/me/rpc/response/{requestId}` | 上行 | 回复 RPC 结果 |
| `v1/devices/me/telemetry` | 上行 | 可选的确认遥测 |

支持的 RPC：

| 方法 | 参数 | 处理 |
| --- | --- | --- |
| `set` | 任意共享属性 | 合并到本地配置 |
| `setMode` | `{"mode": 0\|1\|2}` | 设置运行模式 |
| `setRelay` | `{"on": true\|false}` | 设置继电器状态 |
| `applyConfig` | `{"reportInterval": 5~3600}` | 应用上报周期 |

共享属性示例：

```json
{
  "reportInterval": 30,
  "mode": 1
}
```

RPC 请求示例：

```json
{
  "method": "setMode",
  "params": {
    "mode": 1
  }
}
```

成功响应：

```json
{
  "result": "ok",
  "mode": 1
}
```

失败响应：

```json
{
  "error": "invalid mode"
}
```

## 7. 输出说明

- 日志输出到标准错误，包含连接信息、共享属性、RPC 请求与响应。
- `--dry-run` 输出示例报文与处理结果，便于离线核对格式。
- 设备令牌在日志中自动脱敏。

## 8. 常见问题

| 问题 | 排查 |
| --- | --- |
| 收不到共享属性 | 确认设备已连接且订阅 `v1/devices/me/attributes` |
| 收不到 RPC | 确认订阅 `v1/devices/me/rpc/request/+` |
| RPC 超时 | 设备需在超时前回复 `v1/devices/me/rpc/response/{requestId}` |
| 认证失败 | 确认 `--token` 是设备 Access Token |
| 多客户端互相影响 | 同一个 Token 不要同时启动多个客户端 |

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
