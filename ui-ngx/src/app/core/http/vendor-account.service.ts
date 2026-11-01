// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { defaultHttpOptionsFromConfig, RequestConfig } from './http-utils';
import { VendorAccount, VendorAccountRequest } from '@shared/models/vendor-account.models';

@Injectable({
  providedIn: 'root'
})
export class VendorAccountService {

  constructor(private http: HttpClient) {
  }

  getAccount(tenantId: string, config?: RequestConfig): Observable<VendorAccount> {
    return this.http.get<VendorAccount>(
      `/api/thing-model/admin/tenants/${encodeURIComponent(tenantId)}/account`,
      defaultHttpOptionsFromConfig(config)
    );
  }

  provision(tenantId: string, request: VendorAccountRequest, config?: RequestConfig): Observable<VendorAccount> {
    return this.http.post<VendorAccount>(
      `/api/thing-model/admin/tenants/${encodeURIComponent(tenantId)}/provision`,
      request,
      defaultHttpOptionsFromConfig(config)
    );
  }

  autoProvision(tenantId: string, force = false, config?: RequestConfig): Observable<VendorAccount> {
    return this.http.post<VendorAccount>(
      `/api/thing-model/admin/tenants/${encodeURIComponent(tenantId)}/provision-auto?force=${force}`,
      null,
      defaultHttpOptionsFromConfig(config)
    );
  }
}
