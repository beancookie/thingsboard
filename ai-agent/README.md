# thing-model AI Agent

独立 Python Agent 服务，为前端 AI 助手提供对话和 ThingsBoard 管理操作。

开发约定、目录结构和测试说明见 [AGENT.md](AGENT.md)。

## 技术栈

- Python 3.12
- uv
- FastAPI
- Pydantic
- AsyncOpenAI（OpenAI 兼容接口）
- httpx
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
AI_AGENT_OPENAI_BASE_URL=https://api.deepseek.com/v1
AI_AGENT_OPENAI_API_KEY=<secret>
AI_AGENT_OPENAI_MODEL=deepseek-chat
AI_AGENT_THING_MODEL_URL=http://localhost:8090
AI_AGENT_THINGSBOARD_URL=http://localhost:18080
```

完整配置见 `.env.example`。

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
- 超出上限时静默丢弃最早的消息和动作，系统提示词始终保留。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 存活检查 |
| GET | `/ready` | 就绪检查 |
| POST | `/chat` | AI 对话、动作生成和确认执行 |

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
