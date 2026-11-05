// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
export const VENDOR_SERVICE_ACCOUNT_EMAIL_PREFIX = 'thing-model-svc-';

export function isVendorServiceAccountEmail(email?: string, tenantId?: string): boolean {
  if (!email) {
    return false;
  }
  const normalizedEmail = email.toLowerCase();
  const prefix = tenantId
    ? `${VENDOR_SERVICE_ACCOUNT_EMAIL_PREFIX}${tenantId}`.toLowerCase()
    : VENDOR_SERVICE_ACCOUNT_EMAIL_PREFIX;
  return normalizedEmail.startsWith(prefix);
}

export interface VendorAccount {
  tenantId: string;
  username: string;
  enabled: boolean;
}

export interface VendorAccountRequest {
  username: string;
  password: string;
  force?: boolean;
}
