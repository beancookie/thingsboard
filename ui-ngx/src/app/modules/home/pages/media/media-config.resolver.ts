// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ResolveFn } from '@angular/router';
import { of } from 'rxjs';
import { catchError } from 'rxjs/operators';

export interface MediaConfig {
  consoleUrl?: string;
}

export const DEFAULT_MEDIA_CONSOLE_URL = 'http://localhost:4201/cameras';

export const mediaConfigResolver: ResolveFn<MediaConfig> = () =>
  inject(HttpClient)
    .get<MediaConfig>(`/assets/media.config.json?t=${Date.now()}`)
    .pipe(catchError(() => of({ consoleUrl: DEFAULT_MEDIA_CONSOLE_URL })));
