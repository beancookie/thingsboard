// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { Component, Inject, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { UserService } from '@core/http/user.service';
import { VendorAccountService } from '@core/http/vendor-account.service';
import { PageLink } from '@shared/models/page/page-link';
import { User } from '@shared/models/user.model';
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

  form: FormGroup;

  tenantAdmins: User[] = [];

  existing: VendorAccount;

  isLoading = true;

  isSaving = false;

  errorMessage: string;

  constructor(private dialogRef: MatDialogRef<TenantVendorAccountDialogComponent, VendorAccount>,
              @Inject(MAT_DIALOG_DATA) public data: TenantVendorAccountDialogData,
              private fb: FormBuilder,
              private router: Router,
              private userService: UserService,
              private vendorAccountService: VendorAccountService) {
    this.form = this.fb.group({
      username: ['', [Validators.required, Validators.maxLength(255)]],
      password: ['', [Validators.required]]
    });
  }

  ngOnInit(): void {
    this.load();
  }

  get hasTenantAdmin(): boolean {
    return this.tenantAdmins.length > 0;
  }

  save(): void {
    if (this.form.invalid || this.isSaving || !this.hasTenantAdmin) {
      this.form.markAllAsTouched();
      return;
    }
    this.isSaving = true;
    this.errorMessage = null;
    const value = this.form.getRawValue();
    this.vendorAccountService.provision(this.data.tenantId, {
      username: value.username,
      password: value.password,
      force: !!this.existing
    }).subscribe(
      (account) => this.dialogRef.close(account),
      (error: HttpErrorResponse) => {
        this.isSaving = false;
        this.errorMessage = error?.error?.message || 'product.operation-failed';
      }
    );
  }

  goToTenantAdmins(): void {
    this.dialogRef.close(null);
    this.router.navigate(['/tenants', this.data.tenantId, 'users']);
  }

  cancel(): void {
    this.dialogRef.close(null);
  }

  private load(): void {
    this.vendorAccountService.getAccount(this.data.tenantId).pipe(
      catchError(() => of(null))
    ).subscribe((account) => {
      this.existing = account;
      if (account?.username) {
        this.form.patchValue({username: account.username});
      }
      this.userService.getTenantAdmins(
        this.data.tenantId,
        new PageLink(100, 0)
      ).subscribe(
        (page) => {
          this.tenantAdmins = page.data || [];
          if (!this.form.get('username').value && this.tenantAdmins.length) {
            this.form.patchValue({username: this.tenantAdmins[0].email});
          }
          this.isLoading = false;
        },
        (error: HttpErrorResponse) => {
          this.isLoading = false;
          this.errorMessage = error?.error?.message || 'product.operation-failed';
        }
      );
    });
  }
}
