![banner](https://github.com/user-attachments/assets/3584b592-33dd-4fb4-91d4-47b62b34806c)

# 中铁信科物联网平台

基于 ThingsBoard 社区版二次开发的企业物联网平台，目标是在保留 ThingsBoard 多租户、设备管理、规则引擎和可视化能力的基础上，增加产品与物模型服务、TSL 校验、按产品规则链、遥测入湖和定制前端页面。

- 底座版本：ThingsBoard `4.4.0`
- 定制服务：`thing-model`，JDK 25 / Spring Boot 3.5.15
- 配套入湖服务：独立工程 `thingsboard-ingest`，不在本仓库 Maven reactor 中
- 设计文档：[docs/](docs/)
- 本仓库许可证：[Apache 2.0](LICENSE)

## 1. 项目定位

中国中铁体系内存在大量异构终端，设备协议、报文和物模型定义不统一。平台以 ThingsBoard 为底座，统一承载“产品—设备—物模型—数据”主链路，并通过独立服务补齐规范特有语义。

核心原则：

- 设备直连 ThingsBoard 内置 MQTT Transport，不部署外部 Broker
- TSL 是物模型的唯一事实来源
- 一个厂商一个租户，平台侧维护统一的组织与台账
- 扩展优先放在独立服务和定制前端，避免修改 ThingsBoard 核心表结构与内核逻辑
- 属性与事件统一走 Telemetry，按设计文档不使用 ThingsBoard Alarm 实体

## 2. 当前能力

已实现或已具备：

- 产品与 TSL 版本管理
- TSL JSON Schema 与业务校验
- 压缩 TSL schema 生成
- ThingsBoard Device Profile、产品 Asset 同步
- 按产品生成规则链并绑定 `defaultRuleChainId`
- 规则链内嵌 TSL schema，校验类型、范围、枚举、未知字段、事件参数等
- Kafka 三 topic 外发：
  - `iot.telemetry.normalized`
  - `iot.event.normalized`
  - `iot.invalid`
- 产品与物模型前端页面，支持删除产品并清理关联 ThingsBoard 资源
- 新建租户后自动初始化厂商服务账号
- 设备注册与遥测模拟脚本
- TDengine 入湖服务（配套独立工程 `thingsboard-ingest`，不在本仓库）
- Kubernetes 增量部署说明

当前实现以 [docs/](docs/) 和 [thing-model/README.md](thing-model/README.md) 为准。未实现能力集中记录在 [09-迁移测试与路线图](docs/09-迁移测试与路线图.md)，不再混入当前能力说明。

## 3. 仓库结构

| 目录 | 说明 |
| --- | --- |
| `application/` | ThingsBoard 应用模块 |
| `ui-ngx/` | Angular 前端，包含产品/物模型定制页面 |
| `thing-model/` | 产品与物模型服务，独立 Spring Boot 工程 |
| `docs/` | 架构、物模型、产品同步、设备接入、前端、API、部署与迁移文档 |
| `dao/`、`common/`、`rule-engine/`、`transport/` | ThingsBoard 基础模块 |
| `packaging/`、`msa/`、`monitoring/` | 打包、微服务与监控配置 |
| `thing-model/deploy/` | thing-model 数据库初始化脚本 |
| `TEST_FAST.md` | 上游 ThingsBoard 测试加速说明 |

`thing-model` 不修改 ThingsBoard 源码，只通过 REST API 管理 Device Profile、Asset 和 Rule Chain。

## 4. 文档总目录

| 文档 | 内容 |
| --- | --- |
| [01-平台概览](docs/01-平台概览.md) | 项目定位、当前范围、核心对象和文档导航 |
| [02-架构与数据模型](docs/02-架构与数据模型.md) | 组件关系、请求链路、数据库表、实体映射 |
| [03-物模型与校验](docs/03-物模型与校验.md) | TSL 结构、校验规则、压缩 schema、版本状态 |
| [04-产品同步与规则链](docs/04-产品同步与规则链.md) | 产品发布、ThingsBoard 同步、规则链和 Kafka 消息 |
| [05-设备接入](docs/05-设备接入.md) | MQTT 凭证、主题、遥测、事件、RPC、网关和脚本 |
| [06-前端与权限](docs/06-前端与权限.md) | 产品页面、租户弹窗、菜单、JWT 和代理 |
| [07-API参考](docs/07-API参考.md) | 接口、参数、返回、错误码和示例 |
| [08-部署与运维](docs/08-部署与运维.md) | 配置、数据库、Kubernetes、升级和排障 |
| [09-迁移测试与路线图](docs/09-迁移测试与路线图.md) | 腾讯数据迁移、脚本、测试和未实现项 |

## 5. 环境要求

| 组件 | 版本/说明 |
| --- | --- |
| JDK | 25 |
| Maven | 3.9+ |
| Node.js | 22.22.2 |
| Yarn | 1.22.22 |
| PostgreSQL | 14+ |
| ThingsBoard | 4.4.x |
| Kafka | 规则链外发与入湖消费 |
| TDengine | 3.x，仅入湖服务需要 |

## 6. 快速开始

### 6.1 启动 thing-model

```bash
mvn -f thing-model/pom.xml spring-boot:run
```

默认端口 `8090`：

```bash
curl http://localhost:8090/actuator/health
```

Swagger UI：

```text
http://localhost:8090/swagger-ui.html
```

数据库、ThingsBoard 地址、Kafka、AES key 等配置见 [thing-model/README.md](thing-model/README.md)。

### 6.2 构建 thing-model

```bash
mvn -f thing-model/pom.xml clean package -DskipTests
```

产物：

```text
thing-model/target/thing-model-0.1.0-SNAPSHOT.jar
```

### 6.3 前端

```bash
cd ui-ngx
yarn install --frozen-lockfile
yarn start
```

生产构建：

```bash
yarn build:prod
```

前端通过 `/api/thing-model` 访问 thing-model，通过 `/api` 访问 ThingsBoard。具体代理规则见 [thing-model/README.md](thing-model/README.md) 和 [08-部署与运维](docs/08-部署与运维.md)。

### 6.4 设备模拟

```bash
python -m pip install -r thing-model/scripts/requirements.txt
python thing-model/scripts/simulate_telemetry.py --mode mixed --count 10
```

详细参数见 [thing-model/scripts/README.md](thing-model/scripts/README.md)。

## 7. 测试

thing-model 单元测试：

```bash
mvn -f thing-model/pom.xml test
```

排除外部 ThingsBoard / Testcontainers 集成测试：

```bash
mvn -f thing-model/pom.xml test -Dtest='!*IntegrationTest'
```

ThingsBoard 上游测试加速方式见 [TEST_FAST.md](TEST_FAST.md)。

## 8. 部署

推荐使用 Kubernetes 或 Docker Compose 部署。最小生产形态包括：

- ThingsBoard Web/Core
- MQTT Transport
- PostgreSQL
- Kafka
- TDengine
- thing-model
- 定制前端 Nginx

增量部署 thing-model 与前端见 [08-部署与运维](docs/08-部署与运维.md)。

## 9. 上游 ThingsBoard

本项目基于 [ThingsBoard](https://github.com/thingsboard/thingsboard) 社区版，保留其设备管理、资产、遥测、规则引擎、仪表板和 REST API 能力。

上游资源：

- [ThingsBoard 官网](https://thingsboard.io/)
- [ThingsBoard 文档](https://thingsboard.io/docs/)
- [Getting Started](https://thingsboard.io/docs/getting-started-guides/helloworld/)
- [Rule Engine](https://thingsboard.io/docs/user-guide/rule-engine-2-0/re-getting-started/)

## 10. 许可证

本项目沿用 ThingsBoard 的 [Apache License 2.0](LICENSE)。

安全相关问题请参考 [security.md](security.md)。
