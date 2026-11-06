# thing-model

产品与物模型服务。独立 Spring Boot 工程，通过 `thingsboard-pe-client` 调用 ThingsBoard REST API，不修改 ThingsBoard 源码，也不加入 ThingsBoard 根 Maven reactor。

实施进度见 [PROGRESS.md](PROGRESS.md)。

## 环境要求

- JDK 25（与 ThingsBoard 4.4 一致）
- Maven 3.9+
- PostgreSQL 14+
- ThingsBoard 4.4.x

## 构建与测试

```bash
mvn -f thing-model/pom.xml test
```

集成测试 `ProductRuleChainTbIntegrationTest` 会连接现有 ThingsBoard（默认 `http://localhost:18080`，账号 `tenant@thingsboard.org / tenant`、`sysadmin@thingsboard.org / sysadmin`），并用 Testcontainers 启动独立的 thing-model 数据库。可通过 `TB_URL`、`TB_USERNAME`、`TB_PASSWORD`、`TB_SYSADMIN_USERNAME`、`TB_SYSADMIN_PASSWORD` 覆盖。

该测试默认保留 ThingsBoard 中的 `E2E_RULE_CHAIN` 规则链、Device Profile 和 Asset，便于运行后直接检查；产品记录位于临时 Testcontainers Postgres，测试结束即销毁。测试会打印保留资源的 ID。

### 测试分层

集成测试与业务代码同包：

- `db.RepositoryIntegrationTest`：使用 Testcontainers Postgres
- `product.ProductRuleChainTbIntegrationTest`：连接现有 ThingsBoard
- 其余单元测试与 Web Slice：不依赖 Docker 和 ThingsBoard

```bash
# 全部测试（默认包含外部 ThingsBoard 集成测试）
mvn -f thing-model/pom.xml test

# 只跑单个集成测试
mvn -f thing-model/pom.xml test -Dtest=ProductRuleChainTbIntegrationTest
mvn -f thing-model/pom.xml test -Dtest=RepositoryIntegrationTest

# 只跑单元/切片测试
mvn -f thing-model/pom.xml test -Dtest='!*IntegrationTest'
```

只编译：

```bash
mvn -f thing-model/pom.xml -DskipTests compile
```

## 数据模拟

`scripts/` 提供 Python 模拟上报脚本，会自动创建测试设备、写入物模型属性并循环发送遥测、事件和非法数据：

```bash
python -m pip install -r tools/src/main/python/simulators/requirements.txt
python tools/src/main/python/simulators/simulate_telemetry.py --mode mixed --count 10
```

详细说明见 [tools/src/main/python/simulators/README.md](../tools/src/main/python/simulators/README.md)。

## 前端代理

`ui-ngx` 通过 `/api/thing-model` 访问本服务：

- 开发环境：`ui-ngx/proxy.conf.js` 将 `/api/thing-model` 转发到 `http://localhost:8090`，并重写为 `/api`
- 生产环境：需要在 Nginx/HAProxy 配置同样的转发规则

## 配置

`src/main/resources/application.yml` 支持以下环境变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SPRING_DATASOURCE_URL` | `jdbc:postgresql://localhost:5432/thingmodel` | 平台库 |
| `SPRING_DATASOURCE_USERNAME` | `postgres` | 数据库用户 |
| `SPRING_DATASOURCE_PASSWORD` | `postgres` | 数据库密码 |
| `THINGMODEL_DB_NAME` | `thingmodel` | 启动时校验的数据库名 |
| `THINGMODEL_DB_SCHEMA` | 空 | 独立库模式不设置；共用库时设为 `thingmodel` |
| `THINGMODEL_TB_URL` | `http://localhost:18080` | ThingsBoard 地址 |
| `THINGMODEL_SECRET_KEY` | 空 | AES-GCM 密钥，Base64 编码，16/24/32 字节 |
| `THINGMODEL_SERVICE_ACCOUNT_EMAIL_DOMAIN` | `thing-model.local` | 自动创建租户服务账号时使用的邮箱域名 |
| `THINGMODEL_KAFKA_BOOTSTRAP` | `kafka-test1:9095,kafka-test2:9095,kafka-test3:9095` | 规则链 Kafka bootstrap servers |
| `THINGMODEL_CORS_ALLOWED_ORIGINS` | `*` | 允许的跨域来源，逗号分隔，支持 `*` 与通配模式 |
| `THINGMODEL_CORS_ALLOW_CREDENTIALS` | `false` | 是否允许跨域携带 Cookie；JWT 走 `X-Authorization`，一般无需开启 |
| `THINGMODEL_CORS_MAX_AGE` | `3600` | 预检结果缓存秒数 |

默认允许所有来源；生产环境建议通过 `THINGMODEL_CORS_ALLOWED_ORIGINS=https://a.com,https://b.com` 收紧白名单。

### 数据库拓扑

默认使用**同一实例、独立 database**：

```text
PostgreSQL:5432
├── thingsboard   ThingsBoard 元数据
└── thingmodel    thing-model 的 plat_* 与 flyway_schema_history
```

独立库配置：

```text
SPRING_DATASOURCE_URL=jdbc:postgresql://<host>:5432/thingmodel
SPRING_DATASOURCE_USERNAME=thing_model
SPRING_DATASOURCE_PASSWORD=<password>
THINGMODEL_DB_NAME=thingmodel
```

- `thingmodel` 库与 ThingsBoard 完全隔离。
- `DatabaseGuard` 校验 `current_database()`，拒绝误连 `thingsboard`。
- thing-model 只通过 REST 访问 ThingsBoard，不跨库 JOIN。

初始化独立数据库：

```bash
psql -h <host> -p 5432 -U postgres -d postgres \
  -v thing_model_password='<password>' \
  -f thing-model/deploy/postgres/init-thingmodel.sql
```

也可选用**同库 + 独立 schema** 模式：

```text
PostgreSQL:5432
└── thingsboard
    ├── public       ThingsBoard 元数据
    └── thingmodel   thing-model 的 plat_* 与 flyway_schema_history
```

```text
SPRING_DATASOURCE_URL=jdbc:postgresql://<host>:5432/thingsboard
THINGMODEL_DB_NAME=thingsboard
THINGMODEL_DB_SCHEMA=thingmodel
```

```bash
psql -h <host> -p 5432 -U postgres -d thingsboard \
  -v thing_model_password='<password>' \
  -f thing-model/deploy/postgres/init-thingmodel-schema.sql
```

### Kafka 与规则链

规则链使用外部 Kafka：

```text
kafka-test1:9095,kafka-test2:9095,kafka-test3:9095
```

需要预先创建三个 topic：

```text
iot.telemetry.normalized
iot.event.normalized
iot.invalid
```

产品发布/同步时会生成规则链，名称直接使用 ProductId：

```text
<ProductId>
```

并绑定到对应 `DeviceProfile.defaultRuleChainId`。存量 `auto_<ProductId>_telemetry` 规则链会在下次发布/同步时自动复用并重命名为 ProductId。生成规则链时会把当前产品录入的压缩 TSL schema 内嵌到校验脚本，运行时按属性与事件校验；非法数据不写 ThingsBoard 时序库，只投递 `iot.invalid`。TSL 变更后重新发布或调用 `/sync` 即可刷新规则链。

配置项：

```yaml
thingmodel:
  rulechain:
    enabled: true
    kafka-bootstrap: kafka-test1:9095,kafka-test2:9095,kafka-test3:9095
    topic-telemetry: iot.telemetry.normalized
    topic-event: iot.event.normalized
    topic-invalid: iot.invalid
    key-pattern: "$[deviceName]"
```

Kafka 地址不在代码中写死，统一从 `thingmodel.rulechain.kafka-bootstrap` 或环境变量 `THINGMODEL_KAFKA_BOOTSTRAP` 读取。

生成密钥（PowerShell）：

```powershell
$key = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($key)
[Convert]::ToBase64String($key)
```

数据库建好后启动服务，Flyway 会自动执行 V1/V2/V3/V4 并创建 `plat_*` 表。产品主键为 `(tenant_id, product_id)`，ProductId 额外受全系统唯一约束：

```bash
mvn -f thing-model/pom.xml spring-boot:run
```

服务默认监听 `8090`，健康检查：

```bash
curl http://localhost:8090/actuator/health
```

OpenAPI 文档：

```text
http://localhost:8090/swagger-ui.html
```

Swagger UI 中先通过 `Authorize` 填入 ThingsBoard JWT。

## 请求上下文与权限

- Controller 统一继承 `controller/BaseController`，通过 `getCurrentUser()` / `requireTenantId()` 获取当前用户与租户。
- `auth/RequireAuthority` 是声明式权限注解，由 `AuthInterceptor` 在进入 Controller 前校验。
- 产品页面和产品 API 只允许 `TENANT_ADMIN`，产品租户来自 JWT。`SYS_ADMIN` 不显示产品菜单，也不能访问产品页面/API。
- 产品数据按 `(tenant_id, product_id)` 隔离；ProductId 全系统唯一，不同租户也不能重复。
- 当前没有独立的租户写入解析组件；租户隔离由 Controller 和 Repository 按 JWT tenantId 完成。

## 厂商服务账号

每个厂商租户需要一个 ThingsBoard 租户管理员服务账号，平台用该账号写入本租户的 Device Profile 与 Asset。

新建租户后 ui-ngx 会自动调用自动初始化接口：

```bash
curl -X POST "http://localhost:8090/api/admin/tenants/<tenantId>/provision-auto?force=false" \
  -H "X-Authorization: Bearer <SYS_ADMIN_JWT>"
```

自动初始化会创建专用 `TENANT_ADMIN`、激活并设置随机密码，然后写入 `plat_vendor_account`。服务账号邮箱格式：

```text
thing-model-svc-<tenantId>@<THINGMODEL_SERVICE_ACCOUNT_EMAIL_DOMAIN>
```

也可以使用已有租户管理员手动注册：

```bash
curl -X POST "http://localhost:8090/api/admin/tenants/<tenantId>/provision" \
  -H "X-Authorization: Bearer <SYS_ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"username":"vendor-admin@example.com","password":"vendor-password","force":false}'
```

密码使用 `THINGMODEL_SECRET_KEY` 做 AES-GCM 加密后存入 `plat_vendor_account`，接口不返回密码。

## API

所有 `/api/**` 接口使用 ThingsBoard JWT 或 API Key：

```http
X-Authorization: Bearer <TB_JWT>
X-Authorization: ApiKey <TB_API_KEY>
```

API Key 对应用户必须具备所需权限，例如产品接口需要 `TENANT_ADMIN`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/auth/me` | 当前用户与租户 |
| GET | `/api/products?keyword=` | 产品列表 |
| GET | `/api/products/{productId}` | 产品详情、版本、物模型目录 |
| POST | `/api/products` | 创建/更新产品并同步 ThingsBoard |
| PUT | `/api/products/{productId}/thing-model` | 提交新 TSL 版本 |
| POST | `/api/products/{productId}/thing-model/validate` | 只校验 TSL |
| GET | `/api/products/{productId}/catalog` | 属性/事件/行为目录 |
| POST | `/api/products/{productId}/sync` | 重新同步模板、资产与属性 |
| DELETE | `/api/products/{productId}` | 删除产品、物模型和关联 ThingsBoard 资源 |
| POST | `/api/admin/tenants/{tenantId}/provision-auto` | 自动创建并激活专用 TENANT_ADMIN，注册厂商服务账号 |
| POST | `/api/admin/tenants/{tenantId}/provision` | 使用已有 TENANT_ADMIN 注册厂商服务账号 |
| POST | `/api/admin/tenants/{tenantId}/account` | 注册厂商 ThingsBoard 服务账号 |

创建产品示例：

```bash
curl -X POST "http://localhost:8090/api/products" \
  -H "X-Authorization: Bearer $TB_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "productId": "9HYN9PJNOY",
    "name": "WiFi诊断终端",
    "model": "9HYN9PJNOY",
    "categoryId": "1",
    "tslVersion": "1.0",
    "tsl": { ... TSL JSON ... },
    "strictUnknown": false
  }'
```

响应：

```json
{
  "productId": "9HYN9PJNOY",
  "tslVersion": "1.0",
  "tbProfileId": "...",
  "tbAssetId": "...",
  "propertyCount": 7,
  "eventCount": 0,
  "actionCount": 0,
  "schemaBytes": 700,
  "status": "PUBLISHED",
  "warnings": []
}
```

## 发布流程

1. 校验 `X-Authorization`，解析租户与权限。
2. TSL JSON Schema 结构校验 + 业务校验。
3. 写入 `plat_product` 与 `plat_product_tsl`（DRAFT）。
4. 生成/更新规则链，并把压缩 TSL schema 内嵌到校验脚本。
5. 按产品名幂等创建/更新 ThingsBoard Device Profile，并绑定默认规则链。
6. 创建/更新产品 Asset，并写入 `tsl_json`、`tsl_schema` 等 SERVER_SCOPE 属性。
7. 写入 `plat_profile_binding`，TSL 置为 PUBLISHED。

同步失败时 DRAFT 保留，接口返回 `502`，可调用 `POST /api/products/{productId}/sync` 重试。

## 错误响应

```json
{
  "message": "物模型校验失败",
  "code": "TSL_INVALID",
  "issues": [
    {"code": "ID_DUP", "path": "/properties/2/id", "message": "属性标识重复: speed"}
  ]
}
```

常见状态码：

- `400`：TSL 校验失败、参数缺失
- `401`：JWT 无效
- `403`：跨租户或非 SYS_ADMIN 操作
- `404`：产品/物模型不存在
- `409`：ProductId 冲突、同版本 TSL 内容冲突
- `502`：ThingsBoard 调用失败

## 当前范围

已实现：

- TSL 解析、JSON Schema + 业务校验、压缩 schema
- 腾讯原始 TSL 自动规范化，支持 `stringenum`、`dataType`、数组形式 `specs`
- 产品与 TSL 版本持久化，ProductId 全系统唯一
- Device Profile、产品 Asset、SERVER_SCOPE 属性同步
- 按产品生成规则链 `<ProductId>` 并绑定 `defaultRuleChainId`
- 规则链内嵌产品 TSL schema，按属性 + 事件校验类型、范围、必填、未知字段、枚举、int32、报文大小与时间戳单位
- 非法数据不写时序库，只投递 `iot.invalid`；合法遥测/事件继续落库并投 Kafka
- 规则链 Kafka 出口：`iot.telemetry.normalized`、`iot.event.normalized`、`iot.invalid`
- 厂商服务账号 AES-GCM 加密，新建租户后自动创建并注册专用 `TENANT_ADMIN`
- ThingsBoard JWT 校验与租户隔离
- Controller `BaseController` + `@RequireAuthority`
- 产品列表、详情、TSL 编辑/校验/删除页面，保存物模型后自动同步，租户服务账号初始化弹窗
- 产品删除前检查设备，删除时清理独占的 Device Profile、Asset 和 Rule Chain
- OpenAPI / Swagger UI
- 独立 database 部署与 `DatabaseGuard` 防误连（可选同库 schema 模式）
- 数据访问使用 jOOQ `DSLContext`，支持 JSONB、`ON CONFLICT`、`FOR UPDATE` 与批量写入，不再使用 `JdbcTemplate`
- 单元/集成测试（校验器、压缩 schema、模板生成、规则链、同步、产品服务、Controller、权限、数据库校验、jOOQ 仓储）
- 连接现有 ThingsBoard 的集成测试：新建产品后通过 ThingsBoard REST API 校验规则链名称、节点、连接、内嵌 schema 和 Device Profile 绑定

未实现（后续阶段）：

- 后端设备批量创建与 Access Token 下发 API
- 事件中心
- 组织树、工点绑定、开放 API
- OTA、远程配置、影子、设备 SDK
- TDengine 入湖由外部 `thingsboard-ingest` 负责，不在本工程

## 说明

- ThingsBoard 公共仓库中 `thingsboard-pe-client` 没有 `4.3.1.7`，本工程使用 `4.4.0`。
- PE client 的 `DeviceProfileData` 模型不包含 `alarms` 字段；服务端允许其为空，平台也不使用 Alarm。
- 测试样例 `valid-tsl.json` 根据文档字段重建，包含 7 个属性，不是原始 33 属性文件。
