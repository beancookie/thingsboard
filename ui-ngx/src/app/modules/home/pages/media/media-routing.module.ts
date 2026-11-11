// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { Authority } from '@shared/models/authority.enum';
import { MenuId } from '@core/services/menu.models';
import { MediaComponent } from './media.component';
import { mediaConfigResolver } from './media-config.resolver';

export const mediaRoutes: Routes = [
  {
    path: 'media',
    component: MediaComponent,
    data: {
      auth: [Authority.TENANT_ADMIN],
      title: 'media.cameras',
      breadcrumb: {
        menuId: MenuId.media
      }
    },
    resolve: {
      mediaConfig: mediaConfigResolver
    }
  }
];

const routes: Routes = [
  {
    path: 'media',
    pathMatch: 'full',
    redirectTo: '/entities/media'
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class MediaRoutingModule { }
