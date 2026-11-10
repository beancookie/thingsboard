# 租户初始化工具

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`tenant_provisioner.py` 通过 ThingsBoard REST API 创建租户、租户管理员，并初始化平台服务账号。

- 协议：**REST**
- 覆盖手册：租户管理
- 默认地址：`http://localhost:8080`

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。

## 2. 环境要求

- Python 3.9+
- 系统管理员账号或有效 API Key
- 可访问 ThingsBoard 与 thing-model 服务

## 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 4. 快速开始

查询租户列表：

```powershell
python tenant_provisioner.py --action list
```

创建租户：

```powershell
python tenant_provisioner.py `
  --action create `
  --tenant-name "示例租户" `
  --email tenant@example.com
```

创建租户管理员（发送激活邮件）：

```powershell
python tenant_provisioner.py `
  --action create-admin `
  --tenant-id <TENANT_ID> `
  --email admin@example.com `
  --send-activation-mail
```

初始化平台服务账号：

```powershell
python tenant_provisioner.py --action provision --tenant-id <TENANT_ID>
```

删除租户：

```powershell
python tenant_provisioner.py --action delete --tenant-id <TENANT_ID>
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--tb-url` | `http://localhost:8080` | 否 | ThingsBoard 地址 |
| `--thingmodel-url` | `http://localhost:8080/api/thing-model` | 否 | thing-model 地址 |
| `--api-key` | 无 | 二选一 | 系统管理员 API Key |
| `--username` | `sysadmin@thingsboard.org` | 否 | 系统管理员用户名 |
| `--password` | 无 | 二选一 | 密码；缺省时交互输入 |
| `--action` | 无 | 是 | `list` / `get` / `create` / `create-admin` / `provision` / `delete` |
| `--tenant-id` | 无 | 视操作 | 租户 ID |
| `--tenant-name` | 无 | 创建时 | 租户名称 |
| `--profile-id` | 默认租户配置 | 否 | 租户配置 ID |
| `--email` | 无 | 创建管理员时 | 管理员邮箱 |
| `--first-name` | `Tenant` | 否 | 管理员名 |
| `--last-name` | `Admin` | 否 | 管理员姓 |
| `--country` / `--city` / `--phone` | 无 | 否 | 联系信息 |
| `--description` | 无 | 否 | 描述 |
| `--send-activation-mail` | 关闭 | 否 | 创建管理员时发送激活邮件 |
| `--show-activation-link` | 关闭 | 否 | 创建管理员后输出激活链接 |
| `--force` | 关闭 | 否 | 强制重新初始化服务账号 |
| `--dry-run` | 关闭 | 否 | 只打印请求，不访问平台 |
| `--log-level` | `INFO` | 否 | 日志级别 |

## 6. 接口说明

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| GET | `/api/tenants` | 查询租户列表 |
| GET | `/api/tenant/{tenantId}` | 查询租户详情 |
| POST | `/api/tenant` | 创建或更新租户 |
| DELETE | `/api/tenant/{tenantId}` | 删除租户 |
| POST | `/api/user?sendActivationMail=...` | 创建租户管理员 |
| GET | `/api/user/{userId}/activationLink` | 获取激活链接 |
| GET | `/api/tenantProfileInfo/default` | 查询默认租户配置 |
| POST | `/api/thing-model/admin/tenants/{tenantId}/provision-auto` | 初始化平台服务账号 |

创建租户请求体示例：

```json
{
  "title": "示例租户",
  "tenantProfileId": {
    "entityType": "TENANT_PROFILE",
    "id": "<TENANT_PROFILE_ID>"
  },
  "email": "tenant@example.com"
}
```

## 7. 常见问题

| 问题 | 排查 |
| --- | --- |
| `HTTP 401` | 需要系统管理员权限 |
| 创建租户失败 | 确认租户配置 ID 存在 |
| 服务账号初始化失败 | 检查 thing-model 服务和平台配置 |
| 管理员收不到邮件 | 未配置邮件服务时使用 `--show-activation-link` |
| 删除失败 | 租户下可能仍有资源，先评估并备份 |

## 8. 安全说明

- 仓库不保存任何真实 API Key 或密码。
- 租户删除不可恢复，请先备份配置和数据。

## Java 运行方式

本示例提供独立的 Java Maven 工程，位于 `java/` 目录。

```powershell
cd java
mvn -q compile
mvn -q exec:java -Dexec.args="--action list"
```

- 需要 JDK 17+ 和 Maven。
- Java 版参数与 Python 版保持一致。
- `pom.xml` 已配置 `exec-maven-plugin`，可通过 `-Dexec.args` 传入参数。
