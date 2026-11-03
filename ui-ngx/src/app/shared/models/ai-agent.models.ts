// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
export type AgentMode = 'chat' | 'execute';

export type AgentActionStatus = 'PROPOSED' | 'EXECUTED' | 'FAILED';

export interface AgentMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AgentAction {
  id: string;
  type: string;
  summary: string;
  params: Record<string, unknown>;
  status: AgentActionStatus;
}

export interface AgentContext {
  route?: string;
  product_id?: string;
  tenant_id?: string;
}

export interface AgentChatRequest {
  mode: AgentMode;
  messages: AgentMessage[];
  tsl?: unknown;
  actions?: AgentAction[];
  context?: AgentContext;
}

export interface AgentActionResult {
  action_id: string;
  type: string;
  success: boolean;
  message: string;
  data?: Record<string, unknown>;
}

export interface AgentChatResponse {
  reply: string;
  actions: AgentAction[];
  executed: AgentActionResult[];
}

export interface AiAgentStoredSession {
  version: number;
  messages: AgentMessage[];
  pendingActions: AgentAction[];
  tsl: unknown | null;
  tslFileName: string | null;
  savedAt: string;
}
