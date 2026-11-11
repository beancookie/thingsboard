// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { Injectable } from '@angular/core';
import {
  AgentAction,
  AgentFile,
  AgentMessage,
  AiAgentStoredSession
} from '@shared/models/ai-agent.models';

const STORAGE_PREFIX = 'AI_AGENT_CHAT_V1';
const POSITION_PREFIX = 'AI_AGENT_FAB_POSITION_V1';
const PANEL_PREFIX = 'AI_AGENT_PANEL_V1';
const SESSION_VERSION = 1;
const MAX_MESSAGES = 100;
const MAX_STORAGE_CHARS = 3_500_000;

export interface AiAgentFabPosition {
  left: number;
  top: number;
}

export interface AiAgentPanelState {
  left: number;
  top: number;
  width: number;
  height: number;
}

@Injectable({
  providedIn: 'root'
})
export class AiAgentHistoryService {

  static buildKey(tenantId: string | null | undefined, userId: string | null | undefined): string | null {
    if (!userId) {
      return null;
    }
    return `${STORAGE_PREFIX}_${tenantId || 'sys'}_${userId}`;
  }

  static buildPositionKey(tenantId: string | null | undefined, userId: string | null | undefined): string | null {
    if (!userId) {
      return null;
    }
    return `${POSITION_PREFIX}_${tenantId || 'sys'}_${userId}`;
  }

  static buildPanelKey(tenantId: string | null | undefined, userId: string | null | undefined): string | null {
    if (!userId) {
      return null;
    }
    return `${PANEL_PREFIX}_${tenantId || 'sys'}_${userId}`;
  }

  load(key: string | null): AiAgentStoredSession | null {
    if (!key || typeof localStorage === 'undefined') {
      return null;
    }
    try {
      const raw = localStorage.getItem(key);
      if (!raw) {
        return null;
      }
      const parsed = JSON.parse(raw);
      if (!parsed || parsed.version !== SESSION_VERSION) {
        return null;
      }
      return {
        version: SESSION_VERSION,
        messages: this.normalizeMessages(parsed.messages),
        pendingActions: this.normalizeActions(parsed.pendingActions),
        tsl: parsed.tsl ?? null,
        savedAt: typeof parsed.savedAt === 'string' ? parsed.savedAt : new Date().toISOString()
      };
    } catch {
      return null;
    }
  }

  save(key: string | null, session: AiAgentStoredSession): void {
    if (!key || typeof localStorage === 'undefined') {
      return;
    }
    try {
      const messages = [...session.messages];
      let state: AiAgentStoredSession = {
        ...session,
        version: SESSION_VERSION,
        messages
      };
      while (state.messages.length > MAX_MESSAGES) {
        state.messages.shift();
      }
      let serialized = JSON.stringify(state);
      while (serialized.length > MAX_STORAGE_CHARS && state.messages.length > 0) {
        state.messages.shift();
        serialized = JSON.stringify(state);
      }
      localStorage.setItem(key, serialized);
    } catch (error) {
      console.warn('Failed to persist AI agent history', error);
    }
  }

  loadFabPosition(key: string | null): AiAgentFabPosition | null {
    if (!key || typeof localStorage === 'undefined') {
      return null;
    }
    try {
      const raw = localStorage.getItem(key);
      if (!raw) {
        return null;
      }
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed.left !== 'number' || typeof parsed.top !== 'number') {
        return null;
      }
      return {left: parsed.left, top: parsed.top};
    } catch {
      return null;
    }
  }

  saveFabPosition(key: string | null, position: AiAgentFabPosition): void {
    if (!key || typeof localStorage === 'undefined') {
      return;
    }
    try {
      localStorage.setItem(key, JSON.stringify(position));
    } catch (error) {
      console.warn('Failed to persist AI agent button position', error);
    }
  }

  loadPanelState(key: string | null): AiAgentPanelState | null {
    if (!key || typeof localStorage === 'undefined') {
      return null;
    }
    try {
      const raw = localStorage.getItem(key);
      if (!raw) {
        return null;
      }
      const parsed = JSON.parse(raw);
      if (
        typeof parsed?.left !== 'number'
        || typeof parsed?.top !== 'number'
        || typeof parsed?.width !== 'number'
        || typeof parsed?.height !== 'number'
        || !Number.isFinite(parsed.left)
        || !Number.isFinite(parsed.top)
        || !Number.isFinite(parsed.width)
        || !Number.isFinite(parsed.height)
      ) {
        return null;
      }
      return {
        left: parsed.left,
        top: parsed.top,
        width: parsed.width,
        height: parsed.height
      };
    } catch {
      return null;
    }
  }

  savePanelState(key: string | null, state: AiAgentPanelState): void {
    if (!key || typeof localStorage === 'undefined') {
      return;
    }
    try {
      localStorage.setItem(key, JSON.stringify(state));
    } catch (error) {
      console.warn('Failed to persist AI agent panel state', error);
    }
  }

  clear(key: string | null): void {
    if (!key || typeof localStorage === 'undefined') {
      return;
    }
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.warn('Failed to clear AI agent history', error);
    }
  }

  private normalizeMessages(value: unknown): AgentMessage[] {
    if (!Array.isArray(value)) {
      return [];
    }
    return value
      .filter((item): item is AgentMessage =>
        item
        && (item.role === 'user' || item.role === 'assistant')
        && typeof item.content === 'string'
      )
      .map((item) => {
        const files = this.normalizeFiles(item.files);
        return files.length ? {...item, files} : {role: item.role, content: item.content};
      });
  }

  private normalizeFiles(value: unknown): AgentFile[] {
    if (!Array.isArray(value)) {
      return [];
    }
    return value.filter((item): item is AgentFile =>
      item
      && typeof item.id === 'string'
      && typeof item.name === 'string'
      && typeof item.mime_type === 'string'
      && typeof item.size === 'number'
    );
  }

  private normalizeActions(value: unknown): AgentAction[] {
    if (!Array.isArray(value)) {
      return [];
    }
    return value.filter((item): item is AgentAction =>
      item
      && typeof item.id === 'string'
      && typeof item.type === 'string'
      && typeof item.summary === 'string'
      && item.params
      && typeof item.params === 'object'
      && (item.status === 'PROPOSED' || item.status === 'EXECUTED' || item.status === 'FAILED')
    );
  }
}
