export const name = 'thingsboard-api'
export const inject = ['tools']

const AGENT_URL = process.env.THINGSBOARD_AGENT_URL || 'http://127.0.0.1:8000'
const AGENT_TOKEN = process.env.THINGSBOARD_AGENT_TOKEN || ''

function render(value) {
  const text = typeof value === 'string' ? value : JSON.stringify(value)
  return [{ type: 'text', text }]
}

async function post(path, payload, signal) {
  const response = await fetch(`${AGENT_URL}${path}`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'X-Internal-Token': AGENT_TOKEN,
    },
    body: JSON.stringify(payload),
    signal,
  })

  let data
  try {
    data = await response.json()
  } catch {
    data = {}
  }

  if (!response.ok) {
    return {
      status: 'ERROR',
      code: data.code || `HTTP_${response.status}`,
      message: data.message || 'ai-agent 内部接口调用失败',
    }
  }
  return data
}

export function apply(ctx) {
  ctx.tools.register({
    name: 'search_api_operations',
    description:
      '搜索 ThingsBoard 和 thing-model 的可用 API。任何平台操作前必须先调用本工具，拿到 operation_id 后再调用 call_api_operation。',
    parameters: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: '接口名称、业务动作或关键词，例如“查询租户”“创建设备”',
        },
        service: {
          type: 'string',
          enum: ['thingsboard', 'thing_model'],
          description: '可选，限定服务',
        },
        limit: {
          type: 'integer',
          description: '返回条数，默认 5，最多 10',
        },
      },
      required: ['query'],
      additionalProperties: false,
    },
    output: {
      schema: {},
      render: (_args, value) => render(value),
    },
    async execute(args, exec) {
      return post(
        '/internal/dsh/api/search',
        {
          query: args?.query,
          service: args?.service,
          limit: args?.limit,
        },
        exec.signal,
      )
    },
  })

  ctx.tools.register({
    name: 'call_api_operation',
    description:
      '调用 search_api_operations 返回的 operation_id。读接口立即执行；写接口返回 PROPOSED 待确认动作，不会直接执行。',
    parameters: {
      type: 'object',
      properties: {
        operation_id: {
          type: 'string',
          description: 'search_api_operations 返回的 operation id',
        },
        params: {
          type: 'object',
          description: '接口参数，字段和类型以 search_api_operations 返回的 params 为准',
          additionalProperties: true,
        },
      },
      required: ['operation_id'],
      additionalProperties: false,
    },
    output: {
      schema: {},
      render: (_args, value) => render(value),
    },
    async execute(args, exec) {
      const sessionId = exec.agent ? String(exec.agent.id) : ''
      if (!sessionId) {
        return {
          status: 'ERROR',
          code: 'SESSION_NOT_FOUND',
          message: '当前会话不可用',
        }
      }
      return post(
        '/internal/dsh/api/call',
        {
          session_id: sessionId,
          operation_id: args?.operation_id,
          params: args?.params || {},
        },
        exec.signal,
      )
    },
  })

  try {
    ctx.tools.restrict({
      allow: ['search_api_operations', 'call_api_operation'],
    })
  } catch {
    // 专用 profile 同时会禁用内置 shell 和文件工具。
  }
}
