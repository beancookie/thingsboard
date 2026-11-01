# thing-model 实施进度

> 更新时间：2026-11-01
> 当前实现说明以 [docs/](../docs/) 和 [README.md](README.md) 为准，未实现能力见 [09-迁移测试与路线图](../docs/09-迁移测试与路线图.md)。

## 1. 总体状态

| 方向 | 状态 | 说明 |
| --- | --- | --- |
| 产品与 TSL | 完成 | ProductId 租户内唯一，TSL 版本、目录、压缩 schema 已实现 |
| ThingsBoard 同步 | 完成 | Device Profile、产品 Asset、规则链同步和失败记录 |
| 规则链 | 完成 | 按 ProductId 生成，校验遥测/事件并输出 Kafka |
| 产品前端 | 完成 | 列表、详情、创建/编辑、校验、同步 |
| 租户服务账号 | 完成 | 新建租户后自动创建并注册专用 TENANT_ADMIN |
| 设备开通 API | 未实现 | 当前由 ThingsBoard 或 Python 脚本注册设备 |
| 事件中心 | 未实现 | 没有 `plat_event`、通知和处置 |
| 台账与指标 | 未实现 | 没有组织树、工点、设备绑定和汇聚指标 |
| TDengine 入湖 | 外部实现 | 由 `thingsboard-ingest` 负责，不在本工程 |
| 开放 API / OTA / SDK | 未实现 | 无 `/open/v1`、OTA 封装、设备 SDK |

## 2. 已实现能力

### 产品与物模型

- 产品主数据与 TSL 版本持久化。
- 属性、事件、行为目录落表。
- JSON Schema 结构校验与业务校验。
- 压缩 TSL schema 生成。
- 产品创建、物模型更新、重新同步、目录查询、在线校验。
- 产品删除：有设备时拒绝，删除时级联清理物模型和独占 ThingsBoard 资源。

### ThingsBoard 同步

- 每个租户使用 `plat_vendor_account` 中的专用 `TENANT_ADMIN`。
- 幂等创建/更新 Device Profile。
- 创建/更新产品 Asset，写入 `tsl_json`、`tsl_schema` 和计数字段。
- 按 ProductId 创建/复用产品规则链，绑定 `defaultRuleChainId`。
- 同步失败写入 `plat_profile_binding.sync_result`，支持 `/sync` 重试。

### 规则链

- 14 个节点、14 条连接。
- 运行时校验属性类型、范围、必填、未知字段、枚举、int32、struct、报文大小、时间戳和事件。
- 合法遥测写 ThingsBoard 时序库。
- 非法数据不写时序库，只投递 `iot.invalid`。
- Kafka topic：
  - `iot.telemetry.normalized`
  - `iot.event.normalized`
  - `iot.invalid`

### 前端与权限

- 产品页面挂在 `/entities/products`，只允许 `TENANT_ADMIN`。
- `SYS_ADMIN` 不显示 Products 菜单，调用产品 API 返回 403。
- 租户详情页和新建租户成功后可自动初始化厂商服务账号。
- 前端通过 `/api/thing-model` 代理访问本服务。

### 工程与测试

- 独立 Spring Boot 工程，不加入 ThingsBoard 根 Maven reactor。
- Flyway V1/V2/V3，jOOQ 数据访问。
- `DatabaseGuard` 防止误连 ThingsBoard 数据库。
- 单元测试、Web Slice、Testcontainers 数据库测试、外部 ThingsBoard 集成测试。
- OpenAPI / Swagger UI。

## 3. 当前数据表

```text
plat_product
plat_product_tsl
plat_tsl_property
plat_tsl_event
plat_tsl_action
plat_profile_binding
plat_vendor_account
```

V3 之后产品相关表均包含 `tenant_id`，产品主键为 `(tenant_id, product_id)`。

## 4. 当前接口

```text
GET  /api/auth/me
GET  /api/products
GET  /api/products/{productId}
GET  /api/products/{productId}/thing-model
POST /api/products
PUT  /api/products/{productId}/thing-model
POST /api/products/{productId}/thing-model/validate
GET  /api/products/{productId}/catalog
POST /api/products/{productId}/sync
DELETE /api/products/{productId}

POST /api/admin/tenants/{tenantId}/account
POST /api/admin/tenants/{tenantId}/provision
POST /api/admin/tenants/{tenantId}/provision-auto
GET  /api/admin/tenants/{tenantId}/account
```

## 5. 主要未完成项

1. 后端设备批量开通与 Access Token 下发 API。
2. 组织树、项目/工点、设备绑定和汇聚指标。
3. `plat_event` 与事件中心。
4. 开放 API、WebSocket、AK/SK。
5. OTA、远程配置、影子、NTP 和设备 SDK。
6. JT/T808、HTTPS、CoAP 接入。
7. 生产级限流、审计、监控和备份演练。
8. 产品弃用、回滚、灰度和异步同步任务。

## 6. 常用命令

```powershell
# 单元/切片测试
mvn -f thing-model/pom.xml test "-Dtest=!*IntegrationTest"

# 数据库集成测试
mvn -f thing-model/pom.xml test -Dtest=RepositoryIntegrationTest

# 外部 ThingsBoard 集成测试
mvn -f thing-model/pom.xml test -Dtest=ProductRuleChainTbIntegrationTest

# 全部测试
mvn -f thing-model/pom.xml test

# 启动
mvn -f thing-model/pom.xml spring-boot:run
```
