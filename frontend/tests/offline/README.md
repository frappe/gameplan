# Offline mode Playwright suite

End-to-end coverage for Gameplan's offline support (service worker + shell/data caching,
`gameplan/www/gameplan-sw.js` and `frontend/src/offline.ts`). Plain CommonJS Playwright
scripts, not `@playwright/test` — each story is a `run()` function that returns a
`{ pass, checks: [...] }` result and can also be executed directly with `node`.

Originally built as a throwaway harness at `/tmp/offline-mvp/pw`; migrated here so it
survives reboots and can gate regressions in CI/local dev.

## What's covered (12 stories)

| Story | Covers                                                                                                       |
| ----- | ------------------------------------------------------------------------------------------------------------ |
| US1   | App shell loads offline (reload + deep link) instead of a browser error page                                 |
| US2   | Previously-viewed feed / space / discussion render from cache while offline                                  |
| US3   | Offline indicator appears when connectivity drops, clears on reconnect                                       |
| US4   | A comment typed while offline fails gracefully and isn't lost                                                |
| US5   | Fresh data appears automatically on reconnect, no manual reload                                              |
| US6   | Never-cached content shows an honest "can't load this offline" fallback                                      |
| P1    | Background prefetch (`data/offlinePrefetch.ts`) makes an unvisited member's profile offline-ready            |
| P2    | A profile visited fully online (incl. Posts tab) is available offline                                        |
| P3    | A profile opened right as the browser goes offline (before prefetch runs) degrades honestly                  |
| US7a  | Plain logout clears shell/runtime caches and IndexedDB, but preserves the current user's draft               |
| US7b  | A second user logging in on the same browser (no explicit logout) never sees the first user's cached data    |
| US8   | A new service worker build shows an update toast; clicking Refresh reloads exactly once onto the new version |

## Prerequisites

1. **A production build.** From the repo root: `yarn build`. The suite talks to a real
   service worker, which Vite's dev server doesn't register the same way — always test
   against the built bundle.
2. **A Frappe server serving that build**, e.g.:
   ```
   bench --site <your-site> serve --port 8003
   ```
   (any port works; point `GAMEPLAN_OFFLINE_BASE_URL` at it — see Configuration below).
3. **A seeded test user and content**, on that site:
   - A user with a password (`GAMEPLAN_OFFLINE_USER` / `GAMEPLAN_OFFLINE_PASSWORD`),
     member of at least one `GP Team` (Community) with a non-private `GP Project`
     (Space) that has a `GP Discussion` with a few comments.
   - A **second** user (`GAMEPLAN_OFFLINE_USER2` / `GAMEPLAN_OFFLINE_PASSWORD2`),
     member of the same team — used by US7b to simulate a second person on a shared
     computer. Follow the pattern in `gameplan/debug.py` (per `AGENTS.md`'s debugging
     convention: add an `execute()` function there and run it with
     `bench --site <your-site> execute gameplan.debug.execute`) to create the user,
     set its password, and add it to the team.
   - A few enabled `GP User Profile` members for the People/profile stories (P1-P3) —
     any real members on the site work; override their IDs via env vars if needed (see
     below).

## Running

```
cd frontend
yarn install
yarn test:offline
```

Runs all 12 stories against `GAMEPLAN_OFFLINE_BASE_URL` (default
`http://gameplan.localhost:8003`), writes a summary to `tests/offline/results/summary.json`
and per-story JSON/screenshots under `tests/offline/results/` (gitignored). Exits non-zero
if any story fails.

Run a single story directly: `node tests/offline/us3.js`.

Online regression smokes (confirm normal online usage isn't broken — not part of the 12
offline stories): `yarn test:offline:smoke`.

## Configuration

All seeded-content coupling lives in `config.js`, overridable via env vars:

| Env var                                                                                                                            | Default                                              | Meaning                                                       |
| ---------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------- |
| `GAMEPLAN_OFFLINE_BASE_URL`                                                                                                        | `http://gameplan.localhost:8003`                     | Origin serving the production build                           |
| `GAMEPLAN_OFFLINE_USER` / `GAMEPLAN_OFFLINE_PASSWORD`                                                                              | `offline-tester@example.com` / `offline-test-1234`   | Primary test account                                          |
| `GAMEPLAN_OFFLINE_USER2` / `GAMEPLAN_OFFLINE_PASSWORD2`                                                                            | `offline-tester-2@example.com` / `offline-test-1234` | Second account (US7b)                                         |
| `GAMEPLAN_OFFLINE_COMMUNITY`                                                                                                       | `common-room`                                        | `GP Team` name both accounts belong to                        |
| `GAMEPLAN_OFFLINE_SPACE_ID`                                                                                                        | `3`                                                  | `GP Project` name for the visited/cached space                |
| `GAMEPLAN_OFFLINE_DISCUSSION_ID`                                                                                                   | `55`                                                 | `GP Discussion` name for the visited/cached discussion        |
| `GAMEPLAN_OFFLINE_UNCACHED_SPACE_ID` / `GAMEPLAN_OFFLINE_UNCACHED_DISCUSSION_SPACE_ID` / `GAMEPLAN_OFFLINE_UNCACHED_DISCUSSION_ID` | `4` / `5` / `54`                                     | Content never visited by any story before going offline (US6) |
| `GAMEPLAN_OFFLINE_PERSON_PREFETCH` / `GAMEPLAN_OFFLINE_PERSON_VISITED` / `GAMEPLAN_OFFLINE_PERSON_NO_PREFETCH`                     | `priya-sharma` / `maya-iyer` / `hana-suzuki`         | `GP User Profile` IDs for P1/P2/P3                            |
| `GAMEPLAN_OFFLINE_RESULTS_DIR`                                                                                                     | `tests/offline/results`                              | Where JSON results + screenshots are written                  |

`us8.js` additionally rebuilds the app in place (bumps `gameplan-sw.js`'s
`CACHE_VERSION`, runs `yarn build`, then reverts and rebuilds again in a `finally`) — it
resolves the gameplan app root from its own file location, not an env var.
