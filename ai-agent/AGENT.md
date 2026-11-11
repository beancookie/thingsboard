# ai-agent AGENT 指南

## 1. 项目定位

`ai-agent` 是中国中铁物联网平台的独立 Python AI Agent 服务。

职责：

- 为前端 AI 对话助手提供 `POST /chat` 接口。
- 调用 OpenAI 兼容模型进行工具规划。
- 生成待确认动作，用户确认后执行。
- 通过 REST 调用 ThingsBoard 和 `thing-model`。
- 支持创建租户、租户管理员、产品、设备、用户。

不负责：

- 不修改 ThingsBoard 后端。
- 不直接访问 `thingmodel` 数据库。
- 不读取 `THINGMODEL_SECRET_KEY`。
- 不管理设备 MQTT 遥测；`tb-mqtt-client` 和 `tb-gateway-mqtt` 属于设备侧。

## 2. 技术栈

- Python 3.12
- uv
- FastAPI
- Pydantic
- AsyncOpenAI（OpenAI 兼容接口）
- DeepSeek Harness Python SDK（`AI_AGENT_ENGINE=dsh`）
- httpx
- PyYAML
- pytest / pytest-asyncio / respx
- uvicorn

依赖统一在 `pyproject.toml`，锁文件为 `uv.lock`。不要重新引入 `requirements.txt`。

## 3. 常用命令

```powershell
cd ai-agent

# 安装/同步依赖
uv sync

# 启动服务
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 只跑单元和接口测试
uv run pytest -m "not integration"

# 真实服务集成测试
uv run pytest -m integration

# 全部测试
uv run pytest

# 添加运行依赖
uv add <package>

# 添加测试依赖
uv add --dev <package>

# 刷新锁文件
uv lock

# 命令行聊天
uv run python -m app.cli chat "查询租户" --token <TB_JWT>
AI_AGENT_CLI_TOKEN=<TB_JWT> uv run python -m app.cli chat

# API 目录测试
uv run python -m app.cli catalog validate
uv run python -m app.cli catalog search 租户

# DSH runtime smoke test
uv run python -m app.cli dsh smoke

# 从使用手册生成 API 目录
uv run python scripts/import_manual_apis.py
uv run python scripts/import_manual_apis.py --check

# 从 OpenAPI 生成 API 目录
uv run python scripts/import_openapi.py \
  --service thingsboard \
  --spec application/target/openapi.json \
  --out config/api/thingsboard.yaml \
  --overrides config/api/overrides.yaml

# 检查 API 目录是否最新
uv run python scripts/import_openapi.py \
  --service thingsboard \
  --spec application/target/openapi.json \
  --out config/api/thingsboard.yaml \
  --overrides config/api/overrides.yaml \
  --check
```

本地开发不需要 Docker。Dockerfile 仅用于部署。

## 4. 目录结构

```text
ai-agent/
├── app/
│   ├── main.py                  FastAPI 入口、生命周期、异常处理
│   ├── config.py                AI_AGENT_* 环境变量
│   ├── api/
│   │   ├── agent.py             POST /chat
│   │   ├── files.py             POST /files 上传附件
│   │   ├── internal.py          DSH 内部工具接口
│   │   ├── utils.py             请求 token 提取
│   │   └── health.py            GET /health、/ready
│   ├── auth/
│   │   └── thingsboard.py       ThingsBoard JWT 校验与缓存
│   ├── agent/
│   │   ├── orchestrator.py      对话、工具规划、确认执行
│   │   ├── dsh.py               DeepSeek Harness 运行时封装
│   │   ├── llm.py               AsyncOpenAI 客户端
│   │   ├── tools.py             工具定义、读写工具集合
│   │   ├── executor.py          白名单动作执行与权限校验
│   │   ├── api_catalog.py       API 目录加载、搜索、参数校验
│   │   ├── api_executor.py      API 目录通用执行入口
│   │   ├── files.py             上传附件存储
│   │   ├── sessions.py          DSH 短期会话上下文
│   │   ├── tool_gateway.py      搜索/调用/写提案工具网关
│   │   ├── models.py            请求/响应和动作参数模型
│   │   └── prompts.py           系统提示词
│   ├── clients/
│   │   ├── thingsboard.py       ThingsBoard REST 客户端
│   │   └── thing_model.py       thing-model REST 客户端
│   ├── common/
│   │   └── errors.py            统一业务异常
│   └── cli.py                   命令行聊天与本地测试工具
├── tests/
│   ├── conftest.py
│   ├── test_agent_api.py
│   ├── test_api_catalog.py
│   ├── test_api_executor.py
│   ├── test_auth.py
│   ├── test_clients.py
│   ├── test_cli.py
│   ├── test_dsh.py
│   ├── test_executor.py
│   ├── test_files.py
│   ├── test_files_api.py
│   ├── test_health.py
│   ├── test_import_openapi.py
│   ├── test_internal_api.py
│   ├── test_manual_api_coverage.py
│   ├── test_orchestrator.py
│   ├── test_tool_gateway.py
│   ├── test_tools.py
│   └── integration/
│       ├── conftest.py
│       └── test_thingsboard_integration.py
├── config/
│   └── api/
│       ├── thingsboard.yaml     ThingsBoard 基础 API 目录
│       ├── thing_model.yaml     thing-model API 目录
│       ├── manual_apis.yaml     使用手册生成的 API 目录
│       └── overrides.yaml       人工覆盖项
├── scripts/
│   ├── import_openapi.py        OpenAPI 到 API 目录导入工具
│   └── import_manual_apis.py    使用手册到 API 目录导入工具
├── dsh/
│   └── thingsboard.patch.yml    DSH profile 补丁
├── dsh-plugin-thingsboard/
│   ├── package.json             DSH 插件清单
│   └── index.js                 search/call 工具实现
├── deploy/
│   └── k8s/
│       └── ai-agent.yaml        Secret、ConfigMap、Deployment、Service
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── Dockerfile
└── README.md
```

## 5. 核心流程

```text
前端
  -> POST /api/ai-agent/chat
  -> Nginx / 开发代理
  -> ai-agent POST /chat
  -> 校验 ThingsBoard JWT
  -> 调用 OpenAI 兼容模型
  -> 读工具立即执行，写工具转换为 AgentAction
  -> 前端展示待确认动作
  -> mode=execute 后执行白名单动作
  -> 调用 ThingsBoard / thing-model REST
  -> 返回 AgentActionResult
```

## 6. API 约定

### 请求

```json
{
  "mode": "chat",
  "messages": [
    {"role": "user", "content": "创建一个租户"}
  ],
  "tsl": null,
  "actions": [],
  "context": {
    "route": "/entities/products/4DZDCQUA2D",
    "product_id": "4DZDCQUA2D",
    "tenant_id": "..."
  }
}
```

`mode`：

- `chat`：生成回复或待确认动作，不执行写操作。
- `execute`：执行前端确认后的 `actions`。

### 响应

```json
{
  "reply": "已生成待确认操作，请确认后执行。",
  "actions": [
    {
      "id": "call_xxx",
      "type": "create_tenant",
      "summary": "创建租户",
      "params": {"title": "测试厂商"},
      "status": "PROPOSED"
    }
  ],
  "executed": []
}
```

`AgentActionResult` 字段：

```text
action_id
type
success
message
data
```

后端 JSON 当前使用 snake_case，前端模型需与 wire contract 保持一致。

## 7. 工具与权限

只读工具：

- `list_tenants`：SYS_ADMIN
- `list_products`：TENANT_ADMIN
- `list_devices`：SYS_ADMIN / TENANT_ADMIN

写工具：

- `create_tenant`：SYS_ADMIN
- `create_tenant_admin`：SYS_ADMIN
- `create_product`：TENANT_ADMIN
- `create_device`：TENANT_ADMIN
- `create_user`：SYS_ADMIN / TENANT_ADMIN

规则：

- TENANT_ADMIN 只能操作 JWT 所属租户。
- SYS_ADMIN 代建产品或设备暂不支持。
- 写操作必须二次确认。
- 第一版不提供删除、修改和批量工具。
- 主键、名称、TSL 和权限由服务端重新校验，不能信任模型输出。

## 8. 外部调用

### ThingsBoard

- JWT 校验：`GET /api/auth/user`
- 租户：`/api/tenant`
- 用户：`/api/user?sendActivationMail=true`
- 设备：`/api/device`
- 设备属性：`/api/plugins/telemetry/DEVICE/{id}/attributes/SERVER_SCOPE`

### thing-model

- 产品：`/api/products`
- 服务账号初始化：`/api/admin/tenants/{tenantId}/provision-auto`

Python Agent 不直接访问数据库，只调用 REST。

## 9. 配置

```text
AI_AGENT_ENABLED=true
AI_AGENT_ENGINE=openai|dsh
AI_AGENT_OPENAI_BASE_URL=https://api.deepseek.com/v1
AI_AGENT_OPENAI_API_KEY=<secret>
AI_AGENT_OPENAI_MODEL=deepseek-chat
AI_AGENT_DEEPSEEK_API_KEY=<secret>
AI_AGENT_DEEPSEEK_BASE_URL=
AI_AGENT_DSH_HOME=.dsh-home
AI_AGENT_DSH_WORKSPACE=.dsh-workspace
AI_AGENT_DSH_PROFILE=sdk-minimal
AI_AGENT_DSH_PATCH_TEMPLATE=dsh/thingsboard.patch.yml
AI_AGENT_DSH_PLUGIN_PATH=dsh-plugin-thingsboard/index.js
AI_AGENT_DSH_PROVIDER=deepseek-official
AI_AGENT_DSH_MODEL=deepseek-v4-flash
AI_AGENT_DSH_TIMEOUT_SECONDS=60
AI_AGENT_INTERNAL_AGENT_URL=http://127.0.0.1:8000
AI_AGENT_CLI_URL=http://127.0.0.1:8000
AI_AGENT_CLI_TOKEN=<TB_JWT>
AI_AGENT_TIMEOUT_SECONDS=60
AI_AGENT_MAX_TOKENS=2048
AI_AGENT_THING_MODEL_URL=http://localhost:8090
AI_AGENT_THINGSBOARD_URL=http://localhost:18080
AI_AGENT_AUTH_CACHE_SECONDS=60
AI_AGENT_MAX_MESSAGES=20
AI_AGENT_MAX_TSL_BYTES=2000000
AI_AGENT_MAX_ACTIONS=10
AI_AGENT_MAX_TOOL_ROUNDS=8
AI_AGENT_API_CATALOG_DIR=config/api
AI_AGENT_API_MAX_RESPONSE_BYTES=262144
AI_AGENT_FILE_TTL_SECONDS=600
AI_AGENT_FILE_MAX_BYTES=2000000
AI_AGENT_FILE_TEXT_MAX_BYTES=65536
AI_AGENT_INTERNAL_TOOL_TOKEN=<secret>
```

- `AI_AGENT_OPENAI_API_KEY` 只能保存在后端 Secret 中。
- `AI_AGENT_MAX_MESSAGES`：模型上下文保留最近 N 条对话消息，超出时静默丢弃最早消息。
- `AI_AGENT_MAX_ACTIONS`：待确认和执行动作保留最近 N 个，超出时静默丢弃最早动作。
- 消息和动作超限不返回错误提示；系统提示词始终保留。
- 不记录 JWT、密码、API Key 和完整敏感参数。
- 本地配置从 `.env.example` 复制为 `.env`。

## 10. 测试规范

### 单元与接口测试

```powershell
uv run pytest -m "not integration"
```

覆盖：

- `/health`、`/ready`
- `/chat` 鉴权、参数校验、响应结构
- JWT 缓存与错误映射
- ThingsBoard / thing-model REST 客户端
- 工具定义和动作参数模型
- 动作执行与权限校验
- API 目录加载、搜索、overrides 合并
- OpenAPI 导入与目录生成
- 通用 API 执行器、工具网关、内部接口鉴权
- 对话规划、读工具、写动作确认

### 真实集成测试

```powershell
$env:TB_SYSADMIN_USERNAME='sysadmin@thingsboard.org'
$env:TB_SYSADMIN_PASSWORD='sysadmin'
$env:TB_TENANT_ADMIN_USERNAME='tenant@thingsboard.org'
$env:TB_TENANT_ADMIN_PASSWORD='tenant'
uv run pytest -m integration
```

集成测试要求：

- ThingsBoard 可访问。
- `thing-model` 可访问。
- 测试使用唯一名称并清理测试数据。
- 用户激活邮件测试默认跳过，设置 `TB_TEST_SMTP_ENABLED=true` 后执行。

## 11. 开发约定

- 使用 uv 管理依赖，禁止手写 `requirements.txt`。
- 新增工具时同时更新：
  - `agent/tools.py`
  - `agent/models.py`
  - `agent/executor.py`
  - 对应测试
- 新增普通 REST 接口时优先更新 `config/api/*.yaml`，复杂业务再在 `agent/executor.py` 增加 handler。
- 新增外部 REST 调用时放到 `app/clients/`，不要在业务层直接拼 HTTP。
- API 目录只允许通过现有 `ThingsBoardClient` / `ThingModelClient` 执行，不要新增第二套 HTTP 调用栈。
- 新增错误使用 `AgentError` 子类或标准错误码。
- 写操作必须先返回 `PROPOSED` 动作，不得在 `chat` 模式直接执行。
- 不在日志中输出 JWT、密码、API Key 或完整 TSL 内容。
- 保持 `pyproject.toml`、`uv.lock` 和代码提交一致。
- 修改协议字段时同步前端 `ui-ngx/src/app/shared/models/ai-agent.models.ts`。

## 12. 已知边界

- 第一版无流式输出。
- 第一版无聊天记录持久化。
- 第一版无删除、修改和批量操作。
- SYS_ADMIN 代建产品/设备需要后续内部接口。
- 用户创建依赖 ThingsBoard SMTP 激活邮件。
- 设备 Access Token 不在对话中返回。
