// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { DEFAULT_MEDIA_CONSOLE_URL, MediaConfig } from './media-config.resolver';

@Component({
  selector: 'tb-media',
  templateUrl: './media.component.html',
  styleUrls: ['./media.component.scss'],
  standalone: false
})
export class MediaComponent {

  readonly mediaUrl: string;

  constructor(route: ActivatedRoute) {
    const config = route.snapshot.data['mediaConfig'] as MediaConfig | undefined;
    this.mediaUrl = config?.consoleUrl || DEFAULT_MEDIA_CONSOLE_URL;
  }

}
