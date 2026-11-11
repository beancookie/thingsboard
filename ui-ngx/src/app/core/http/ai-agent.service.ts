// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AgentChatRequest, AgentChatResponse, AgentFile } from '@shared/models/ai-agent.models';
import {
  defaultHttpOptionsFromConfig,
  defaultHttpUploadOptions,
  RequestConfig
} from './http-utils';

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

  uploadFile(file: File): Observable<AgentFile> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return this.http.post<AgentFile>(
      '/api/ai-agent/files',
      formData,
      defaultHttpUploadOptions()
    );
  }
}
