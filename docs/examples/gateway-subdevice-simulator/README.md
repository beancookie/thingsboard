# 网关子设备 MQTT 模拟器

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`gateway_subdevice_simulator.py` 使用网关设备 Access Token 连接 ThingsBoard MQTT，
模拟多个子设备上线、上报遥测和属性，退出时发送下线消息。

对应手册：[网关功能使用手册](../../manuals/网关功能使用手册.md)。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。

## 2. 环境要求

- Python 3.9+
- 可访问 ThingsBoard MQTT 端口（默认 `1883`，TLS 通常为 `8883`）
- 已创建网关设备并获取 Access Token
- 子设备已在平台注册
- 网关设备与子设备已建立 `Contains` 关系

## 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 4. 快速开始

先打印示例报文，不连接 MQTT：

```powershell
python gateway_subdevice_simulator.py `
  --sub-device sub-device-01 `
  --sub-device sub-device-02 `
  --dry-run
```

连接平台模拟 3 个子设备，持续上报：

```powershell
python gateway_subdevice_simulator.py `
  --mqtt-host <MQTT_HOST> `
  --mqtt-port 1883 `
  --gateway-name gateway-01 `
  --gateway-token <GATEWAY_ACCESS_TOKEN> `
  --sub-device sub-device-01 `
  --sub-device sub-device-02 `
  --sub-device sub-device-03 `
  --interval 5
```

从设备注册 CSV 读取子设备：

```powershell
python gateway_subdevice_simulator.py `
  --mqtt-host <MQTT_HOST> `
  --gateway-token <GATEWAY_ACCESS_TOKEN> `
  --sub-devices-csv .\device-output\device-credentials.csv `
  --interval 5 --count 10
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--mqtt-host` | `127.0.0.1` | 否 | MQTT 服务地址 |
| `--mqtt-port` | `1883` | 否 | MQTT 服务端口 |
| `--gateway-token` | 无 | 连接是 | 网关设备 Access Token；`--dry-run` 时可省略 |
| `--gateway-name` | `gateway-01` | 否 | 网关名称，同时作为 MQTT Client ID |
| `--keepalive` | `60` | 否 | MQTT Keepalive 秒数 |
| `--qos` | `1` | 否 | MQTT QoS，可选 `0` / `1` / `2` |
| `--tls` | 关闭 | 否 | 启用 TLS |
| `--ca-cert` | 无 | 否 | TLS CA 证书路径 |
| `--sub-devices-csv` | 无 | 二选一 | 子设备 CSV |
| `--sub-device` | 无 | 二选一 | 子设备名称，可重复 |
| `--device-type` | `default` | 否 | 子设备类型（网关上报的 `type`） |
| `--interval` | `5` | 否 | 遥测上报间隔（秒） |
| `--count` | `0` | 否 | 上报轮次，`0` 表示持续运行 |
| `--publish-attributes` | 关闭 | 否 | 子设备上线时同时上报属性 |
| `--seed` | 无 | 否 | 随机数种子 |
| `--dry-run` | 关闭 | 否 | 只打印示例报文，不连接 MQTT |
| `--log-level` | `INFO` | 否 | 日志级别 |

子设备 CSV 字段：

- `device_name`：子设备名称（必填）；
- `device_type` / `product_id` / `profile_name`：子设备类型（可选）。

## 6. MQTT 主题与报文

| 主题 | 方向 | 用途 |
| --- | --- | --- |
| `v1/gateway/connect` | 上行 | 子设备上线 |
| `v1/gateway/disconnect` | 上行 | 子设备下线 |
| `v1/gateway/telemetry` | 上行 | 子设备遥测 |
| `v1/gateway/attributes` | 上行 | 子设备属性 |

子设备上线：

```json
{
  "device": "sub-device-01",
  "type": "default"
}
```

子设备遥测：

```json
{
  "sub-device-01": [
    {
      "ts": 1790000000000,
      "values": {
        "temperature": 25.6,
        "humidity": 60,
        "voltage": 220.1,
        "current": 3.2,
        "status": "online"
      }
    }
  ]
}
```

子设备属性：

```json
{
  "sub-device-01": {
    "device_type": "default",
    "gateway": true,
    "status": "online"
  }
}
```

子设备下线：

```json
{
  "device": "sub-device-01"
}
```

## 7. 输出说明

- 日志输出到标准错误，包含连接信息、子设备上线/下线与轮次汇总。
- `--dry-run` 输出完整示例报文，便于核对格式。
- 网关令牌在日志中自动脱敏。

## 8. 常见问题

| 问题 | 排查 |
| --- | --- |
| `gatewaySessionHandler is null` | 确认网关设备已开启「是否网关」 |
| 子设备未显示 | 确认网关与子设备已建立 `Contains` 关系 |
| 遥测无数据 | 确认子设备已注册，且 `type` 与设备配置匹配 |
| 连接被踢下线 | 同一网关 Token 不要同时启动多个客户端 |
| 断线后子设备离线 | 脚本退出时会发送下线消息，重连后重新上线 |

## 9. 安全说明

- 仓库不保存任何真实网关或子设备 Token。
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
