// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
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
