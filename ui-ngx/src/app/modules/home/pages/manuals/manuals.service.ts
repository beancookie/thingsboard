// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, shareReplay, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { ExampleEntry, ExamplesManifest, ManualEntry, ResolvedDocLink } from './manual.models';

const DOCS_BASE_PATH = '/assets/docs/';
const MANUALS_INDEX_PATH = 'manuals/README.md';
const EXAMPLES_INDEX_PATH = 'examples/examples.json';

@Injectable({
  providedIn: 'root'
})
export class ManualsService {

  private index$: Observable<ManualEntry[]> | null = null;
  private examples$: Observable<ExampleEntry[]> | null = null;
  private readonly contentCache = new Map<string, Observable<string>>();

  constructor(private http: HttpClient) {
  }

  getIndex(): Observable<ManualEntry[]> {
    if (!this.index$) {
      this.index$ = this.http.get(`${DOCS_BASE_PATH}${MANUALS_INDEX_PATH}`, {responseType: 'text'}).pipe(
        map((readme) => this.parseIndex(readme)),
        catchError((error) => {
          this.index$ = null;
          return throwError(() => error);
        }),
        shareReplay({bufferSize: 1, refCount: false})
      );
    }
    return this.index$!;
  }

  getExamples(): Observable<ExampleEntry[]> {
    if (!this.examples$) {
      this.examples$ = this.http.get(`${DOCS_BASE_PATH}${EXAMPLES_INDEX_PATH}`).pipe(
        map((manifest: ExamplesManifest) => (manifest?.examples || []).filter((example) => !!example?.id && !!example?.readme)),
        catchError((error) => {
          this.examples$ = null;
          return throwError(() => error);
        }),
        shareReplay({bufferSize: 1, refCount: false})
      );
    }
    return this.examples$!;
  }

  getContent(path: string): Observable<string> {
    const normalizedPath = this.normalizePath(path);
    if (!this.contentCache.has(normalizedPath)) {
      this.contentCache.set(
        normalizedPath,
        this.http.get(`${DOCS_BASE_PATH}${encodeURI(normalizedPath)}`, {responseType: 'text'}).pipe(
          shareReplay({bufferSize: 1, refCount: false})
        )
      );
    }
    return this.contentCache.get(normalizedPath)!;
  }

  clearContent(path: string): void {
    this.contentCache.delete(this.normalizePath(path));
  }

  preprocessMarkdown(markdown: string, currentPath: string): string {
    const imageRegex = /!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;
    return markdown.replace(imageRegex, (match, alt: string, href: string) => {
      const resolved = this.resolveDocLink(currentPath, href);
      if (!resolved) {
        return match;
      }
      return `![${alt}](${this.assetUrl(resolved.path)}${resolved.hash || ''})`;
    });
  }

  resolveDocLink(currentPath: string, href: string): ResolvedDocLink | null {
    const value = (href || '').trim();
    if (!value || value.startsWith('#') || /^(https?:|mailto:|tel:|data:|javascript:)/i.test(value)) {
      return null;
    }
    try {
      const base = new URL(`${DOCS_BASE_PATH}${encodeURI(this.normalizePath(currentPath))}`, window.location.origin);
      const target = new URL(value, base);
      if (target.origin !== base.origin || !target.pathname.startsWith(DOCS_BASE_PATH)) {
        return null;
      }
      return {
        path: this.normalizePath(decodeURIComponent(target.pathname.substring(DOCS_BASE_PATH.length))),
        hash: target.hash || undefined
      };
    } catch {
      return null;
    }
  }

  assetUrl(path: string): string {
    return `${DOCS_BASE_PATH}${encodeURI(this.normalizePath(path))}`;
  }

  private parseIndex(readme: string): ManualEntry[] {
    const result: ManualEntry[] = [];
    const seen = new Set<string>();
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    let match: RegExpExecArray | null;
    while ((match = linkRegex.exec(readme)) !== null) {
      const title = match[1].trim();
      const href = match[2].trim().split('#')[0];
      if (!href || href.startsWith('http') || href.startsWith('mailto:') ||
          href.startsWith('#') || href.startsWith('../') || href.startsWith('images/') ||
          !href.endsWith('使用手册.md')) {
        continue;
      }
      const path = this.normalizePath(`manuals/${href}`);
      if (!seen.has(path)) {
        seen.add(path);
        result.push({title: title || href, path});
      }
    }
    return result;
  }

  private normalizePath(path: string): string {
    return (path || '')
      .trim()
      .replace(/^\/+/, '')
      .replace(/^assets\/docs\//, '')
      .replace(/^\.\//, '');
  }
}
