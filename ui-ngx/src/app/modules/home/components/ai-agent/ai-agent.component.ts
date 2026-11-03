// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  HostListener,
  Inject,
  ViewChild,
  computed,
  signal
} from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Store } from '@ngrx/store';
import { getCurrentAuthState } from '@core/auth/auth.selectors';
import { AiAgentService } from '@core/http/ai-agent.service';
import { AiAgentFabPosition, AiAgentHistoryService } from '@core/services/ai-agent-history.service';
import { AppState } from '@core/core.state';
import { WINDOW } from '@core/services/window.service';
import { SharedModule } from '@shared/shared.module';
import { Authority } from '@shared/models/authority.enum';
import {
  AgentAction,
  AgentChatResponse,
  AgentMessage
} from '@shared/models/ai-agent.models';

const MAX_TSL_BYTES = 2_000_000;
const FAB_SIZE = 56;
const FAB_MARGIN = 24;
const PANEL_WIDTH = 420;
const PANEL_MAX_HEIGHT = 680;
const PANEL_GAP = 12;

@Component({
  selector: 'tb-ai-agent',
  templateUrl: './ai-agent.component.html',
  styleUrls: ['./ai-agent.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatDividerModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    TranslateModule,
    SharedModule
  ]
})
export class AiAgentComponent {

  private readonly authState = getCurrentAuthState(this.store);
  private readonly allowedAuthorities = [Authority.SYS_ADMIN, Authority.TENANT_ADMIN];

  readonly visible = this.allowedAuthorities.includes(this.authState.authUser?.authority);
  private readonly storageKey = AiAgentHistoryService.buildKey(
    this.authState.authUser?.tenantId,
    this.authState.authUser?.userId
  );
  private readonly positionKey = AiAgentHistoryService.buildPositionKey(
    this.authState.authUser?.tenantId,
    this.authState.authUser?.userId
  );

  readonly panelOpen = signal(false);
  readonly fabPosition = signal<AiAgentFabPosition>({left: FAB_MARGIN, top: FAB_MARGIN});
  readonly messages = signal<AgentMessage[]>([]);
  readonly pendingActions = signal<AgentAction[]>([]);
  readonly input = signal('');
  readonly tslText = signal('');
  readonly showTslEditor = signal(false);
  readonly tsl = signal<unknown | null>(null);
  readonly tslFileName = signal<string | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  readonly canSend = computed(() =>
    this.input().trim().length > 0
    && !this.loading()
    && this.pendingActions().length === 0
  );

  readonly panelPosition = computed(() => this.calculatePanelPosition(this.fabPosition()));

  private dragging = false;
  private dragMoved = false;
  private suppressClick = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private dragStartPosition: AiAgentFabPosition = {left: 0, top: 0};

  @ViewChild('messagesContainer') messagesContainer?: ElementRef<HTMLDivElement>;

  constructor(private store: Store<AppState>,
              private router: Router,
              private translate: TranslateService,
              private aiAgentService: AiAgentService,
              private historyService: AiAgentHistoryService,
              @Inject(WINDOW) private window: Window) {
    this.restoreSession();
    const savedPosition = this.historyService.loadFabPosition(this.positionKey);
    this.fabPosition.set(this.clampFabPosition(savedPosition ?? this.defaultFabPosition()));
  }

  togglePanel(): void {
    this.panelOpen.update((open) => !open);
    if (this.panelOpen()) {
      this.scrollToBottom();
    }
  }

  closePanel(): void {
    this.panelOpen.set(false);
  }

  onFabPointerDown(event: PointerEvent): void {
    if (event.pointerType === 'mouse' && event.button !== 0) {
      return;
    }
    this.dragging = true;
    this.dragMoved = false;
    this.dragStartX = event.clientX;
    this.dragStartY = event.clientY;
    this.dragStartPosition = this.fabPosition();
    const target = event.currentTarget as HTMLElement;
    try {
      target.setPointerCapture(event.pointerId);
    } catch {
      // Pointer capture is not available in some embedded browsers.
    }
  }

  onFabPointerMove(event: PointerEvent): void {
    if (!this.dragging) {
      return;
    }
    const deltaX = event.clientX - this.dragStartX;
    const deltaY = event.clientY - this.dragStartY;
    if (!this.dragMoved && Math.abs(deltaX) < 4 && Math.abs(deltaY) < 4) {
      return;
    }
    this.dragMoved = true;
    this.fabPosition.set(this.clampFabPosition({
      left: this.dragStartPosition.left + deltaX,
      top: this.dragStartPosition.top + deltaY
    }));
    event.preventDefault();
  }

  onFabPointerUp(event: PointerEvent): void {
    if (!this.dragging) {
      return;
    }
    this.dragging = false;
    const target = event.currentTarget as HTMLElement;
    try {
      target.releasePointerCapture(event.pointerId);
    } catch {
      // Pointer capture is not available in some embedded browsers.
    }
    if (this.dragMoved) {
      this.historyService.saveFabPosition(this.positionKey, this.fabPosition());
      this.suppressClick = true;
      setTimeout(() => {
        this.suppressClick = false;
      }, 50);
    }
  }

  onFabClick(event: Event): void {
    if (this.suppressClick) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    this.togglePanel();
  }

  @HostListener('window:resize')
  onWindowResize(): void {
    const clamped = this.clampFabPosition(this.fabPosition());
    if (clamped.left !== this.fabPosition().left || clamped.top !== this.fabPosition().top) {
      this.fabPosition.set(clamped);
      this.historyService.saveFabPosition(this.positionKey, clamped);
    }
  }

  clearChat(): void {
    this.historyService.clear(this.storageKey);
    this.messages.set([]);
    this.pendingActions.set([]);
    this.input.set('');
    this.tsl.set(null);
    this.tslText.set('');
    this.tslFileName.set(null);
    this.error.set(null);
    this.showTslEditor.set(false);
  }

  onInputKeydown(event: Event): void {
    const keyboardEvent = event as KeyboardEvent;
    if (keyboardEvent.key === 'Enter' && !keyboardEvent.shiftKey) {
      keyboardEvent.preventDefault();
      this.sendMessage();
    }
  }

  sendMessage(): void {
    if (!this.canSend()) {
      return;
    }
    const content = this.input().trim();
    const messages = [...this.messages(), {role: 'user', content} as AgentMessage];
    this.messages.set(messages);
    this.input.set('');
    this.error.set(null);
    this.loading.set(true);
    this.persistSession();
    this.scrollToBottom();

    this.aiAgentService.chat({
      mode: 'chat',
      messages,
      tsl: this.tsl() ?? undefined,
      context: this.buildContext()
    }).subscribe({
      next: (response) => this.handleChatResponse(response),
      error: (error) => this.handleError(error)
    });
  }

  confirmActions(): void {
    if (!this.pendingActions().length || this.loading()) {
      return;
    }
    const actions = this.pendingActions();
    this.error.set(null);
    this.loading.set(true);

    this.aiAgentService.chat({
      mode: 'execute',
      messages: [],
      actions,
      tsl: this.tsl() ?? undefined,
      context: this.buildContext()
    }).subscribe({
      next: (response) => {
        this.loading.set(false);
        this.pendingActions.set([]);
        this.tsl.set(null);
        this.tslText.set('');
        this.tslFileName.set(null);
        this.appendAssistant(this.formatExecutionResponse(response));
      },
      error: (error) => this.handleError(error)
    });
  }

  cancelActions(): void {
    this.pendingActions.set([]);
    this.persistSession();
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) {
      return;
    }
    if (file.size > MAX_TSL_BYTES) {
      this.error.set(this.translate.instant('ai-agent.tsl-too-large'));
      return;
    }
    file.text().then((text) => {
      this.applyTslText(text, file.name);
    }).catch(() => {
      this.error.set(this.translate.instant('ai-agent.invalid-json'));
    });
  }

  applyPastedTsl(): void {
    this.applyTslText(this.tslText(), 'pasted-tsl.json');
  }

  clearTsl(): void {
    this.tsl.set(null);
    this.tslText.set('');
    this.tslFileName.set(null);
    this.showTslEditor.set(false);
    this.persistSession();
  }

  private applyTslText(text: string, fileName: string): void {
    try {
      const parsed = JSON.parse(text);
      if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('TSL must be an object');
      }
      this.tsl.set(parsed);
      this.tslText.set(text);
      this.tslFileName.set(fileName);
      this.error.set(null);
      this.showTslEditor.set(false);
      this.persistSession();
    } catch {
      this.error.set(this.translate.instant('ai-agent.invalid-json'));
    }
  }

  private handleChatResponse(response: AgentChatResponse): void {
    this.loading.set(false);
    const reply = response.reply?.trim();
    if (reply) {
      this.appendAssistant(reply);
    }
    if (response.actions?.length) {
      this.pendingActions.set(response.actions);
    }
    this.persistSession();
    this.scrollToBottom();
  }

  private handleError(error: HttpErrorResponse): void {
    this.loading.set(false);
    const message = error?.error?.message || this.translate.instant('ai-agent.operation-failed');
    this.error.set(message);
    this.scrollToBottom();
  }

  private appendAssistant(content: string): void {
    this.messages.update((messages) => [
      ...messages,
      {role: 'assistant', content}
    ]);
    this.persistSession();
    this.scrollToBottom();
  }

  private formatExecutionResponse(response: AgentChatResponse): string {
    const lines = [response.reply?.trim()].filter((line) => !!line);
    response.executed?.forEach((result) => {
      const status = result.success
        ? this.translate.instant('ai-agent.execute-success')
        : this.translate.instant('ai-agent.execute-failed');
      lines.push(`${status}: ${result.message}`);
    });
    return lines.join('\n');
  }

  private buildContext(): {route?: string; product_id?: string; tenant_id?: string} {
    const route = this.router.url;
    const match = route.match(/\/entities\/products\/([^/?]+)/);
    const context: {route?: string; product_id?: string; tenant_id?: string} = {
      route
    };
    if (match?.[1]) {
      context.product_id = decodeURIComponent(match[1]);
    }
    if (this.authState.authUser?.tenantId) {
      context.tenant_id = this.authState.authUser.tenantId;
    }
    return context;
  }

  private defaultFabPosition(): AiAgentFabPosition {
    const width = this.window?.innerWidth || 1024;
    const height = this.window?.innerHeight || 768;
    return {
      left: width - FAB_SIZE - FAB_MARGIN,
      top: height - FAB_SIZE - FAB_MARGIN
    };
  }

  private clampFabPosition(position: AiAgentFabPosition): AiAgentFabPosition {
    const width = this.window?.innerWidth || 1024;
    const height = this.window?.innerHeight || 768;
    const maxLeft = Math.max(FAB_MARGIN, width - FAB_SIZE - FAB_MARGIN);
    const maxTop = Math.max(FAB_MARGIN, height - FAB_SIZE - FAB_MARGIN);
    return {
      left: Math.min(Math.max(position.left, FAB_MARGIN), maxLeft),
      top: Math.min(Math.max(position.top, FAB_MARGIN), maxTop)
    };
  }

  private calculatePanelPosition(fab: AiAgentFabPosition): AiAgentFabPosition {
    const width = this.window?.innerWidth || 1024;
    const height = this.window?.innerHeight || 768;
    const panelWidth = Math.min(PANEL_WIDTH, Math.max(260, width - FAB_MARGIN * 2));
    const panelHeight = Math.max(240, Math.min(PANEL_MAX_HEIGHT, height - 140));
    let left = fab.left + FAB_SIZE - panelWidth;
    if (left < FAB_MARGIN) {
      left = fab.left;
    }
    left = Math.min(
      Math.max(left, FAB_MARGIN),
      Math.max(FAB_MARGIN, width - panelWidth - FAB_MARGIN)
    );
    let top = fab.top - panelHeight - PANEL_GAP;
    if (top < FAB_MARGIN) {
      top = fab.top + FAB_SIZE + PANEL_GAP;
    }
    top = Math.min(
      Math.max(top, FAB_MARGIN),
      Math.max(FAB_MARGIN, height - panelHeight - FAB_MARGIN)
    );
    return {left, top};
  }

  private restoreSession(): void {
    const session = this.historyService.load(this.storageKey);
    if (!session) {
      return;
    }
    this.messages.set(session.messages);
    this.pendingActions.set(session.pendingActions);
    this.tsl.set(session.tsl);
    this.tslFileName.set(session.tslFileName);
    if (session.tsl !== null && session.tsl !== undefined) {
      this.tslText.set(JSON.stringify(session.tsl, null, 2));
    }
  }

  private persistSession(): void {
    this.historyService.save(this.storageKey, {
      version: 1,
      messages: this.messages(),
      pendingActions: this.pendingActions(),
      tsl: this.tsl(),
      tslFileName: this.tslFileName(),
      savedAt: new Date().toISOString()
    });
  }

  onMarkdownReady(): void {
    this.scrollToBottom();
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const container = this.messagesContainer?.nativeElement;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    });
  }
}
