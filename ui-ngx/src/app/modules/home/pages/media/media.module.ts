// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedModule } from '@shared/shared.module';
import { MediaRoutingModule } from './media-routing.module';
import { MediaComponent } from './media.component';

@NgModule({
  declarations: [
    MediaComponent
  ],
  imports: [
    CommonModule,
    SharedModule,
    MediaRoutingModule
  ]
})
export class MediaModule { }
