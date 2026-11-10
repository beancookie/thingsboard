// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { Component, DestroyRef, ElementRef, OnInit, ViewChild, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MatDrawer } from '@angular/material/sidenav';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { firstValueFrom } from 'rxjs';
import { MediaBreakpoints } from '@shared/models/constants';
import { ExampleEntry, ExampleFile, ExampleFileGroup, ExampleGroup } from '@home/pages/manuals/manual.models';
import { ManualsService } from '@home/pages/manuals/manuals.service';

@Component({
  selector: 'tb-examples',
  templateUrl: './examples.component.html',
  styleUrls: ['./examples.component.scss'],
  standalone: false
})
export class ExamplesComponent implements OnInit {

  @ViewChild('drawer') drawer: MatDrawer;
  @ViewChild('contentScroller') contentScroller: ElementRef<HTMLElement>;

  examples: ExampleEntry[] = [];
  filteredExamples: ExampleEntry[] = [];
  exampleGroups: ExampleGroup[] = [];
  selectedExample: ExampleEntry | null = null;
  selectedExampleFile: ExampleFile | null = null;
  exampleReadme: string | null = null;
  exampleSource: string | null = null;
  exampleTabIndex = 0;
  searchText = '';
  examplesLoading = true;
  exampleContentLoading = false;
  downloading = false;
  error: string | null = null;
  drawerMode: 'side' | 'over' = 'side';
  drawerOpen = true;

  private pendingExampleId: string | null = null;
  private readonly exampleCategoryOrder = ['设备接入', '产品管理', '规则与告警', '组织与权限', '开发辅助'];
  private readonly destroyRef = inject(DestroyRef);

  constructor(private route: ActivatedRoute,
              private router: Router,
              private manualsService: ManualsService,
              private breakpointObserver: BreakpointObserver) {
  }

  ngOnInit(): void {
    this.breakpointObserver.observe(MediaBreakpoints['gt-sm']).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe((result) => {
      this.drawerMode = result.matches ? 'side' : 'over';
      this.drawerOpen = result.matches;
    });

    this.route.queryParamMap.pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe((params) => {
      const exampleId = params.get('example');
      if (exampleId) {
        this.pendingExampleId = exampleId;
        this.tryLoadExample(exampleId);
      } else {
        this.pendingExampleId = null;
        this.clearExample();
      }
    });

    this.loadExamples();
  }

  loadExamples(): void {
    this.examplesLoading = true;
    this.manualsService.getExamples().pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (examples) => {
        this.examples = examples;
        this.applyFilter();
        this.examplesLoading = false;
        if (this.pendingExampleId) {
          this.tryLoadExample(this.pendingExampleId);
        } else if (!this.route.snapshot.queryParamMap.get('example') && examples.length) {
          this.router.navigate(['/examples'], {
            queryParams: {example: examples[0].id},
            replaceUrl: true
          });
        }
      },
      error: () => {
        this.examplesLoading = false;
        if (this.pendingExampleId) {
          this.error = 'manual.example-load-failed';
        }
      }
    });
  }

  tryLoadExample(id: string): void {
    const entry = this.examples.find((example) => example.id === id);
    if (!entry) {
      if (this.examplesLoading) {
        return;
      }
      this.selectedExample = null;
      this.exampleReadme = null;
      this.exampleSource = null;
      this.selectedExampleFile = null;
      this.error = 'manual.example-not-found';
      return;
    }
    if (this.selectedExample?.id === entry.id && this.exampleReadme) {
      return;
    }
    this.error = null;
    this.selectedExample = entry;
    this.selectedExampleFile = null;
    this.exampleReadme = null;
    this.exampleSource = null;
    this.exampleTabIndex = 0;
    this.exampleContentLoading = true;
    this.manualsService.getContent(entry.readme).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (content) => {
        this.exampleReadme = this.manualsService.preprocessMarkdown(content, entry.readme);
        this.exampleContentLoading = false;
        const defaultFile = entry.files?.find((file) => file.path === entry.entry) || entry.files?.[0];
        if (defaultFile) {
          this.selectExampleFile(defaultFile, false);
        }
        this.scrollToTop();
      },
      error: () => {
        this.manualsService.clearContent(entry.readme);
        this.exampleContentLoading = false;
        this.error = 'manual.example-load-failed';
      }
    });
  }

  selectExampleFile(file: ExampleFile, activate = true): void {
    this.selectedExampleFile = file;
    if (activate) {
      this.exampleTabIndex = this.fileGroup(file) === 'java' ? 2 : 1;
    }
    this.exampleSource = null;
    this.exampleContentLoading = true;
    this.manualsService.getContent(file.path).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (content) => {
        this.exampleSource = content;
        this.exampleContentLoading = false;
      },
      error: () => {
        this.manualsService.clearContent(file.path);
        this.exampleSource = null;
        this.exampleContentLoading = false;
      }
    });
  }

  get pythonFiles(): ExampleFile[] {
    return this.filesForGroup('python');
  }

  get javaFiles(): ExampleFile[] {
    return this.filesForGroup('java');
  }

  get hasFilesForCurrentTab(): boolean {
    return this.exampleFilesForCurrentTab().length > 0;
  }

  onExampleTabChange(index: number): void {
    this.exampleTabIndex = index;
    if (index === 1) {
      this.ensureFileForGroup('python');
    } else if (index === 2) {
      this.ensureFileForGroup('java');
    }
  }

  onSearch(value: string): void {
    this.searchText = value;
    this.applyFilter();
  }

  selectExample(example: ExampleEntry): void {
    this.router.navigate(['/examples'], {
      queryParams: {example: example.id}
    });
    if (this.drawerMode === 'over') {
      this.drawer.close();
    }
  }

  toggleDrawer(): void {
    this.drawer.toggle();
  }

  retry(): void {
    if (this.selectedExample && this.error === 'manual.example-load-failed') {
      this.manualsService.clearContent(this.selectedExample.readme);
      this.tryLoadExample(this.selectedExample.id);
    } else if (!this.examples.length) {
      this.loadExamples();
    }
  }

  assetUrl(path: string): string {
    return this.manualsService.assetUrl(path);
  }

  async downloadExample(): Promise<void> {
    if (!this.selectedExample || this.downloading) {
      return;
    }
    const files = this.exampleFilesForCurrentTab();
    if (!files.length) {
      return;
    }
    this.downloading = true;
    try {
      const JSZip = (await import('jszip')).default;
      const zip = new JSZip();
      const contents = await Promise.all(files.map(async (file) => {
        try {
          const content = await firstValueFrom(this.manualsService.getContent(file.path));
          return {path: this.exampleRelativePath(file), content};
        } catch {
          return null;
        }
      }));
      for (const item of contents) {
        if (item) {
          zip.file(item.path, item.content);
        }
      }
      const blob = await zip.generateAsync({type: 'blob'});
      this.triggerBlobDownload(blob, `${this.selectedExample.id}.zip`);
    } catch (e) {
      console.error('Failed to download example archive', e);
    } finally {
      this.downloading = false;
    }
  }

  private exampleFilesForCurrentTab(): ExampleFile[] {
    return this.filesForGroup(this.exampleTabIndex === 2 ? 'java' : 'python');
  }

  private filesForGroup(group: ExampleFileGroup): ExampleFile[] {
    const files = this.selectedExample?.files || [];
    const groupFiles = files.filter((file) => this.fileGroup(file) === group);
    if (!groupFiles.length) {
      return [];
    }
    const sharedFiles = files.filter((file) => this.fileGroup(file) === 'shared');
    return [...groupFiles, ...sharedFiles];
  }

  private fileGroup(file: ExampleFile): ExampleFileGroup {
    return file.group || this.inferFileGroup(file);
  }

  private ensureFileForGroup(group: ExampleFileGroup): void {
    const files = this.filesForGroup(group);
    if (!files.length) {
      this.selectedExampleFile = null;
      this.exampleSource = null;
      return;
    }
    if (this.selectedExampleFile && files.some((file) => file.path === this.selectedExampleFile.path)) {
      return;
    }
    this.selectExampleFile(files[0], false);
  }

  private inferFileGroup(file: ExampleFile): ExampleFileGroup {
    if (file.name === 'README.md') {
      return 'shared';
    }
    if (file.language === 'java' || file.language === 'xml' ||
        file.name === 'pom.xml' || file.path.includes('/java/')) {
      return 'java';
    }
    return 'python';
  }

  private exampleRelativePath(file: ExampleFile): string {
    const exampleId = this.selectedExample?.id;
    if (!exampleId) {
      return file.name;
    }
    const prefix = `examples/${exampleId}/`;
    return file.path.startsWith(prefix) ? file.path.substring(prefix.length) : file.name;
  }

  private triggerBlobDownload(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  onMarkdownClick(event: MouseEvent): void {
    const currentPath = this.selectedExample?.readme;
    if (event.defaultPrevented || event.button !== 0 || !currentPath) {
      return;
    }
    const target = event.target as HTMLElement;
    const anchor = target.closest('a');
    if (!anchor) {
      return;
    }
    const href = anchor.getAttribute('href');
    if (!href) {
      return;
    }
    const resolved = this.manualsService.resolveDocLink(currentPath, href);
    if (!resolved) {
      return;
    }
    event.preventDefault();
    if (resolved.path.toLowerCase().endsWith('.md')) {
      const example = this.examples.find((item) => item.readme === resolved.path);
      if (example) {
        this.router.navigate(['/examples'], {
          queryParams: {example: example.id}
        });
      } else {
        this.router.navigate(['/manuals'], {
          queryParams: {doc: resolved.path}
        });
      }
    } else {
      window.open(this.manualsService.assetUrl(resolved.path), '_blank', 'noopener');
    }
  }

  get exampleSourceMarkdown(): string {
    if (!this.exampleSource || !this.selectedExampleFile) {
      return '';
    }
    const language = this.selectedExampleFile.language || 'text';
    return '```' + language + '\n' + this.exampleSource + '\n```';
  }

  private clearExample(): void {
    this.selectedExample = null;
    this.selectedExampleFile = null;
    this.exampleReadme = null;
    this.exampleSource = null;
    this.exampleTabIndex = 0;
    this.exampleContentLoading = false;
  }

  private applyFilter(): void {
    const search = this.searchText.trim().toLowerCase();
    if (!search) {
      this.filteredExamples = this.examples;
    } else {
      this.filteredExamples = this.examples.filter((example) =>
        example.title.toLowerCase().includes(search) ||
        (example.description || '').toLowerCase().includes(search) ||
        (example.category || '').toLowerCase().includes(search) ||
        (example.protocol || '').toLowerCase().includes(search)
      );
    }
    this.exampleGroups = this.groupExamples(this.filteredExamples);
  }

  private groupExamples(examples: ExampleEntry[]): ExampleGroup[] {
    const grouped = new Map<string, ExampleEntry[]>();
    for (const example of examples) {
      const category = (example.category || '').trim() || '其他';
      if (!grouped.has(category)) {
        grouped.set(category, []);
      }
      grouped.get(category).push(example);
    }
    const result: ExampleGroup[] = [];
    for (const category of this.exampleCategoryOrder) {
      if (grouped.has(category)) {
        result.push({category, examples: grouped.get(category)});
        grouped.delete(category);
      }
    }
    for (const [category, items] of grouped) {
      result.push({category, examples: items});
    }
    return result;
  }

  private scrollToTop(): void {
    setTimeout(() => {
      if (this.contentScroller) {
        this.contentScroller.nativeElement.scrollTop = 0;
      }
    });
  }
}
