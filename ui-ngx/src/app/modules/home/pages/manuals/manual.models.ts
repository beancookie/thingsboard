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

export type ExampleFileGroup = 'python' | 'java' | 'shared';

export interface ExampleFile {
  name: string;
  path: string;
  language: string;
  group?: ExampleFileGroup;
}

export interface ExampleEntry {
  id: string;
  title: string;
  description: string;
  category?: string;
  protocol?: string;
  readme: string;
  entry?: string;
  files: ExampleFile[];
}

export interface ExamplesManifest {
  examples: ExampleEntry[];
}

export interface ExampleGroup {
  category: string;
  examples: ExampleEntry[];
}
