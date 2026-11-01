// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { defaultHttpOptionsFromConfig, RequestConfig } from './http-utils';
import {
  CreateProductRequest,
  ProductDetail,
  ProductItem,
  ProductResponse,
  ProductValidationResult,
  ThingModelView,
  UpdateThingModelRequest
} from '@shared/models/product.models';

@Injectable({
  providedIn: 'root'
})
export class ProductService {

  constructor(private http: HttpClient) {
  }

  listProducts(keyword?: string, tenantId?: string, config?: RequestConfig): Observable<ProductItem[]> {
    let url = '/api/thing-model/products';
    const params: string[] = [];
    if (keyword && keyword.trim().length) {
      params.push(`keyword=${encodeURIComponent(keyword.trim())}`);
    }
    if (tenantId) {
      params.push(`tenantId=${encodeURIComponent(tenantId)}`);
    }
    if (params.length) {
      url += `?${params.join('&')}`;
    }
    return this.http.get<ProductItem[]>(url, defaultHttpOptionsFromConfig(config));
  }

  getProduct(productId: string, tenantId?: string, config?: RequestConfig): Observable<ProductDetail> {
    return this.http.get<ProductDetail>(
      `/api/thing-model/products/${encodeURIComponent(productId)}${this.tenantQuery(tenantId)}`,
      defaultHttpOptionsFromConfig(config)
    );
  }

  getThingModel(productId: string, tenantId?: string, config?: RequestConfig): Observable<ThingModelView> {
    return this.http.get<ThingModelView>(
      `/api/thing-model/products/${encodeURIComponent(productId)}/thing-model${this.tenantQuery(tenantId)}`,
      defaultHttpOptionsFromConfig(config)
    );
  }

  createProduct(request: CreateProductRequest, config?: RequestConfig): Observable<ProductResponse> {
    return this.http.post<ProductResponse>(
      '/api/thing-model/products',
      request,
      defaultHttpOptionsFromConfig(config)
    );
  }

  updateThingModel(productId: string, request: UpdateThingModelRequest,
                   tenantId?: string, config?: RequestConfig): Observable<ProductResponse> {
    return this.http.put<ProductResponse>(
      `/api/thing-model/products/${encodeURIComponent(productId)}/thing-model${this.tenantQuery(tenantId)}`,
      request,
      defaultHttpOptionsFromConfig(config)
    );
  }

  validateThingModel(productId: string, tsl: any, tenantId?: string,
                     config?: RequestConfig): Observable<ProductValidationResult> {
    return this.http.post<ProductValidationResult>(
      `/api/thing-model/products/${encodeURIComponent(productId)}/thing-model/validate${this.tenantQuery(tenantId)}`,
      {tsl},
      defaultHttpOptionsFromConfig(config)
    );
  }

  syncProduct(productId: string, tenantId?: string, config?: RequestConfig): Observable<ProductResponse> {
    return this.http.post<ProductResponse>(
      `/api/thing-model/products/${encodeURIComponent(productId)}/sync${this.tenantQuery(tenantId)}`,
      null,
      defaultHttpOptionsFromConfig(config)
    );
  }

  private tenantQuery(tenantId?: string): string {
    return tenantId ? `?tenantId=${encodeURIComponent(tenantId)}` : '';
  }
}
