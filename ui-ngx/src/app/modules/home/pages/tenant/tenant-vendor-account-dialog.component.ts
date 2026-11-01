// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { Component, Inject, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { VendorAccountService } from '@core/http/vendor-account.service';
import { VendorAccount } from '@shared/models/vendor-account.models';

export interface TenantVendorAccountDialogData {
  tenantId: string;
  tenantTitle?: string;
}

@Component({
  selector: 'tb-tenant-vendor-account-dialog',
  templateUrl: './tenant-vendor-account-dialog.component.html',
  styleUrls: ['./tenant-vendor-account-dialog.component.scss'],
  standalone: false
})
export class TenantVendorAccountDialogComponent implements OnInit {

  isProvisioning = false;

  errorMessage: string;

  account: VendorAccount;

  constructor(private dialogRef: MatDialogRef<TenantVendorAccountDialogComponent, VendorAccount>,
              @Inject(MAT_DIALOG_DATA) public data: TenantVendorAccountDialogData,
              private vendorAccountService: VendorAccountService) {
  }

  ngOnInit(): void {
    this.provision();
  }

  provision(): void {
    this.isProvisioning = true;
    this.errorMessage = null;
    this.account = null;
    this.vendorAccountService.autoProvision(this.data.tenantId).subscribe(
      (account) => {
        this.account = account;
        this.isProvisioning = false;
      },
      (error: HttpErrorResponse) => {
        this.isProvisioning = false;
        this.errorMessage = error?.error?.message || 'product.operation-failed';
      }
    );
  }

  close(): void {
    this.dialogRef.close(this.account);
  }
}
