# 网关与子设备配置工具

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`gateway_config_tool.py` 通过 ThingsBoard REST API 创建网关/子设备、建立 `Contains` 关系、
查询网关在线状态，并写入网关 `general_configuration` 配置。

- 协议：**REST**
- 覆盖手册：网关功能
- 默认地址：`http://localhost:8080`

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。

## 2. 环境要求

- Python 3.9+
- 可访问 ThingsBoard 服务
- 租户管理员账号或有效 API Key
- 已准备网关与子设备的设备配置（Device Profile）ID

## 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 4. 快速开始

创建网关设备：

```powershell
python gateway_config_tool.py `
  --action create-gateway `
  --gateway-name gateway-01 `
  --profile-id <DEVICE_PROFILE_ID>
```

创建子设备：

```powershell
python gateway_config_tool.py `
  --action create-sub-device `
  --sub-device-name sub-device-01 `
  --profile-id <DEVICE_PROFILE_ID>
```

绑定子设备：

```powershell
python gateway_config_tool.py `
  --action bind `
  --gateway-name gateway-01 `
  --sub-device-name sub-device-01
```

查询网关列表：

```powershell
python gateway_config_tool.py --action list
```

查询网关在线状态：

```powershell
python gateway_config_tool.py --action status --gateway-name gateway-01
```

写入网关配置：

```powershell
python gateway_config_tool.py `
  --action set-config `
  --gateway-name gateway-01 `
  --config .\gateway-general-configuration.json
```

读取网关配置：

```powershell
python gateway_config_tool.py --action get-config --gateway-name gateway-01
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--tb-url` | `http://localhost:8080` | 否 | ThingsBoard 地址 |
| `--timeout` | `30` | 否 | HTTP 超时秒数 |
| `--api-key` | 无 | 二选一 | ThingsBoard API Key |
| `--username` | `tenant@thingsboard.org` | 否 | 账号登录用户名 |
| `--password` | 无 | 二选一 | 账号登录密码；缺省时交互输入 |
| `--action` | 无 | 是 | `create-gateway` / `create-sub-device` / `bind` / `list` / `status` / `set-config` / `get-config` |
| `--gateway-name` | 无 | 视操作 | 网关设备名称 |
| `--gateway-id` | 无 | 视操作 | 网关设备 ID |
| `--sub-device-name` | 无 | 视操作 | 子设备名称 |
| `--profile-id` | 无 | 创建时 | 设备配置 ID |
| `--relation-type` | `Contains` | 否 | 网关与子设备的关系类型 |
| `--config` | 无 | 写入配置时 | `general_configuration` JSON 文件 |
| `--dry-run` | 关闭 | 否 | 只打印请求，不访问平台 |
| `--log-level` | `INFO` | 否 | 日志级别 |

## 6. 接口说明

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| POST | `/api/device` | 创建网关/子设备 |
| GET | `/api/tenant/devices` | 查询设备列表 |
| GET | `/api/tenant/devices?deviceName={name}` | 按名称查询设备 |
| POST | `/api/relation` | 建立网关 `Contains` 子设备关系 |
| GET | `/api/plugins/telemetry/DEVICE/{gatewayId}/values/attributes` | 查询状态/配置属性 |
| POST | `/api/plugins/telemetry/DEVICE/{gatewayId}/attributes/SHARED_SCOPE` | 写入共享属性 |

创建网关请求体：

```json
{
  "name": "gateway-01",
  "type": "default",
  "deviceProfileId": {
    "entityType": "DEVICE_PROFILE",
    "id": "<DEVICE_PROFILE_ID>"
  },
  "additionalInfo": {
    "gateway": true
  }
}
```

写入配置请求体：

```json
{
  "general_configuration": {
    "connectors": []
  }
}
```

## 7. 常见问题

| 问题 | 排查 |
| --- | --- |
| 子设备未显示 | 确认已执行 `bind` 且关系类型为 `Contains` |
| `gatewaySessionHandler is null` | 确认网关设备已开启 `additionalInfo.gateway=true` |
| 状态一直离线 | 网关需通过 MQTT 实际连接并上报状态 |
| 配置未生效 | 确认写入的是 `SHARED_SCOPE`，网关上线后会收到共享属性 |
| 创建失败 | 检查 `--profile-id` 与设备名称是否有效 |

## 8. 安全说明

- 仓库不保存任何真实 API Key 或密码。
- 网关配置可能包含连接器凭证，请妥善保管配置文件。

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
