// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0

export interface ManualEntry {
  title: string;
  path: string;
}

export interface ApiDocLink {
  labelKey: string;
  icon: string;
  url: string;
}

export interface ResolvedDocLink {
  path: string;
  hash?: string;
}
