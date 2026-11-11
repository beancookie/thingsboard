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
import { firstValueFrom } from 'rxjs';
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
  AgentFile,
  AgentMessage
} from '@shared/models/ai-agent.models';

const MAX_FILE_BYTES = 2_000_000;
const FAB_SIZE = 56;
const FAB_MARGIN = 24;
const PANEL_WIDTH = 420;
const PANEL_MAX_HEIGHT = 680;
const PANEL_GAP = 12;
const PANEL_MIN_WIDTH = 320;
const PANEL_MIN_HEIGHT = 360;
const PANEL_MARGIN = 8;
const MOBILE_BREAKPOINT = 600;

type ResizeDirection = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw';

interface PanelRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

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
  private readonly panelKey = AiAgentHistoryService.buildPanelKey(
    this.authState.authUser?.tenantId,
    this.authState.authUser?.userId
  );

  readonly panelOpen = signal(false);
  readonly panelRect = signal<PanelRect>({
    left: FAB_MARGIN,
    top: FAB_MARGIN,
    width: PANEL_WIDTH,
    height: PANEL_MAX_HEIGHT
  });
  readonly panelDragging = signal(false);
  readonly panelResizing = signal(false);
  readonly fabPosition = signal<AiAgentFabPosition>({left: FAB_MARGIN, top: FAB_MARGIN});
  readonly messages = signal<AgentMessage[]>([]);
  readonly pendingActions = signal<AgentAction[]>([]);
  readonly attachments = signal<AgentFile[]>([]);
  readonly input = signal('');
  readonly tsl = signal<unknown | null>(null);
  readonly tslFileId = signal<string | null>(null);
  readonly loading = signal(false);
  readonly uploading = signal(false);
  readonly error = signal<string | null>(null);

  readonly canSend = computed(() =>
    this.input().trim().length > 0
    && !this.loading()
    && !this.uploading()
    && this.pendingActions().length === 0
  );

  private dragging = false;
  private dragMoved = false;
  private suppressClick = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private dragStartPosition: AiAgentFabPosition = {left: 0, top: 0};
  private panelDragState: {
    startX: number;
    startY: number;
    startLeft: number;
    startTop: number;
  } | null = null;
  private panelResizeState: {
    direction: ResizeDirection;
    startX: number;
    startY: number;
    startRect: PanelRect;
  } | null = null;

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
    const savedPanel = this.historyService.loadPanelState(this.panelKey);
    this.panelRect.set(this.clampPanelRect(savedPanel ?? this.defaultPanelRect()));
  }

  togglePanel(): void {
    this.panelOpen.update((open) => !open);
    if (this.panelOpen()) {
      this.panelRect.set(this.clampPanelRect(this.panelRect()));
      this.scrollToBottom();
    }
  }

  closePanel(): void {
    this.persistPanelState();
    this.panelOpen.set(false);
  }

  onPanelDragStart(event: PointerEvent): void {
    if (this.isMobile() || (event.target as HTMLElement).closest('button')) {
      return;
    }
    event.preventDefault();
    const rect = this.panelRect();
    this.panelDragState = {
      startX: event.clientX,
      startY: event.clientY,
      startLeft: rect.left,
      startTop: rect.top
    };
    this.panelDragging.set(true);
    this.capturePointer(event);
  }

  onResizeStart(event: PointerEvent, direction: ResizeDirection): void {
    if (this.isMobile()) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    this.panelResizeState = {
      direction,
      startX: event.clientX,
      startY: event.clientY,
      startRect: this.panelRect()
    };
    this.panelResizing.set(true);
    this.capturePointer(event);
  }

  @HostListener('window:pointermove', ['$event'])
  onGlobalPointerMove(event: PointerEvent): void {
    if (this.panelDragState) {
      event.preventDefault();
      const state = this.panelDragState;
      const rect = this.panelRect();
      this.panelRect.set(this.clampPanelRect({
        left: state.startLeft + event.clientX - state.startX,
        top: state.startTop + event.clientY - state.startY,
        width: rect.width,
        height: rect.height
      }));
      return;
    }
    if (this.panelResizeState) {
      event.preventDefault();
      this.panelRect.set(this.resizePanelRect(this.panelResizeState, event));
    }
  }

  @HostListener('window:pointerup')
  @HostListener('window:pointercancel')
  onGlobalPointerUp(): void {
    if (!this.panelDragState && !this.panelResizeState) {
      return;
    }
    this.panelDragState = null;
    this.panelResizeState = null;
    this.panelDragging.set(false);
    this.panelResizing.set(false);
    this.persistPanelState();
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
    const currentPanel = this.panelRect();
    const clampedPanel = this.clampPanelRect(currentPanel);
    if (
      clampedPanel.left !== currentPanel.left
      || clampedPanel.top !== currentPanel.top
      || clampedPanel.width !== currentPanel.width
      || clampedPanel.height !== currentPanel.height
    ) {
      this.panelRect.set(clampedPanel);
      this.persistPanelState();
    }
  }

  clearChat(): void {
    this.historyService.clear(this.storageKey);
    this.messages.set([]);
    this.pendingActions.set([]);
    this.attachments.set([]);
    this.input.set('');
    this.tsl.set(null);
    this.tslFileId.set(null);
    this.error.set(null);
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
    const files = this.attachments();
    const userMessage: AgentMessage = {
      role: 'user',
      content,
      ...(files.length ? {files: [...files]} : {})
    };
    const messages = [...this.messages(), userMessage];
    this.messages.set(messages);
    this.input.set('');
    this.attachments.set([]);
    this.error.set(null);
    this.loading.set(true);
    this.persistSession();
    this.scrollToBottom();

    this.aiAgentService.chat({
      mode: 'chat',
      messages,
      tsl: this.tsl() ?? undefined,
      files: files.length ? files : undefined,
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
        this.tslFileId.set(null);
        this.attachments.set([]);
        this.appendAssistant(this.formatExecutionResponse(response));
      },
      error: (error) => this.handleError(error)
    });
  }

  cancelActions(): void {
    this.pendingActions.set([]);
    this.persistSession();
  }

  onFilesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    input.value = '';
    if (!files.length) {
      return;
    }
    const tooLarge = files.find((file) => file.size > MAX_FILE_BYTES);
    if (tooLarge) {
      this.error.set(this.translate.instant('ai-agent.file-too-large'));
      return;
    }
    this.uploading.set(true);
    this.error.set(null);
    this.uploadFiles(files).catch(() => {
      this.error.set(this.translate.instant('ai-agent.upload-failed'));
    }).finally(() => {
      this.uploading.set(false);
    });
  }

  removeAttachment(file: AgentFile): void {
    this.attachments.update((files) => files.filter((item) => item.id !== file.id));
    if (this.tslFileId() === file.id) {
      this.tsl.set(null);
      this.tslFileId.set(null);
    }
  }

  formatFileSize(size: number): string {
    if (size < 1024) {
      return `${size} B`;
    }
    if (size < 1024 * 1024) {
      return `${(size / 1024).toFixed(1)} KB`;
    }
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }

  private async uploadFiles(files: File[]): Promise<void> {
    const uploaded = await Promise.all(files.map(async (file) => {
      const text = this.isJsonFile(file) ? await file.text() : null;
      const meta = await firstValueFrom(this.aiAgentService.uploadFile(file));
      return {meta, text};
    }));
    for (const item of uploaded) {
      this.attachments.update((files) => [...files, item.meta]);
      if (item.text) {
        this.applyTslFile(item.text, item.meta);
      }
    }
  }

  private applyTslFile(text: string, file: AgentFile): void {
    if (this.tsl()) {
      return;
    }
    try {
      const parsed = JSON.parse(text);
      if (this.looksLikeTsl(parsed)) {
        this.tsl.set(parsed);
        this.tslFileId.set(file.id);
      }
    } catch {
      // Non-TSL JSON is still kept as a regular attachment.
    }
  }

  private looksLikeTsl(value: unknown): boolean {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) {
      return false;
    }
    const record = value as Record<string, unknown>;
    return ['profile', 'properties', 'events', 'actions'].some((key) => key in record);
  }

  private isJsonFile(file: File): boolean {
    return file.type === 'application/json' || file.name.toLowerCase().endsWith('.json');
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

  private defaultPanelRect(): PanelRect {
    const viewportWidth = this.window?.innerWidth || 1024;
    const viewportHeight = this.window?.innerHeight || 768;
    const width = Math.min(
      PANEL_WIDTH,
      Math.max(PANEL_MIN_WIDTH, viewportWidth - FAB_MARGIN * 2)
    );
    const height = Math.min(
      PANEL_MAX_HEIGHT,
      Math.max(PANEL_MIN_HEIGHT, viewportHeight - 140)
    );
    const fab = this.fabPosition();
    let left = fab.left + FAB_SIZE - width;
    if (left < FAB_MARGIN) {
      left = fab.left;
    }
    let top = fab.top - height - PANEL_GAP;
    if (top < FAB_MARGIN) {
      top = fab.top + FAB_SIZE + PANEL_GAP;
    }
    return this.clampPanelRect({left, top, width, height});
  }

  private resizePanelRect(
    state: {
      direction: ResizeDirection;
      startX: number;
      startY: number;
      startRect: PanelRect;
    },
    event: PointerEvent
  ): PanelRect {
    const direction = state.direction;
    const start = state.startRect;
    const dx = event.clientX - state.startX;
    const dy = event.clientY - state.startY;
    const viewportWidth = this.window?.innerWidth || 1024;
    const viewportHeight = this.window?.innerHeight || 768;
    let left = start.left;
    let top = start.top;
    let width = start.width;
    let height = start.height;

    if (direction.includes('w')) {
      const right = start.left + start.width;
      left = Math.min(
        Math.max(start.left + dx, PANEL_MARGIN),
        right - PANEL_MIN_WIDTH
      );
      width = right - left;
    } else if (direction.includes('e')) {
      width = Math.min(
        Math.max(start.width + dx, PANEL_MIN_WIDTH),
        viewportWidth - PANEL_MARGIN - left
      );
    }

    if (direction.includes('n')) {
      const bottom = start.top + start.height;
      top = Math.min(
        Math.max(start.top + dy, PANEL_MARGIN),
        bottom - PANEL_MIN_HEIGHT
      );
      height = bottom - top;
    } else if (direction.includes('s')) {
      height = Math.min(
        Math.max(start.height + dy, PANEL_MIN_HEIGHT),
        viewportHeight - PANEL_MARGIN - top
      );
    }

    return this.clampPanelRect({left, top, width, height});
  }

  private clampPanelRect(rect: PanelRect): PanelRect {
    const viewportWidth = this.window?.innerWidth || 1024;
    const viewportHeight = this.window?.innerHeight || 768;
    const maxWidth = Math.max(PANEL_MIN_WIDTH, viewportWidth - PANEL_MARGIN * 2);
    const maxHeight = Math.max(PANEL_MIN_HEIGHT, viewportHeight - PANEL_MARGIN * 2);
    const width = Math.min(Math.max(rect.width, PANEL_MIN_WIDTH), maxWidth);
    const height = Math.min(Math.max(rect.height, PANEL_MIN_HEIGHT), maxHeight);
    const left = Math.min(
      Math.max(rect.left, PANEL_MARGIN),
      Math.max(PANEL_MARGIN, viewportWidth - width - PANEL_MARGIN)
    );
    const top = Math.min(
      Math.max(rect.top, PANEL_MARGIN),
      Math.max(PANEL_MARGIN, viewportHeight - height - PANEL_MARGIN)
    );
    return {
      left: Math.round(left),
      top: Math.round(top),
      width: Math.round(width),
      height: Math.round(height)
    };
  }

  private capturePointer(event: PointerEvent): void {
    const target = event.currentTarget as HTMLElement | null;
    try {
      target?.setPointerCapture(event.pointerId);
    } catch {
      // Pointer capture is not available in some embedded browsers.
    }
  }

  private persistPanelState(): void {
    this.historyService.savePanelState(this.panelKey, this.panelRect());
  }

  private isMobile(): boolean {
    return (this.window?.innerWidth || 1024) <= MOBILE_BREAKPOINT;
  }

  private restoreSession(): void {
    const session = this.historyService.load(this.storageKey);
    if (!session) {
      return;
    }
    this.messages.set(session.messages);
    this.pendingActions.set(session.pendingActions);
    this.tsl.set(session.tsl);
  }

  private persistSession(): void {
    this.historyService.save(this.storageKey, {
      version: 1,
      messages: this.messages(),
      pendingActions: this.pendingActions(),
      tsl: this.tsl(),
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
