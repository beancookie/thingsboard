# AGENTS.md

ThingsBoard CE frontend (`ui-ngx`). Angular SPA served by the ThingsBoard backend.

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
| `yarn start` | Dev server on `http://localhost:4200` (proxies to backend on `:8080`) |
| `yarn build` | Development build |
| `yarn build:prod` | Production build (`--max_old_space_size=4096`) |
| `yarn lint` | ESLint (`ng lint`) |
| `yarn build:types` | Regenerate TypeScript types (`generate-types.js`) |
| `yarn build:icon-metadata` | Regenerate icon metadata |

## Running locally

The dev server proxies API calls to a running ThingsBoard backend:

- `proxy.conf.js` forwards `http://localhost:4200` → `http://localhost:8080`
  (`ws://localhost:8080` for WebSockets).
- Start the backend first (see root `pom.xml` / `application` module), then `yarn start`.

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
