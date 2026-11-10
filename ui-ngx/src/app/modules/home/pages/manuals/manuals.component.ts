// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { Component, DestroyRef, ElementRef, OnInit, ViewChild, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MatDrawer } from '@angular/material/sidenav';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MediaBreakpoints } from '@shared/models/constants';
import { ApiDocLink, ExampleEntry, ManualEntry } from './manual.models';
import { ManualsService } from './manuals.service';

@Component({
  selector: 'tb-manuals',
  templateUrl: './manuals.component.html',
  styleUrls: ['./manuals.component.scss'],
  standalone: false
})
export class ManualsComponent implements OnInit {

  @ViewChild('drawer') drawer: MatDrawer;
  @ViewChild('contentScroller') contentScroller: ElementRef<HTMLElement>;

  manuals: ManualEntry[] = [];
  filteredManuals: ManualEntry[] = [];
  examples: ExampleEntry[] = [];
  apiDocs: ApiDocLink[] = [
    {
      labelKey: 'manual.api-docs-thingsboard',
      icon: 'api',
      url: 'https://thingsboard.zhgcloud.com/swagger-ui/index.html'
    },
    {
      labelKey: 'manual.api-docs-thing-model',
      icon: 'schema',
      url: 'https://thingsboard.zhgcloud.com/thing-model/swagger-ui/index.html'
    }
  ];
  selectedPath: string | null = null;
  selectedTitle = '';
  markdown: string | null = null;
  searchText = '';
  indexLoading = true;
  contentLoading = false;
  error: string | null = null;
  drawerMode: 'side' | 'over' = 'side';
  drawerOpen = true;

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
      const doc = params.get('doc');
      if (doc) {
        this.loadDoc(doc);
      }
    });

    this.loadIndex();
    this.loadExampleRoutes();
  }

  loadIndex(): void {
    this.indexLoading = true;
    this.error = null;
    this.manualsService.getIndex().pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (manuals) => {
        this.manuals = manuals;
        this.applyFilter();
        this.indexLoading = false;
        if (this.selectedPath) {
          const selected = this.manuals.find((manual) => manual.path === this.selectedPath);
          if (selected) {
            this.selectedTitle = selected.title;
          }
        } else if (manuals.length && !this.route.snapshot.queryParamMap.get('doc')) {
          this.router.navigate([], {
            relativeTo: this.route,
            queryParams: {doc: manuals[0].path},
            replaceUrl: true
          });
        }
      },
      error: () => {
        this.indexLoading = false;
        this.error = 'manual.load-failed';
      }
    });
  }

  loadExampleRoutes(): void {
    this.manualsService.getExamples().pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (examples) => {
        this.examples = examples;
      },
      error: () => {
        this.examples = [];
      }
    });
  }

  loadDoc(path: string): void {
    const normalizedPath = path.trim();
    if (!normalizedPath || (normalizedPath === this.selectedPath && this.markdown)) {
      return;
    }
    if (normalizedPath === 'manuals/README.md') {
      this.selectedPath = null;
      this.selectedTitle = '';
      this.markdown = null;
      this.contentLoading = false;
      this.error = null;
      if (this.route.snapshot.queryParamMap.get('doc')) {
        this.router.navigate([], {
          relativeTo: this.route,
          queryParams: {},
          replaceUrl: true
        });
      }
      return;
    }
    this.selectedPath = normalizedPath;
    const selected = this.manuals.find((manual) => manual.path === normalizedPath);
    this.selectedTitle = selected ? selected.title : this.titleFromPath(normalizedPath);
    this.contentLoading = true;
    this.error = null;
    this.markdown = null;
    this.manualsService.getContent(normalizedPath).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (content) => {
        this.markdown = this.manualsService.preprocessMarkdown(content, normalizedPath);
        this.contentLoading = false;
        this.scrollToTop();
      },
      error: () => {
        this.manualsService.clearContent(normalizedPath);
        this.contentLoading = false;
        this.error = 'manual.not-found';
      }
    });
  }

  onSearch(value: string): void {
    this.searchText = value;
    this.applyFilter();
  }

  selectManual(manual: ManualEntry): void {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {doc: manual.path}
    });
    if (this.drawerMode === 'over') {
      this.drawer.close();
    }
  }

  toggleDrawer(): void {
    this.drawer.toggle();
  }

  retry(): void {
    if (!this.manuals.length) {
      this.loadIndex();
    } else if (this.selectedPath) {
      this.manualsService.clearContent(this.selectedPath);
      this.markdown = null;
      this.loadDoc(this.selectedPath);
    }
  }

  assetUrl(path: string): string {
    return this.manualsService.assetUrl(path);
  }

  onMarkdownClick(event: MouseEvent): void {
    if (event.defaultPrevented || event.button !== 0 || !this.selectedPath) {
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
    const resolved = this.manualsService.resolveDocLink(this.selectedPath, href);
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
        this.router.navigate([], {
          relativeTo: this.route,
          queryParams: {doc: resolved.path}
        });
      }
    } else {
      window.open(this.manualsService.assetUrl(resolved.path), '_blank', 'noopener');
    }
  }

  private applyFilter(): void {
    const search = this.searchText.trim().toLowerCase();
    if (!search) {
      this.filteredManuals = this.manuals;
    } else {
      this.filteredManuals = this.manuals.filter((manual) =>
        manual.title.toLowerCase().includes(search) || manual.path.toLowerCase().includes(search)
      );
    }
  }

  private titleFromPath(path: string): string {
    const fileName = path.split('/').pop() || path;
    return fileName.endsWith('.md') ? fileName.substring(0, fileName.length - 3) : fileName;
  }

  private scrollToTop(): void {
    setTimeout(() => {
      if (this.contentScroller) {
        this.contentScroller.nativeElement.scrollTop = 0;
      }
    });
  }
}
