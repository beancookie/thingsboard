# 客户与用户初始化工具

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`customer_user_provisioner.py` 通过 ThingsBoard REST API 创建客户、客户用户，并把设备或资产分配给客户。

- 协议：**REST**
- 覆盖手册：客户与用户
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

查询客户列表：

```powershell
python customer_user_provisioner.py --action list-customers
```

创建客户：

```powershell
python customer_user_provisioner.py `
  --action create-customer `
  --customer-name "示例客户" `
  --email customer@example.com
```

创建客户用户：

```powershell
python customer_user_provisioner.py `
  --action create-user `
  --customer-id <CUSTOMER_ID> `
  --email user@example.com `
  --send-activation-mail
```

分配设备：

```powershell
python customer_user_provisioner.py `
  --action assign-device `
  --customer-id <CUSTOMER_ID> `
  --device-id <DEVICE_ID>
```

分配资产：

```powershell
python customer_user_provisioner.py `
  --action assign-asset `
  --customer-id <CUSTOMER_ID> `
  --asset-id <ASSET_ID>
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--tb-url` | `http://localhost:8080` | 否 | ThingsBoard 地址 |
| `--api-key` | 无 | 二选一 | ThingsBoard API Key |
| `--username` | `tenant@thingsboard.org` | 否 | 租户管理员用户名 |
| `--password` | 无 | 二选一 | 密码；缺省时交互输入 |
| `--action` | 无 | 是 | `list-customers` / `create-customer` / `create-user` / `list-users` / `assign-device` / `assign-asset` / `delete-customer` |
| `--customer-id` | 无 | 视操作 | 客户 ID |
| `--customer-name` | 无 | 创建时 | 客户名称 |
| `--email` | 无 | 创建用户时 | 用户邮箱 |
| `--first-name` / `--last-name` | `Customer` / `User` | 否 | 用户名和姓 |
| `--country` / `--city` / `--phone` | 无 | 否 | 联系信息 |
| `--description` | 无 | 否 | 描述 |
| `--device-id` | 无 | 分配设备时 | 设备 ID |
| `--asset-id` | 无 | 分配资产时 | 资产 ID |
| `--send-activation-mail` | 关闭 | 否 | 创建用户时发送激活邮件 |
| `--show-activation-link` | 关闭 | 否 | 创建用户后输出激活链接 |
| `--page-size` | `100` | 否 | 分页大小 |
| `--page` | `0` | 否 | 页码 |
| `--dry-run` | 关闭 | 否 | 只打印请求，不访问平台 |
| `--log-level` | `INFO` | 否 | 日志级别 |

## 6. 接口说明

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| GET | `/api/customers` | 查询客户列表 |
| POST | `/api/customer` | 创建或更新客户 |
| DELETE | `/api/customer/{customerId}` | 删除客户 |
| POST | `/api/user?sendActivationMail=...` | 创建客户用户 |
| GET | `/api/customer/{customerId}/users` | 查询客户用户 |
| POST | `/api/customer/{customerId}/device/{deviceId}` | 分配设备 |
| POST | `/api/customer/{customerId}/asset/{assetId}` | 分配资产 |

创建客户请求体示例：

```json
{
  "title": "示例客户",
  "email": "customer@example.com"
}
```

创建客户用户请求体示例：

```json
{
  "customerId": {
    "entityType": "CUSTOMER",
    "id": "<CUSTOMER_ID>"
  },
  "email": "user@example.com",
  "firstName": "Customer",
  "lastName": "User",
  "authority": "CUSTOMER_USER"
}
```

## 7. 常见问题

| 问题 | 排查 |
| --- | --- |
| `HTTP 401` | 需要租户管理员权限 |
| 创建用户失败 | 邮箱必须唯一；检查客户 ID |
| 收不到激活邮件 | 未配置邮件服务时使用 `--show-activation-link` |
| 分配失败 | 确认设备/资产存在且属于当前租户 |
| 删除客户失败 | 先取消设备、资产、仪表板分配 |

## 8. 安全说明

- 仓库不保存任何真实 API Key 或密码。
- 删除客户前请确认用户和资源是否需要保留。

## Java 运行方式

本示例提供独立的 Java Maven 工程，位于 `java/` 目录。

```powershell
cd java
mvn -q compile
mvn -q exec:java -Dexec.args="--action list-customers"
```

- 需要 JDK 17+ 和 Maven。
- Java 版参数与 Python 版保持一致。
- `pom.xml` 已配置 `exec-maven-plugin`，可通过 `-Dexec.args` 传入参数。
