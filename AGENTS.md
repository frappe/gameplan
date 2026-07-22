# Gameplan

Async-first discussions tool for remote teams. Frappe (Python) backend + Vue 3 / TypeScript SPA frontend.

## Architecture

- **Dual app**: Frappe app serving a Vue SPA at the `/g` route via `gameplan/www/g.py` (boot data) and `gameplan/api.py` (whitelisted endpoints). Real-time via Socket.IO.
- **Backend**: DocTypes in `gameplan/gameplan/doctype/`. MariaDB. Full-text search via SQLite FTS5 (`gameplan.search_sqlite.GameplanSearch`, wired in `hooks.py`).
- **Frontend**: `frontend/src/` — `components/` (shared), `pages/`, `data/` (fetching composables), `utils/`. Vue Router under `/g/`. No state libraries (use `ref`/`computed`).
- **frappe-ui**: local copy in `./frappe-ui/` (git submodule). TS types auto-generated from the doctype list in `frontend/vite.config.ts`.

## Product language vs. schema

UI/product language is **Community** and **Space**; the schema still uses old names. Use Community/Space in app/UI code; the doctype names stay as-is until a migration is planned.

- `GP Project` = **Space** (holds discussions, tasks, pages)
- `GP Team` = **Community** (groups spaces; "Category" in older UI)
- Other core doctypes: `GP Discussion`, `GP Comment`, `GP Page`, `GP Task`, `GP User Profile`

## Commands

Local site names vary by development environment (CI uses `gameplan.test`). `gameplan-demo.test` is reserved for destructive E2E tests.

- `yarn dev` — Vite frontend on :8080 (unlinks local frappe-ui, uses published package)
- `yarn dev:frappe-ui` — same, but symlinks `node_modules/frappe-ui` → `./frappe-ui/` for library work
- `yarn build` / `bench start` (from `frappe-bench/`) — build frontend / run backend
- Backend tests: `bench --site <site> run-tests --app gameplan` (or `--module <path>`, `--test <method>`).
- E2E: `cd frontend && yarn test` (Cypress, specs in `frontend/cypress/e2e/`). **Always run Cypress against the demo site `gameplan-demo.test`, never another local site** — specs call `gameplan.test_api.clear_data`, which deletes ALL Gameplan data on whichever site the request resolves to. Requires `enable_ui_tests: 1` in that site's `site_config.json`. Before running, confirm the local `frappe serve` actually resolves `gameplan-demo.test:8000` to the demo site (host aliasing can route it to the default/dev site and wipe real data).
- frappe-ui units: `cd frappe-ui && yarn test` (Vitest)
- Lint: `pre-commit run --all-files` (ruff for Python — tabs, double quotes, line 110; Prettier for frontend)
- Generate a browser session ID with `bench --site <site> browse --user <user> --sid`.

## Frontend conventions

- `<script setup lang="ts">` + Composition API. Small component → single file; large → folder with `index.ts`.
- Prefer `useTemplateRef` over `ref`/`querySelector` for DOM access.
- **Data fetching**: only frappe-ui's `useList` / `useDoc` / `useCall` — never `useFetch`. Examples in `frontend/src/data/`.
- Always prefer `/api/v2` endpoints over v1
- `useCall` defaults to `method: 'GET'` — always pass `method: 'POST'` explicitly for calls that mutate data (see Backend conventions below for why a GET mutation silently no-ops)
- **Styling / design / Tailwind**
  - Follow `./frappe-ui/skills/frappe-ui/SKILL.md` (components + semantic design tokens)
  - Gameplan rule: **gray shades only — never color shades, even for primary states.**
- @vueuse/core is available — prefer it over custom implementations.

## Backend conventions

- Prefer `frappe.qb.get_query()` over `frappe.db.get_all()` (pass `ignore_permissions=False` when checks are needed).
- Prefer `frappe.qb` for writing database patches as well.
- Permissions: `has_permission` hooks in `hooks.py` (e.g. `GP Page`); community/space membership gates access.
- Debugging: add `def execute():` to a file like `gameplan/debug.py`, run via `bench --site gameplan-demo.test execute gameplan.debug.execute`.
- Mutating `@frappe.whitelist()` endpoints must set `methods=["POST"]` (or another unsafe method) explicitly. Frappe rolls back the DB transaction at the end of any GET request (`frappe/app.py::sync_database`) regardless of what the function did — a mutation left reachable via GET runs, calls `save()` with no error, then gets silently discarded.
- Prefer a doctype-scoped instance method (e.g. `GPUserProfile.set_image`, called via `useDoc({ methods })` → `POST /api/v2/document/<doctype>/<name>/method/<method>`) over a generic function in `api.py` when the action targets one specific document. Keep any admin/business-logic gate (e.g. `require_admin()`) inside the method itself — the doctype's own `has_permission` alone may be more permissive (e.g. letting a user write their own doc) than the action should allow.

## Feature Verification

When building a feature with UI, always verify it in browser. Use the in-app browser if available, otherwise use Chrome Devtools MCP. Create a test user (or users) for yourself on the local site you are testing. Environment-specific browser routing and authentication instructions belong in the development machine's global `AGENTS.md`, not this repository file.

- When a PR needs visual evidence, upload before/after screenshots as GitHub attachments in the PR description. Never add screenshot files to the repository.

## Code comments

Explain _why_, not _what_. JSDoc/TSDoc for complex functions/composables. No comments for self-explanatory code.

## Codebase health

- When editing code, always find opportunities to refactor code and leave it better than it was before
- Prefer generic components and utilities if code is repeated in multiple areas
- Prefer simpler code over complex
- When working on a specific component in Gameplan, if some generic part could be extracted out which can benefit other Frappe apps via frappe-ui, suggest it.

## Fixing bugs in dependencies

If a bug is actually in `frappe` or `frappe-ui`, fix it upstream (PR against `frappe/frappe` or `frappe/frappe-ui`) instead of working around it in Gameplan.

- No local hacks (dropping a field, reimplementing framework logic, monkey-patching) to dodge a dependency bug — that just hides it from every other app using the same dependency.
- A temporary local workaround is fine only if Gameplan is blocked and the upstream fix won't land in time — reference the upstream PR in a comment and remove the workaround once it ships.
