# 新厂家初次对接演示

本目录用于模拟一个新厂家第一次接入中国中铁物联网平台的完整流程。

> 本目录只包含文档、示例 JSON 和截图清单，不包含任何脚本。
>
> 平台侧操作全部通过系统页面或 HTTP API 完成。
>
> 设备侧数据上报使用 MQTT 客户端，例如 MQTTX。

## 1. 演示目标

完成以下闭环：

```text
创建厂家租户
  -> 初始化平台服务账号
  -> 创建并激活租户管理员
  -> 创建产品并导入 TSL
  -> 产品自动生效
  -> 创建设备并获取凭证
  -> MQTT 接入并上报遥测
  -> 在平台页面和 API 验证数据
```

## 2. 示例对象

| 对象 | 示例值 |
| --- | --- |
| 厂家/租户 | `示例新厂家` |
| 租户管理员 | `vendor-admin@example.com` |
| 产品 ID | `NEWVENDOR001` |
| 产品名称 | `示例环境监测终端` |
| 型号 | `NEWVENDOR001` |
| 设备名称 | `NEWVENDOR001-0001` |
| TSL 版本 | `1.0` |
| 站点编码 | `DEMO-SITE-001` |

## 3. 前置条件

- 平台已启动并可访问。
- `thing-model` 已启动并可访问。
- 已配置默认租户配置。
- 已配置默认资产配置。
- 系统管理员账号可登录。
- 如使用激活邮件，平台邮件服务已配置。
- 已准备 MQTT 客户端，例如 MQTTX。
- 已准备一个未使用的租户管理员邮箱。

## 4. 演示流程

| 阶段 | 内容 | 文档 |
| --- | --- | --- |
| 01 | 创建租户、初始化服务账号、创建并激活租户管理员 | [01-tenant-and-account.md](01-tenant-and-account.md) |
| 02 | 创建产品、导入 TSL、验证产品发布 | [02-product-and-tsl.md](02-product-and-tsl.md) |
| 03 | 创建设备、获取凭证、MQTT 接入 | [03-device-and-mqtt.md](03-device-and-mqtt.md) |
| 04 | 验证遥测、属性、告警和通知 | [04-verification.md](04-verification.md) |
| 05 | 常见问题、排障和清理 | [05-troubleshooting.md](05-troubleshooting.md) |

相关用户手册和平台文档见 [INDEX.md](INDEX.md)。

## 5. 验收清单

| 验收项 | 预期结果 |
| --- | --- |
| 租户创建 | 新厂家租户出现在租户列表 |
| 平台服务账号 | 初始化成功，账号可用于产品资源初始化 |
| 租户管理员 | 可登录，能看到产品菜单 |
| 产品创建 | 产品状态为已发布 |
| 产品发布 | 自动生成产品配置、产品资产、规则链 |
| 设备创建 | 设备使用产品对应的产品配置 |
| 设备凭证 | 可获取 Access Token |
| MQTT 连接 | 设备可连接平台 |
| 遥测上报 | 最新遥测可查询 |
| 设备属性 | 服务端属性可查询 |
| 告警 | 如配置告警规则，可生成告警 |
| 通知 | 如配置通知规则，可在收件箱看到通知 |

## 6. 安全提示

- 不要提交或截图真实 Access Token。
- 不要提交租户管理员密码。
- 不要把 JWT 写入文档或代码仓库。
- 演示完成后建议删除演示设备和演示产品。
- 删除租户前必须确认影响范围。
- 平台服务账号不要当作日常登录账号。

## 7. 文件说明

```text
demo/new-vendor-onboarding/
├── README.md
├── INDEX.md
├── 01-tenant-and-account.md
├── 02-product-and-tsl.md
├── 03-device-and-mqtt.md
├── 04-verification.md
├── 05-troubleshooting.md
├── assets/
│   ├── new-vendor-product.tsl.json
│   ├── telemetry-sample.json
│   ├── event-sample.json
│   ├── product-response-sample.json
│   └── screenshot-checklist.md
└── api/
    └── api-reference.md
```
