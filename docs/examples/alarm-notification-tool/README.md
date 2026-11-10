# 告警与通知工具

> 中国中铁物联网平台文档集 · 示例代码

## 1. 概述

`alarm_notification_tool.py` 通过 ThingsBoard REST API 查询和处理告警，并预览或发送通知请求。

- 协议：**REST**
- 覆盖手册：告警与通知
- 默认地址：`http://localhost:8080`

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。

## 2. 环境要求

- Python 3.9+
- 租户管理员账号或有效 API Key
- 已配置通知模板和收件人组（发送通知时）

## 3. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 4. 快速开始

查询告警：

```powershell
python alarm_notification_tool.py --action list-alarms
```

确认告警：

```powershell
python alarm_notification_tool.py --action ack --alarm-id <ALARM_ID>
```

清除告警：

```powershell
python alarm_notification_tool.py --action clear --alarm-id <ALARM_ID>
```

指派告警：

```powershell
python alarm_notification_tool.py `
  --action assign `
  --alarm-id <ALARM_ID> `
  --assignee-id <USER_ID>
```

添加评论：

```powershell
python alarm_notification_tool.py `
  --action comment `
  --alarm-id <ALARM_ID> `
  --comment "已联系现场处理"
```

预览通知：

```powershell
python alarm_notification_tool.py `
  --action preview-notification `
  --payload .\notification.json
```

发送通知：

```powershell
python alarm_notification_tool.py `
  --action send-notification `
  --payload .\notification.json
```

## 5. 参数说明

| 参数 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `--tb-url` | `http://localhost:8080` | 否 | ThingsBoard 地址 |
| `--api-key` | 无 | 二选一 | ThingsBoard API Key |
| `--username` | `tenant@thingsboard.org` | 否 | 账号登录用户名 |
| `--password` | 无 | 二选一 | 密码；缺省时交互输入 |
| `--action` | 无 | 是 | `list-alarms` / `get-alarm` / `ack` / `clear` / `assign` / `comment` / `preview-notification` / `send-notification` / `list-targets` / `list-templates` |
| `--alarm-id` | 无 | 视操作 | 告警 ID |
| `--assignee-id` | 无 | 指派时 | 指派人用户 ID |
| `--comment` | 无 | 评论时 | 评论内容 |
| `--payload` | 无 | 通知时 | 通知请求 JSON 文件 |
| `--page-size` | `100` | 否 | 分页大小 |
| `--page` | `0` | 否 | 页码 |
| `--dry-run` | 关闭 | 否 | 只打印请求，不访问平台 |
| `--log-level` | `INFO` | 否 | 日志级别 |

## 6. 接口说明

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| GET | `/api/alarms` | 查询告警列表 |
| GET | `/api/alarm/{alarmId}` | 查询告警详情 |
| POST | `/api/alarm/{alarmId}/ack` | 确认告警 |
| POST | `/api/alarm/{alarmId}/clear` | 清除告警 |
| POST | `/api/alarm/{alarmId}/assign/{assigneeId}` | 指派告警 |
| POST | `/api/alarm/{alarmId}/comment` | 添加评论 |
| GET | `/api/notification/targets` | 查询收件人组 |
| GET | `/api/notification/templates` | 查询通知模板 |
| POST | `/api/notification/request/preview` | 预览通知 |
| POST | `/api/notification/request` | 发送通知 |

评论请求体：

```json
{
  "comment": {
    "text": "已联系现场处理"
  }
}
```

通知请求体以平台页面或 Swagger 为准，建议先从页面导出或复制一份 `notification.json`。

## 7. 常见问题

| 问题 | 排查 |
| --- | --- |
| `HTTP 401` | 账号无告警/通知权限 |
| 通知预览失败 | 检查 `notification.json` 格式、模板和收件人组 |
| 告警确认/清除失败 | 确认告警状态允许该操作 |
| 评论失败 | 评论内容不能为空 |
| 客户用户看不到告警 | 确认告警已分配给该客户或设为公开 |

## 8. 安全说明

- 仓库不保存任何真实 API Key 或密码。
- 通知内容可能包含业务数据，请妥善保管 `notification.json`。

## Java 运行方式

本示例提供独立的 Java Maven 工程，位于 `java/` 目录。

```powershell
cd java
mvn -q compile
mvn -q exec:java -Dexec.args="--action list-alarms"
```

- 需要 JDK 17+ 和 Maven。
- Java 版参数与 Python 版保持一致。
- `pom.xml` 已配置 `exec-maven-plugin`，可通过 `-Dexec.args` 传入参数。
