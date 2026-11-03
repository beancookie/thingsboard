// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AgentChatRequest, AgentChatResponse } from '@shared/models/ai-agent.models';
import { defaultHttpOptionsFromConfig, RequestConfig } from './http-utils';

@Injectable({
  providedIn: 'root'
})
export class AiAgentService {

  constructor(private http: HttpClient) {
  }

  chat(request: AgentChatRequest, config?: RequestConfig): Observable<AgentChatResponse> {
    return this.http.post<AgentChatResponse>(
      '/api/ai-agent/chat',
      request,
      defaultHttpOptionsFromConfig(config)
    );
  }
}
