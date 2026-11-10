# 示例代码

> 中国中铁物联网平台文档集 · 示例代码

本目录提供可直接运行的 Python 示例，与「用户手册」配合使用。
示例统一遵循 [Python 示例代码规范](_standards.md)，只通过命令行参数配置，不内置任何密钥。

每个示例同时提供独立的 Java Maven 工程，位于各示例的 `java/` 目录，可在示例页「Java 代码」页签查看。

## 示例列表

| 示例 | 说明 | 分类 |
| --- | --- | --- |
| [DLT645 电表 MQTT 模拟器](dlt645-meter-simulator/README.md) | 模拟电表上报遥测与事件，处理共享属性和 RPC | 设备接入 / MQTT |
| [DLT645 电表 HTTP 模拟器](dlt645-meter-http/README.md) | 通过 HTTP 上报电表遥测与事件，处理共享属性和 RPC | 设备接入 / HTTP |
| [DLT645 电表 CoAP 模拟器](dlt645-meter-coap/README.md) | 通过 CoAP 上报电表遥测与事件，Observe 共享属性和 RPC | 设备接入 / CoAP |
| [设备下行接收示例](device-downlink-client/README.md) | 订阅共享属性与 RPC，处理平台下发命令 | 设备接入 / MQTT |
| [设备批量注册工具](device-bulk-registrar/README.md) | 批量创建设备、获取凭证并绑定网关 | 设备接入 |
| [网关子设备 MQTT 模拟器](gateway-subdevice-simulator/README.md) | 模拟子设备上线、遥测、属性与下线 | 设备接入 |
| [物模型产品导出工具](thing-model-product-exporter/README.md) | 导出产品列表与完整 TSL 物模型 | 产品管理 |
| [产品增删改查工具](product-crud-tool/README.md) | 产品查询、创建、更新、TSL 校验与删除 | 产品管理 |
| [设备增删改查工具](device-crud-tool/README.md) | 设备查询、创建、更新、删除与凭证查询 | 产品管理 |
| [网关与子设备配置工具](gateway-config-tool/README.md) | 网关/子设备创建、关系绑定、状态与配置 | 产品管理 |
| [规则链增删改查工具](rulechain-crud-tool/README.md) | 规则链 CRUD、元数据、根规则链与导入导出 | 产品管理 |
| [租户初始化工具](tenant-provisioner/README.md) | 创建租户、管理员并初始化平台服务账号 | 组织与权限 |
| [客户与用户初始化工具](customer-user-provisioner/README.md) | 创建客户、客户用户并分配资源 | 组织与权限 |
| [告警与通知工具](alarm-notification-tool/README.md) | 查询处理告警，预览和发送通知 | 规则与告警 |
| [计算字段管理工具](calculated-field-manager/README.md) | 计算字段 CRUD、脚本测试与调试 | 规则与告警 |
| [物模型 TSL 校验工具](tsl-validator/README.md) | 离线校验 TSL 结构与字段规范 | 开发辅助 |

## 目录约定

```text
docs/examples/
├── README.md
├── _standards.md
├── examples.json
├── dlt645-meter-simulator/
├── dlt645-meter-http/
├── dlt645-meter-coap/
├── device-downlink-client/
├── device-bulk-registrar/
├── gateway-subdevice-simulator/
├── thing-model-product-exporter/
├── product-crud-tool/
├── device-crud-tool/
├── gateway-config-tool/
├── rulechain-crud-tool/
├── tenant-provisioner/
├── customer-user-provisioner/
├── alarm-notification-tool/
├── calculated-field-manager/
└── tsl-validator/
```

## 新增示例流程

1. 在 `docs/examples/` 下创建 `<example-slug>/` 目录。
2. 按 [Python 示例代码规范](_standards.md) 编写入口脚本、`README.md` 和 `requirements.txt`。
3. 在 `examples.json` 的 `examples` 数组中增加一条元数据。
4. 在本文件的「示例列表」中增加一行。
5. 运行 `python -m py_compile` 与 `--help` 验证脚本。
6. 刷新「用户手册」页面左侧的「示例代码」分组即可看到新示例。

## examples.json 字段

| 字段 | 说明 |
| --- | --- |
| `id` | 示例唯一标识，用于 `?example=<id>` 直达 |
| `title` | 页面显示标题 |
| `description` | 一句话说明 |
| `category` | 分类 |
| `readme` | 使用说明 Markdown 路径（相对 `/assets/docs/`） |
| `entry` | 入口脚本路径 |
| `files` | 源代码页可查看的文件列表 |

`files` 中每一项包含：

| 字段 | 说明 |
| --- | --- |
| `name` | 显示文件名 |
| `path` | 文件路径（相对 `/assets/docs/`） |
| `language` | 代码高亮语言，例如 `python`、`markdown`、`json`、`text` |
