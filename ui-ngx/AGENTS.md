# AGENTS.md

ThingsBoard CE frontend (`ui-ngx`). Angular SPA served by the ThingsBoard backend.

This branch (`feat/ztxk`) is a **private-deployment fork** branded as
**中国中铁物联网平台** (China Railway IoT Platform). See
[Fork customizations](#fork-customizations-private-deployment) before making changes.

## Stack

- Angular 20.3 / Angular Material 20 / CDK 20
- TypeScript 5.9, RxJS 7.8, NgRx 20
- Style: SCSS + Tailwind CSS; component selector prefix `tb`

## Package manager (IMPORTANT)

Use **Yarn 1.22.22** and Node **v22.22.2**. Do **not** use `npm install` — it fails with
`ERESOLVE` because `ngx-hm-carousel@19` declares `@angular/common@^19` while the project is on
Angular 20. The `resolutions` field in `package.json` is Yarn-only and is ignored by npm.

```bash
yarn install
```

`prepare` runs `patch-package`, so `node_modules` gets patched local dependency files.

## Commands

| Command | Purpose |
|---------|---------|
| `yarn install` | Install dependencies (Yarn 1.x required) |
| `yarn start` | Dev server on `http://localhost:4200` (proxies to backend on `:18080`) |
| `yarn build` | Development build |
| `yarn build:prod` | Production build (`--max_old_space_size=4096`) |
| `yarn lint` | ESLint (`ng lint`) |
| `yarn build:types` | Regenerate TypeScript types (`generate-types.js`) |
| `yarn build:icon-metadata` | Regenerate icon metadata |

## Running locally

The dev server proxies API calls to a running ThingsBoard backend:

- `proxy.conf.js` forwards `http://localhost:4200` → `http://localhost:18080`
  (`ws://localhost:18080` for WebSockets). This targets the local Docker backend; set
  `forwardUrl` / `wsForwardUrl` back to `http://localhost:8080` to use a backend on the default port.
- Start the backend first (see root `pom.xml` / `application` module), then `yarn start`.

## Fork customizations (private deployment)

Key divergences from upstream. Do not "restore" these when merging upstream changes.

### Branding & theme

- Logos (brand blue `#195DA2`): `src/assets/crecg_logo_title_blue.svg` (full wordmark) and
  `src/assets/crecg_logo_blue.svg` (square icon).
  - Referenced in `shared/components/logo.component.ts` (login default),
    `modules/home/home.component.ts` (`logo` / `collapsedLogo`) and
    `modules/home/components/dashboard-page/dashboard-page.component.ts`
    (`defaultDashboardLogo`).
- Login page (`modules/login/pages/login/login.component.{html,scss}`):
  - Full-screen background `assets/login-background.png` with a dark overlay; light card.
  - All accents use `#195DA2` (submit/text/outlined buttons, input focus, icons, progress bar,
    divider, titles).
  - Visible title uses i18n key `login.login-title`.
- Browser tab:
  - Favicon: `index.html` points to `assets/crecg_logo_blue.svg`.
  - Static title in `index.html` and runtime title from `env.appTitle` = `中国中铁物联网平台`
    (`src/environments/environment.ts`, `environment.prod.ts`). `title.service.ts` renders
    `` `${env.appTitle} | ${pageTitle}` ``.

### Removed / neutralized external links

- `shared/models/constants.ts`: `helpBaseUrl = ''`.
- `shared/components/help.component.html` is intentionally empty, so every `[tb-help]` "?" button
  renders nothing. Keep `HelpComponent` declared (templates still bind `[tb-help]`).
- Login logo link and dashboard "Powered by" link were de-linked.
- Deleted the GitHub badge component/module and `core/http/git-hub.service.ts` (usages removed from
  home toolbar, dashboard toolbar and widget editor).
- Hardcoded `thingsboard.io` / Flutter / Microsoft links were stripped from the device-connectivity
  dialog, IoT Hub dialogs, mobile app configuration dialog, notification recipient dialog,
  home-page widgets (`doc-links`, `getting-started`, `version-info`) and locale help hints.

### Hidden features and routes

- Hidden by removing the menu reference **and** unhooking the lazy module; the feature code is kept.
- Mobile center: `mobile_center` removed from `menu.models.ts`, `MobileModule` removed from
  `modules/home/pages/home-pages.module.ts`.
- IoT Hub: `iot_hub` menu entry removed, `IotHubModule` removed from `home-pages.module.ts`, and the
  tenant-home IoT Hub banner widget removed. The `IotHubActionsService` "add from IoT Hub" table
  actions and all `iot-hub` code remain (unhooked).

### Home dashboards

- `src/assets/dashboard/{sys_admin,tenant_admin,customer_user}_home_page.json` are customized:
  removed Documentation / Version / Connect mobile app (+ Getting started), the SYS_ADMIN
  "Functions" card and the TENANT_ADMIN IoT Hub banner; default layouts were rebalanced into a
  two-column grid; `mobileHide` flags preserved.
- To remove a widget: delete its entry in `configuration.widgets`, its entry in
  `configuration.states.<state>.layouts.main.widgets`, and any now-orphaned `state`.

### i18n

- `src/assets/locale/locale.constant-zh_CN.json` is fully in sync with `en_US` (no missing keys).
  Any new `en_US` key **must** get a `zh_CN` translation too.
- External links inside locale help hints were removed (kept the surrounding text).

### Git / IDE

- `.vscode/` is ignored in both the root `.gitignore` and `ui-ngx/.gitignore`.
- Work happens on branch `feat/ztxk`.

### Deployment note

- Changes to `environment.*` (`appTitle`), `index.html` or SCSS require restarting `yarn start`
  (env values are inlined at build time) followed by a hard refresh.
- Deployments served by the backend/Docker need `yarn build:prod` and a redeploy; do not hand-edit
  build artifacts under `ui-ngx/target/**`.

## Architecture

Detailed route-to-source mapping, entity table/resolver catalog, shared component catalog,
Angular Material DOM patterns, form structure, and HTTP service reference live in
`structure.md` — read it before navigating the codebase.

Path aliases (`tsconfig.json`):

| Alias | Maps to |
|-------|---------|
| `@app/*` | `src/app/*` |
| `@core/*` | `src/app/core/*` |
| `@modules/*` | `src/app/modules/*` |
| `@home/*` | `src/app/modules/home/*` |
| `@shared/*` | `src/app/shared/*` |
| `@env/*` | `src/environments/*` |

Key directories:

```
src/app/
├── core/
│   ├── http/         # HTTP services (one per entity type)
│   └── services/     # Menu, auth, utils
├── modules/
│   ├── home/
│   │   ├── components/   # entity table/details, alarm, dashboard, etc.
│   │   └── pages/        # Page modules (one dir per feature)
│   └── login/
└── shared/
    ├── components/   # shared UI components
    └── models/       # interfaces / enums
```

Most pages follow a per-entity 3-file pattern: `<entity>-table-config.resolver.ts`,
`<entity>.component.ts` (extends `EntityComponent<T>`), `<entity>-tabs.component.ts`.

## Code conventions

- Indentation: 2 spaces, UTF-8, final newline (`.editorconfig`); JSON uses 4 spaces.
- Do not add comments unless asked.
- Standalone Angular components; selector prefix must be `tb`.
- Prefer existing shared components/services over ad-hoc implementations.
- Entity detail forms extend `EntityComponent<T>` and implement `buildForm` /
  `updateForm` / `updateFormState`; save merges `{ ...entity, ...entityFormValue() }`.
- No `data-testid` attributes; select via Material structure, `formControlName`, labels,
  roles, and `matColumnDef`.

## Verification

There is no test suite to run (only `src/app/core/auth/auth.service.spec.ts`; no karma/jest
config). Verify changes by:

```bash
yarn lint
yarn build:prod
```
