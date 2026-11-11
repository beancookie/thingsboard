# thing-model AI Agent

独立 Python Agent 服务，为前端 AI 助手提供对话和 ThingsBoard 管理操作。

开发约定、目录结构和测试说明见 [AGENT.md](AGENT.md)。

## 技术栈

- Python 3.12
- uv
- FastAPI
- Pydantic
- AsyncOpenAI（OpenAI 兼容接口）
- DeepSeek Harness Python SDK（可选编排引擎）
- httpx
- PyYAML
- pytest

## 环境要求

- Python 3.12
- uv

## 启动

```bash
cd ai-agent
uv sync
cp .env.example .env
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Windows PowerShell 使用：

```powershell
Copy-Item .env.example .env
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

接口文档：

```text
http://localhost:8000/swagger-ui.html
```

依赖管理：

```bash
uv add <package>
uv add --dev <package>
uv lock
uv sync
```

## 配置

```text
AI_AGENT_ENABLED=true
AI_AGENT_ENGINE=openai
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
AI_AGENT_THING_MODEL_URL=http://localhost:8090
AI_AGENT_THINGSBOARD_URL=http://localhost:18080
AI_AGENT_API_CATALOG_DIR=config/api
AI_AGENT_INTERNAL_TOOL_TOKEN=<secret>
AI_AGENT_FILE_TTL_SECONDS=600
AI_AGENT_FILE_MAX_BYTES=2000000
AI_AGENT_FILE_TEXT_MAX_BYTES=65536
AI_AGENT_MAX_TOOL_ROUNDS=8
```

完整配置见 `.env.example`。

`AI_AGENT_ENGINE` 默认 `openai`，保留原 OpenAI 兼容编排路径，同时提供 `search_api_operations` / `call_api_operation` 两个目录工具。设置为 `dsh` 后，`ai-agent` 通过 `deepseek-harness-sdk` 启动 DSH runtime，并使用 `dsh/thingsboard.patch.yml` 加载同样的目录工具。

## 命令行聊天工具

用于快速测试运行中的 `ai-agent`：

```bash
# 单次消息
uv run python -m app.cli chat "查询租户" --token "$TB_TOKEN"

# 交互模式
AI_AGENT_CLI_TOKEN="$TB_TOKEN" uv run python -m app.cli
# 等价写法
AI_AGENT_CLI_TOKEN="$TB_TOKEN" uv run python -m app.cli chat

# 指定地址
uv run python -m app.cli chat "查询租户" \
  --token "$TB_TOKEN" \
  --url http://localhost:8000
```

交互模式支持：

```text
/clear        清空当前对话
/tsl <file>   加载 TSL 文件
/help         查看帮助
/exit         退出
```

检测到待确认动作时，CLI 会询问是否执行；使用 `--yes` 可自动确认。  
`--token` 也可以省略，改用 `AI_AGENT_CLI_TOKEN` 或 `TB_TOKEN`。

目录和 OpenAPI 相关命令：

```bash
uv run python -m app.cli catalog validate
uv run python -m app.cli catalog search 租户
uv run python -m app.cli dsh smoke
```

## API 目录

`config/api/` 保存 ThingsBoard 和 thing-model 的接口白名单。新增接口时从使用手册或 OpenAPI 生成并人工审核：

```bash
# 从 docs/manuals 生成
uv run python scripts/import_manual_apis.py
uv run python scripts/import_manual_apis.py --check

# 从 OpenAPI 生成
uv run python scripts/import_openapi.py \
  --service thingsboard \
  --spec application/target/openapi.json \
  --out config/api/thingsboard.yaml \
  --overrides config/api/overrides.yaml

uv run python scripts/import_openapi.py \
  --service thing_model \
  --spec http://localhost:8090/v3/api-docs \
  --out config/api/thing_model.yaml \
  --overrides config/api/overrides.yaml
```

`overrides.yaml` 用于覆盖中文摘要、别名、权限、风险和 `code_access`。

## Kubernetes

参考配置见 `deploy/k8s/ai-agent.yaml`，包含 Secret、ConfigMap、Deployment 和 Service。

```bash
kubectl -n <namespace> apply -f ai-agent/deploy/k8s/ai-agent.yaml
kubectl -n <namespace> rollout status deployment/ai-agent
```

部署前替换 `<namespace>`、`<registry>`、`<tag>`、`<openai-api-key>`，并按集群实际服务名调整 `AI_AGENT_THING_MODEL_URL` 和 `AI_AGENT_THINGSBOARD_URL`。

AI Agent 监听 `8000`，健康检查为 `/health` 和 `/ready`。前端网关需要把 `/api/ai-agent/` 转发到 `http://ai-agent:8000/`。

## 上下文队列

服务按队列保留最近内容，不会因为超出上限返回错误：

- `AI_AGENT_MAX_MESSAGES`：默认 20，只把最近 20 条对话消息送入模型。
- `AI_AGENT_MAX_ACTIONS`：默认 10，只保留最近 10 个待确认或执行动作。
- `AI_AGENT_MAX_TOOL_ROUNDS`：默认 8，允许模型进行多轮工具调用。
- 超出上限时静默丢弃最早的消息和动作，系统提示词始终保留。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 存活检查 |
| GET | `/ready` | 就绪检查 |
| POST | `/chat` | AI 对话、动作生成和确认执行 |
| POST | `/files` | 上传附件，仅用于模型上下文，不提供下载 |

上传后的文件只用于模型理解，不会返回文件，也不提供下载入口。所有操作结果只显示在对话框文本中。

所有接口使用 ThingsBoard JWT：

```http
X-Authorization: Bearer <TB_JWT>
```

## 对话请求

```json
{
  "mode": "chat",
  "messages": [
    {
      "role": "user",
      "content": "创建一个租户，名称是测试厂商"
    }
  ]
}
```

带附件时：

```json
{
  "mode": "chat",
  "messages": [
    {
      "role": "user",
      "content": "分析这个文件",
      "files": [
        {"id": "file_xxx", "name": "data.csv", "mime_type": "text/csv", "size": 123}
      ]
    }
  ],
  "files": [
    {"id": "file_xxx", "name": "data.csv", "mime_type": "text/csv", "size": 123}
  ]
}
```

返回待确认动作：

```json
{
  "reply": "已生成待确认操作，请确认后执行。",
  "actions": [
    {
      "id": "call_xxx",
      "type": "create_tenant",
      "summary": "创建租户",
      "params": {
        "title": "测试厂商"
      },
      "status": "PROPOSED"
    }
  ],
  "executed": []
}
```

确认执行：

```json
{
  "mode": "execute",
  "messages": [],
  "actions": [
    {
      "id": "call_xxx",
      "type": "create_tenant",
      "summary": "创建租户",
      "params": {
        "title": "测试厂商"
      },
      "status": "PROPOSED"
    }
  ]
}
```

## 工具

只读：

- `list_tenants`
- `list_products`
- `list_devices`

写操作：

- `create_tenant`
- `create_tenant_admin`
- `create_product`
- `create_device`
- `create_user`

写操作只生成待确认动作，用户确认后才执行。

`create_product` 支持三种 TSL 来源：

1. AI 在动作 `params.tsl` 中生成的 TSL
2. 本次请求附带的 `tsl`
3. 两者都没有时，自动生成 `properties: []` 的最小合法 TSL

## 测试

单元测试和接口测试：

```bash
cd ai-agent
uv run pytest -m "not integration"
```

真实 ThingsBoard / thing-model 集成测试：

```bash
export AI_AGENT_THINGSBOARD_URL=http://localhost:18080
export AI_AGENT_THING_MODEL_URL=http://localhost:8090
export TB_SYSADMIN_USERNAME=sysadmin@thingsboard.org
export TB_SYSADMIN_PASSWORD=sysadmin
export TB_TENANT_ADMIN_USERNAME=tenant@thingsboard.org
export TB_TENANT_ADMIN_PASSWORD=tenant

uv run pytest -m integration
```

创建用户并验证激活邮件的测试默认跳过：

```bash
export TB_TEST_SMTP_ENABLED=true
uv run pytest -m integration
```

集成测试会使用唯一名称创建并清理租户、产品、设备和用户。

## 边界

- Agent 不直接访问数据库。
- Agent 不保存用户 JWT。
- Agent 不读取 `THINGMODEL_SECRET_KEY`。
- 设备 MQTT SDK（`tb-mqtt-client` / `tb-gateway-mqtt`）不属于本服务。
