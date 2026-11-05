// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedModule } from '@app/shared/shared.module';
import { ManualsRoutingModule } from './manuals-routing.module';
import { ManualsComponent } from './manuals.component';

@NgModule({
  declarations: [
    ManualsComponent
  ],
  imports: [
    CommonModule,
    SharedModule,
    ManualsRoutingModule
  ]
})
export class ManualsModule { }
