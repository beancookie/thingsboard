// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedModule } from '@app/shared/shared.module';
import { ServiceInfoRoutingModule } from './service-info-routing.module';
import { ServiceInfoComponent } from './service-info.component';

@NgModule({
  declarations: [
    ServiceInfoComponent
  ],
  imports: [
    CommonModule,
    SharedModule,
    ServiceInfoRoutingModule
  ]
})
export class ServiceInfoModule { }
