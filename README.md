![banner](https://github.com/user-attachments/assets/3584b592-33dd-4fb4-91d4-47b62b34806c)

# 中国中铁物联网平台

中国中铁物联网平台是在社区版基础上二次开发的企业物联网平台，目标是在保留多租户、设备管理、规则引擎和可视化能力的基础上，增加产品与物模型能力、TSL 校验、按产品规则链、遥测入湖和定制前端页面。

- 底座版本：社区版 `4.4.0`
- 产品与物模型模块：JDK 25 / Spring Boot 3.5.15
- 数据入湖服务：消费 Kafka 并写入 TDengine/事件库
- 设计文档：[docs/](docs/)
- 本仓库许可证：[Apache 2.0](LICENSE)

## 1. 项目定位

中国中铁体系内存在大量异构终端，设备协议、报文和物模型定义不统一。平台以社区版为底座，统一承载“产品—设备—物模型—数据”主链路，并补齐规范特有语义。

核心原则：

- 设备直连平台内置 MQTT 传输，不部署外部消息代理
- TSL 是物模型的唯一事实来源
- 一个厂商一个租户，平台侧维护统一的组织与台账
- 扩展优先放在产品与物模型模块和定制前端，避免修改平台核心表结构与内核逻辑
- 属性与事件统一走遥测，按设计文档不使用平台告警实体

## 2. 当前能力

已实现或已具备：

- 产品与 TSL 版本管理
- TSL JSON Schema 与业务校验
- 压缩 TSL schema 生成
- 产品配置、产品资产生成与更新
- 按产品生成规则链并绑定 `defaultRuleChainId`
- 规则链内嵌 TSL schema，校验类型、范围、枚举、未知字段、事件参数等
- Kafka 三个主题外发：
  - `iot.telemetry.normalized`
  - `iot.event.normalized`
  - `iot.invalid`
- 产品与物模型前端页面，支持删除产品并清理关联资源
- 新建租户后自动初始化平台服务账号
- 设备注册与遥测模拟脚本
- TDengine 数据入湖服务
- 视频网关：摄像头管理、推流配置、HLS / WebRTC 预览
- Kubernetes 增量部署说明

当前实现以 [docs/](docs/) 为准。未实现能力集中记录在 [09-测试与路线图](docs/09-测试与路线图.md)，不再混入当前能力说明。

## 3. 仓库结构

| 目录 | 说明 |
| --- | --- |
| `application/` | 中国中铁物联网平台应用模块 |
| `ui-ngx/` | Angular 前端，包含产品/物模型定制页面 |
| `thing-model/` | 产品与物模型模块 |
| `media/` | 视频网关（摄像头管理、推流配置、HLS / WebRTC 预览） |
| `docs/` | 架构、物模型、产品发布、设备接入、前端、API、部署与测试文档 |
| `dao/`、`common/`、`rule-engine/`、`transport/` | 中国中铁物联网平台基础模块 |
| `packaging/`、`msa/`、`monitoring/` | 打包、微服务与监控配置 |
| `thing-model/deploy/` | 产品与物模型数据库初始化脚本 |
| `TEST_FAST.md` | 上游社区版测试加速说明 |

产品与物模型模块不修改平台核心源码，只在平台内管理产品配置、资产和规则链。

## 4. 文档总目录

| 文档 | 内容 |
| --- | --- |
| [01-平台概览](docs/01-平台概览.md) | 项目定位、当前范围、核心对象和文档导航 |
| [02-架构与数据模型](docs/02-架构与数据模型.md) | 组件关系、请求链路、数据库表、实体映射 |
| [03-物模型与校验](docs/03-物模型与校验.md) | TSL 结构、校验规则、压缩 schema、版本状态 |
| [04-产品与规则链](docs/04-产品与规则链.md) | 产品发布、平台处理、规则链和 Kafka 消息 |
| [05-设备接入](docs/05-设备接入.md) | MQTT 凭证、主题、遥测、事件、RPC、网关和脚本 |
| [06-前端与权限](docs/06-前端与权限.md) | 产品页面、租户弹窗、菜单、JWT 和代理 |
| [07-API参考](docs/07-API参考.md) | 接口、参数、返回、错误码和示例 |
| [08-部署与运维](docs/08-部署与运维.md) | 配置、数据库、Kubernetes、升级和排障 |
| [09-测试与路线图](docs/09-测试与路线图.md) | 物模型兼容、脚本、测试和未实现项 |
| [10-租户与产品快速使用手册](docs/10-租户与产品快速使用手册.md) | 从新建租户到使用示例 TSL 创建产品 |
| [11-AI-Agent对话助手方案](docs/11-AI-Agent对话助手方案.md) | 前端对话助手、后端 Agent API、工具权限与确认流程 |
| [12-AI-Agent操作演示](docs/12-AI-Agent操作演示.md) | AI 助手查询、创建租户/产品/设备/用户及异常演示 |
| [13-AI-Agent-DSH全接口接入方案](docs/13-AI-Agent-DSH全接口接入方案.md) | DSH 编排层、统一 API 目录与全接口接入 |
| [14-视频网关](docs/14-视频网关.md) | 摄像头管理、推流配置、HLS / WebRTC 预览与部署 |
| [用户手册](docs/manuals/README.md) | 面向第三方接入方的网关等功能操作手册 |

## 5. 环境要求

| 组件 | 版本/说明 |
| --- | --- |
| JDK | 25 |
| Maven | 3.9+ |
| Node.js | 22.22.2 |
| Yarn | 1.22.22 |
| PostgreSQL | 14+ |
| 中国中铁物联网平台 | 4.4.x |
| Kafka | 规则链外发与入湖消费 |
| Python | 3.12（视频网关） |
| uv | 视频网关依赖管理 |
| MediaMTX | 视频网关推流与 HLS / WebRTC 分发 |
| TDengine | 3.x，仅入湖服务需要 |

## 6. 快速开始

### 6.1 启动产品与物模型模块

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

数据库、平台地址、Kafka、AES 密钥等配置见 [thing-model/README.md](thing-model/README.md)。

### 6.2 构建产品与物模型模块

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

前端通过 `/api/thing-model` 访问产品与物模型模块，通过 `/api` 访问平台核心服务。具体代理规则见 [08-部署与运维](docs/08-部署与运维.md)。

### 6.4 设备模拟

```bash
python -m pip install -r tools/src/main/python/simulators/requirements.txt
python tools/src/main/python/simulators/simulate_telemetry.py --mode mixed --count 10
```

详细参数见 [tools/src/main/python/simulators/README.md](tools/src/main/python/simulators/README.md)。

## 7. 测试

产品与物模型模块单元测试：

```bash
mvn -f thing-model/pom.xml test
```

排除平台集成 / Testcontainers 测试：

```bash
mvn -f thing-model/pom.xml test -Dtest='!*IntegrationTest'
```

上游社区版测试加速方式见 [TEST_FAST.md](TEST_FAST.md)。

## 8. 部署

推荐使用 Kubernetes 或 Docker Compose 部署。最小生产形态包括：

- 平台 Web/Core
- MQTT 传输
- PostgreSQL
- Kafka
- TDengine
- 产品与物模型模块
- 定制前端 Nginx

增量部署产品与物模型模块与前端见 [08-部署与运维](docs/08-部署与运维.md)。

## 9. 上游社区版

本项目基于 [上游社区版](https://github.com/thingsboard/thingsboard)，保留其设备管理、资产、遥测、规则引擎、仪表板和 REST API 能力。

上游资源：

- [上游官网](https://thingsboard.io/)
- [上游文档](https://thingsboard.io/docs/)
- [Getting Started](https://thingsboard.io/docs/getting-started-guides/helloworld/)
- [规则引擎](https://thingsboard.io/docs/user-guide/rule-engine-2-0/re-getting-started/)

## 10. 许可证

本项目沿用上游社区版的 [Apache License 2.0](LICENSE)。

安全相关问题请参考 [security.md](security.md)。
