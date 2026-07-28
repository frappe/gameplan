# AFK Execution Runbook

How to drive this PRD autonomously: **one phase at a time**, each implemented by one subagent and checked by a second, independent subagent, then committed. Read this alongside `./PLAN.md`, `./DECISIONS.md`, and `./CODE_STYLE.md` before any autonomous run.

---

## Roles per phase

1. **Implementer** — reads the phase file plus the reference docs, makes the code changes, writes the phase's required Cypress spec(s), runs a quick self-check, and records any divergence from the plan (see "Recording new realities").
2. **Verifier** — a *separate* subagent with *fresh* context (must not be the implementer). Re-reads the phase's "Verify before commit" + "Cypress coverage" sections against the actual diff and the running app, runs the gates, and returns **PASS** or a concrete list of failures.
3. **Commit** — only on PASS. Use the phase's suggested commit message. 1–3 commits per phase. **Never push.**

If the verifier returns failures, hand them back to the implementer and re-verify. Bound this to ~3 rounds. If still failing, stop, set the phase `Status: blocked`, and surface the blocker. **Do not commit a failing phase.**

---

## Bootstrap (every subagent, every phase)

Read in order: `PLAN.md` → `DECISIONS.md` → `CODE_STYLE.md` → the specific `phase-NN-*.md`. The phase files are deltas on top of the shared decisions; they are **not** self-contained.

---

## Gates (what the verifier actually runs)

- **Static:** the grep checks in the phase's "Verify before commit" (e.g. the route-param audit grep). No stale `activeCategory` / `categorySpaces` / `router.js` references where the phase forbids them.
- **Build (compile gate):** `cd frontend && yarn build` must succeed. There is no separate typecheck/lint script (no `vue-tsc`/`eslint`), so the build is the only compile gate — treat a build failure as a hard fail.
- **Frontend behavior — Cypress (required every phase):** run the spec(s) named in the phase's "Cypress coverage" section, headless:
  - `cd frontend && yarn test` (full suite) or `npx cypress run --spec "cypress/e2e/<phase-spec>.cy.ts"` (single spec, faster during iteration).
  - Cypress targets `http://gameplan-demo.test:8000` (see `frontend/cypress.config.ts`). **That site must be running and built**, and is wiped by `POST /api/method/gameplan.ui_test_helpers.reset`. It is the disposable test site — never point Cypress at a site with real data.
  - Use the existing custom commands: `cy.login()`, `cy.scope('sidebar'|'dialog'|'header'|'body')`, `cy.button(text)`, `cy.combobox(placeholder)`. Mirror `cypress/e2e/onboarding.cy.js`.
- **Backend (Phase 08 and any backend change):** `bench --site gameplan.frappe.test run-tests --app gameplan` (or `--module <dotted.path>` for speed). For migrations, run `bench --site <test-site> migrate` **twice** and confirm the second run is a no-op (idempotency).

---

## Cypress spec rules

- "Simple, high-order" = one happy-path `it()` per behavior the phase introduces. Not exhaustive. Pattern: `cy.login()` → set up state (often `clear_data` + create via API/UI) → navigate → assert URL + a visible element.
- File naming: `cypress/e2e/community-<short>.cy.ts`. Keep specs independent (each logs in and seeds its own state).
- Phases 01–03 are already `done` but predate this requirement — add a catch-up spec `community-shell.cy.ts` (rail switcher, scoped discussions URL, global bookmarks) during Phase 04 or 09 so the early IA also has coverage.

---

## Known execution realities (updated as phases run)

From the **Phase 04 pilot**:
- **Cypress runs in-environment.** `gameplan-demo.test:8000` is up and Chrome is installed, so the verifier can and should run the phase spec headless (`yarn --cwd frontend cypress run --spec ...`). A green run is expected, not optional.
- **Seed joined membership in specs.** A freshly inserted `GP Team` does **not** auto-add its creator as a member, and `getActiveCommunity` (router guard + `communityState`) only sees *joined* communities. A spec that creates a community must also join it (e.g. `update_joined_teams`) or the scoped-route guard 404s. The rail switcher uses a custom `#trigger` slot with no `aria-haspopup="listbox"`, so open it via the `aria-label="More communities"` icon button, not `selectCombobox`.
From the **Phase 06 pilot**:
- **Build against the published frappe-ui, not the symlinked checkout.** Cypress hits the demo site, which serves the bundle produced by `yarn --cwd frontend build`. The `build` script does **not** unlink a local frappe-ui (only `dev` runs `unlink-frappe-ui.mjs`). If `node_modules/frappe-ui` is a symlink to `../../frappe-ui` (left over from a `dev:frappe-ui` session), the production bundle compiles against the local checkout and a reka-ui `TooltipRoot` context skew throws `Injection Symbol(TooltipRootContext) not found`, which silently drops buttons (e.g. the Discussions "Add new") to `<!--v-if-->`. Before building for Cypress, run `node frontend/scripts/unlink-frappe-ui.mjs` to restore the published package, then `yarn --cwd frontend build`. Check with `ls -la frontend/node_modules/frappe-ui` (should be a real dir, not a symlink).

- **Pre-existing red specs — do NOT attribute to your phase.** `onboarding.cy.js` and the space-detail specs (`discussion.cy.js`, `page.cy.js`, `task.cy.js`, `project.cy.js`, and draft-publish in `new-discussion.cy.ts`) fail at HEAD for reasons outside phases 04–07: (a) `gameplan.api.onboarding` creates a `GP Project` with no `team`, and (b) those specs visit `/g/space/<space>` for a community the test user never joined. **Phase 08 fixes both** (community-required onboarding that joins the creator + the auto-created public `General` space). Verifiers for phases 05–08 should run their **targeted** spec, not the full suite; Phase 09 runs the full suite and expects it green once Phase 08 has landed.

---

## Recording new realities (required)

Implementers **will** find the codebase differs from the plan — it already happened (the `team` `fetch_from` correction; the Phase 01–03 Notes). Do not silently diverge:

- **Product / strategy / decision change** (anything another phase relies on): update `DECISIONS.md`, and the affected phase files if the contract changed.
- **Implementation discovery** (a file moved, a helper already exists, an extra edit was needed): record it in that phase file's `Notes:` block — mirror the style used in phases 01–03.
- If a planned approach turned out wrong, correct the doc and state why in one line. The docs are the source of truth the next subagent reads.

---

## Status markers (parseable — keep current)

Each phase header uses:

- `Status: not started | in progress | blocked | done`
- `Commit checkpoint: <hash> — <message>` once committed.

A run resumes at the **first phase that is not `done`**. Set `in progress` when a phase starts; set `done` with the commit hash when it lands.

---

## AFK guardrails

- Branch is `feature/community`. Commit there; **never push** and never open a PR without explicit human approval (Phase 09 only *prepares* the PR description).
- Phase 08 mutates the database (migrations + `fetch_from` schema change). Run only against the disposable test site, and run each patch twice to prove idempotency before committing.
- Respect every phase's "Guardrails" section — especially "do not community-scope global pages" and "do not delete legacy Team/Project files."
- Phases are sequential; do not start phase N+1 until N is `done`. Phase 07 is the only loosely-coupled one (depends on 01–02, uses Phase 04 naming) and may run any time after 04.
