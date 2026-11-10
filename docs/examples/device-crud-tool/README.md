# 设备增删改查工具

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`device_crud_tool.py` 通过 ThingsBoard REST API 完成设备查询、创建、更新、删除和凭证查询。

- 协议：**REST**
- 覆盖手册：设备管理
- 默认地址：`http://localhost:8080`

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。

## 2. 环境要求

- Python 3.9+
- 可访问 ThingsBoard 服务
- 租户管理员账号或有效 API Key
- 已准备好设备配置（Device Profile）ID

## 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 4. 快速开始

查询设备列表：

```powershell
python device_crud_tool.py --action list
```

按 ID 查询设备：

```powershell
python device_crud_tool.py --action get --device-id <DEVICE_ID>
```

按名称查询：

```powershell
python device_crud_tool.py --action get --device-name device-01
```

创建设备：

```powershell
python device_crud_tool.py `
  --action create `
  --name device-01 `
  --profile-id <DEVICE_PROFILE_ID> `
  --label 环境监测设备
```

创建网关设备：

```powershell
python device_crud_tool.py `
  --action create `
  --name gateway-01 `
  --profile-id <DEVICE_PROFILE_ID> `
  --gateway
```

更新设备描述：

```powershell
python device_crud_tool.py `
  --action update `
  --device-name device-01 `
  --description "1 号站点环境监测设备"
```

查询凭证：

```powershell
python device_crud_tool.py --action credentials --device-name device-01
```

删除设备：

```powershell
python device_crud_tool.py --action delete --device-name device-01
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--tb-url` | `http://localhost:8080` | 否 | ThingsBoard 地址 |
| `--timeout` | `30` | 否 | HTTP 超时秒数 |
| `--api-key` | 无 | 二选一 | ThingsBoard API Key |
| `--username` | `tenant@thingsboard.org` | 否 | 账号登录用户名 |
| `--password` | 无 | 二选一 | 账号登录密码；缺省时交互输入 |
| `--action` | 无 | 是 | `list` / `get` / `create` / `update` / `delete` / `credentials` |
| `--device-id` | 无 | 视操作 | 设备 ID |
| `--device-name` | 无 | 视操作 | 设备名称 |
| `--name` | 无 | 创建时 | 新设备名称 |
| `--profile-id` | 无 | 创建时 | 设备配置 ID |
| `--label` | 无 | 否 | 设备标签 |
| `--gateway` | 关闭 | 否 | 标记为网关设备 |
| `--description` | 无 | 否 | 设备描述 |
| `--config` | 无 | 否 | 创建/更新的 JSON 配置文件 |
| `--page-size` | `100` | 否 | 分页大小 |
| `--page` | `0` | 否 | 页码 |
| `--dry-run` | 关闭 | 否 | 只打印请求，不访问平台 |
| `--log-level` | `INFO` | 否 | 日志级别 |

## 6. 接口说明

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| GET | `/api/tenant/devices` | 查询设备列表 |
| GET | `/api/tenant/devices?deviceName={name}` | 按名称查询设备 |
| GET | `/api/device/{deviceId}` | 查询设备详情 |
| POST | `/api/device` | 创建或更新设备 |
| DELETE | `/api/device/{deviceId}` | 删除设备 |
| GET | `/api/device/{deviceId}/credentials` | 查询设备凭证 |

创建设备请求体示例：

```json
{
  "name": "device-01",
  "type": "default",
  "deviceProfileId": {
    "entityType": "DEVICE_PROFILE",
    "id": "<DEVICE_PROFILE_ID>"
  },
  "label": "环境监测设备",
  "additionalInfo": {
    "gateway": true,
    "description": "设备描述"
  }
}
```

## 7. 常见问题

| 问题 | 排查 |
| --- | --- |
| `HTTP 401` | API Key 或账号密码无效 |
| 创建失败 | 确认 `--profile-id` 存在且属于当前租户 |
| 设备已存在 | 设备名称租户内唯一，改用其他名称或先删除 |
| 删除失败 | 设备可能被规则链、仪表板或客户引用 |
| 凭证为空 | 设备凭证类型可能不是 Access Token |

## 8. 安全说明

- 仓库不保存任何真实 API Key、密码或设备 Token。
- 删除设备前请确认没有关联资源。

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
