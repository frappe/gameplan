# Gameplan

Async-first discussions tool for remote teams. Frappe (Python) backend + Vue 3 /
TypeScript SPA served at `/g`.

Backend in `gameplan/`, frontend in `frontend/src/` (`components/`, `pages/`,
`data/` for fetching composables, `utils/`).

**The code is the source of truth for conventions.** It is consistent — find the
nearest precedent and copy it. This file covers only what the code cannot tell you.
Where a trap or policy below contradicts the precedent you found, this file wins.

## Naming: product vs schema

New code, UI copy and commit messages say **Space** and **Community**. The schema
still carries the old names. Do not rename the doctypes.

- `GP Project` = Space
- `GP Team` = Community

## Where the non-obvious things live

- Boot data: `gameplan/www/g.py`. Whitelisted endpoints: `gameplan/api.py`, plus
  document methods on the doctype classes.
- Permissions: `gameplan/permissions.py` and the `has_permission` hooks in `hooks.py`.
- Full-text search: `gameplan/search_sqlite.py` (SQLite FTS5 in its own per-site
  file), registered once in `hooks.py`. Async index queue drained by cron.
- Patches sit next to their doctype in `gameplan/gameplan/doctype/<dt>/patches/`,
  registered in `gameplan/patches.txt`. App-level `gameplan/patches/` is for
  cross-doctype work only.

## Traps

- **The vendored `./frappe-ui/` is not the version that runs.** The submodule is on
  beta.28; `frontend/package.json` pins beta.51. `yarn dev:frappe-ui` symlinks the
  stale checkout. Read `frontend/node_modules/frappe-ui/` for current library
  source; use `./frappe-ui/` only when doing library work.
- **Cypress wipes the entire site**, not the records a spec created — `resetData`
  calls `gameplan.ui_test_helpers.reset`. Point it at a disposable site, nothing else.
- **Colour shades**: in Gameplan code use gray tokens. Amber survives in
  `ReactionsDesktop.vue`, `ReactionsMobile.vue` and the `DiscussionRow.vue` unread
  badge — the exception, not a licence to add more. frappe-ui's own components do
  ship colour (the Rail unread badge is `theme="red"`); that is the library's call
  and not a precedent for new Gameplan markup. Unread is drawn amber, red and gray
  in three different places, so match the rule here, not the nearest neighbour.
- **On a SQLite site, backend tests fail intermittently while a dev server is
  running** — both hold the same DB file. Symptom is dozens of
  `QueryDeadlockError: database is locked`, never an assertion failure. Stop the
  server or re-run; do not debug it as a real failure.

## Policy

- Fix a `frappe` or `frappe-ui` bug upstream, not with a Gameplan workaround. A local
  workaround needs a comment naming the upstream PR that removes it.
- Verify UI work in a browser before calling it done. Screenshots belong in the PR as
  GitHub attachments, never in the repo.

## Environment

Site names and ports vary per bench. Resolve them, do not assume.

- Sites: `ls sites/`. Use the one with `"allow_tests": true` in its `site_config.json`.
- Vite dev port is `8080 + (webserver_port - 8000)`, read from
  `sites/common_site_config.json`.
- Backend tests: `bench --site <site> run-tests --app gameplan` (also `--module`,
  `--test`).
- E2E: `cd frontend && yarn test`. Needs a dev server (`bench start`, or
  `DEV_SERVER=1 bench serve`) plus `allow_tests`, `enable_ui_tests: 1` and
  `developer_mode: 1` in `site_config.json`. `enable_ui_tests` is read through
  `cint`, so `"true"` counts as off.
- Lint: `pre-commit run --all-files` (ruff: tabs, double quotes, line 110).
- Debug: add `def execute():` to `gameplan/debug.py`, run
  `bench --site <site> execute gameplan.debug.execute`.
- Sign in as another user: `bench browse --site <site> --user <u> --sid` (needs
  `developer_mode`). In the app, `DevUserSwitcher.vue` shows in dev builds with
  `enable_dev_user_switcher: 1`.
