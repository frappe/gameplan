# Test Suite Rebuild — Plan and Status

Working plan for rebuilding Gameplan's test suite "the way it should have been
written on day 1." This document is the cross-session source of truth: read it
together with `TESTING.md` (architecture and conventions) before continuing the
work. Update the Status section as steps land.

Branch: `feat/test-foundation` (PRs target `develop`).

## Goal

One test map mirroring the product's feature catalog, at three layers:

1. **Backend (Frappe integration tests)** — owns business rules, permissions,
   edge cases, API contracts. The workhorse.
2. **Cypress E2E** — owns user journeys, one happy path per feature, UI /
   routing / mobile behavior. Never permission matrices or edge cases.
3. **Vitest** (not set up yet, thin) — pure frontend logic only.

## Working agreements (from Faris)

- Commit small, complete pieces often. Branch first; never commit on develop.
- If a test surfaces a real Gameplan bug: fix the bug. Never bend a test to
  pass. Product intent wins over current code.
- Stop for manual review after each numbered step below.
- No new module-level endpoints in `gameplan/api.py` — doc-scoped methods only;
  genuine framework gaps get fixed upstream in frappe.
- Features with UI get verified in a real browser before calling them done.

## Product decisions made during this work

- **Guest policy**: guests are participants in spaces they have access to —
  they can comment, react, edit their OWN content, delete their OWN content.
  They cannot touch others' content and get nothing outside granted spaces.
- **Permission tier model**: frappe `write` on content means "may interact"
  (react, comment, vote) — guests with space access hold write. Who may edit or
  delete whose content is business logic in the `content_has_permission` hook
  (`gameplan/permissions.py`): editors pass outright; interactors pass only if
  no protected fields are changing on the doc instance (interaction-safe
  allowlist per doctype, e.g. the reactions child table). The field diff must
  handle both hook contexts: clean-doc gate checks (v2 POST doc-method gate;
  `get_doc_before_save()` is unpopulated — fall back to DB-row diff) and
  dirty-doc save-time checks.
- Rejected along the way (do not resurrect): a generic `gameplan.api.react`
  endpoint; an upstream frappe `permission_type` change. Both were made
  unnecessary by the tier model above.
- Open: none currently.

## Step 1 — Foundation (DONE, verified)

- `gameplan/tests/base.py` — `GameplanTestCase` with persona cast (`admin`,
  `member`, `second_member`, `guest`, `outsider`), `as_user()`,
  `assert_allowed` / `assert_not_allowed`.
- `gameplan/tests/fixtures.py` — product-language builders
  (`create_community`, `create_space`, `create_discussion`, ...).
- `gameplan/tests/{features,permissions,platform}/` package skeleton.
- `gameplan/tests/permissions/test_permission_matrix.py` — table-driven
  executable spec: actor × (read, write, delete) per space kind.
- `gameplan/ui_test_helpers.py` — Cypress seed API: `reset(scenario)` wipes all
  Gameplan data AND users, reseeds personas (password `admin`), builds named
  scenarios (`onboarded`, `space_with_discussion`, `private_space_with_guest`,
  `two_communities`), returns created ids.
- `frontend/cypress/support/personas.ts` (`cy.loginAs`) and `seed.ts`
  (`resetData(scenario)`).
- `TESTING.md`.

## Interlude — Guest participation spec (DONE except browser verification)

Implementing the guest policy + tier model above. Sequence (an agent is
executing this; check `git log feat/test-foundation` for how far it got):

1. Remove `gameplan.api.react` endpoint; restore doc-method URL in
   `frontend/src/data/reactions.ts`; abandon any `apps/frappe` branch.
2. Tier model in `content_has_permission` write branch + protected-fields diff.
3. Matrix: guest write rows on granted-space content flip to True (write =
   interact, clean-doc semantics); edit-blocking asserted via real save
   attempts in `gameplan/tests/features/test_guest_participation.py`.
4. Guests can delete own content: `can_delete_content` owner-exception, delete
   DocPerm for Gameplan Guest on GP Comment (+ `bench migrate`), frontend
   `canDeleteContent` mirror, characterization test flipped to real assertion.
5. Frontend gates (kept from earlier rounds): `canEditContent` util mirrors
   backend; edit affordances on Comment/DiscussionView gated; Pin / Close /
   Re-open / Move hidden for guests (same gate as Edit).
6. Full regression: `bench --site gameplan-demo.test run-tests --app gameplan`,
   pre-commit, `cd frontend && yarn build`.
7. Browser verification as a guest (seed `private_space_with_guest`, log in as
   `guest@example.com`): react, comment, edit own, delete own, no edit/lifecycle
   affordances on others' content.

Status 2026-07-24: items 1-7 complete and verified — full backend suite green
(191 tests, exit 0), frontend build green. Browser verification complete: as a
guest, all 7 UI checks passed — sees the community and only the granted "Secret
Plans" space (not "General"), opens the discussion, reacts (persists on reload),
comments, edits and deletes own comment, and has NO Edit / Pin / Close / Move on
the member's post; member sanity login navigates normally and keeps every
lifecycle action. No console errors. No caveats.

Known real bugs already fixed on the branch: `can_edit_content` denied guests
unconditionally (now owner-exception); guests saw Edit on everyone's comments.
Guest had zero SPA navigation — `team_access_criterion` returned no communities
(`Team.name == ""`), so a guest's GP Team list was empty and every community/
space/discussion route 404'd ("No communities available"); `can_view_community`
also blocked the team-read path. Fixed: guests now get the communities of their
granted spaces (list + read), and the frontend shell treats a guest as joined to
every community it fetches.

## Step 2 — Migrate existing tests into the new structure (COMPLETE)

No behavior changes; green before and after. Mechanical, good for parallel
agents.

Backend (~120 tests move; absorb the 10 real per-doctype files, delete 13 empty
stubs):

| Existing | Destination |
|---|---|
| `tests/test_permissions_backend.py` | fold into `permissions/test_permission_matrix.py` (extend matrix world: pages/tasks doctypes, community-admin actor) + `permissions/test_guest_access.py` + management flows into `features/test_communities.py` / `test_spaces.py` |
| `tests/test_email_digest.py` | `features/test_email_digest.py` |
| `tests/test_attachments.py` | `platform/test_attachments.py` |
| `tests/test_html_utils.py` | `platform/test_html_utils.py` |
| `tests/test_community_migrations.py` | `platform/test_migrations.py` |
| `tests/test_bulk_updates.py` | split: notifications parts → `features/test_notifications.py`, move_to_team → `features/test_communities.py` |
| `tests/test_api_security.py` | `features/test_members.py` (invite/role/disable guards) |
| `tests/test_search_sqlite_ranking.py` | `features/test_search.py` |
| doctype `test_gp_unread_record.py` | `features/test_unread.py` |
| doctype `test_gp_user_profile.py` | `features/test_profiles.py` |
| doctype `test_gp_team.py` | `features/test_communities.py` |
| doctype `test_gp_discussion.py` | `features/test_discussions.py` |
| doctype `test_gp_draft.py` | `features/test_drafts.py` |
| doctype `test_gp_project.py` | `features/test_spaces.py` |
| doctype `test_gp_page.py` / `test_gp_comment.py` / `test_gp_task.py` | permissions → matrix; rest → respective feature files |
| doctype `test_gp_notification.py` | `features/test_notifications.py` |
| `tests/utils.py` | delete after flipping imports to `fixtures.py` |

E2E: convert 6 legacy `.cy.js` to `.ts` (split monolithic `it()`s); re-home all
21 specs into feature folders (`shell/` absorbs the community-shell /
community-smoke / community-naming overlap); move specs onto
`resetData()` / `cy.loginAs()`; extract duplicated helpers (rail switcher,
user normalization — the latter dies with the new seed API); then delete
`gameplan/test_api.py`.

Status 2026-07-24: complete and verified. Backend files are re-homed into
`features/` and `platform/`, the per-doctype and stub files are gone, and
`tests/utils.py` is replaced by `fixtures.py`. All 21 Cypress specs are
TypeScript, live in feature folders, and seed through `resetData(scenario)` /
`cy.loginAs(persona)` — so `gameplan/test_api.py` is deleted and
`gameplan/ui_test_helpers.py` is the only seed surface (5 scenarios).

Verification: backend suite green — 177 tests across the three batches
(16 + 106 + 55), exit 0. Cypress green — 52 tests across 21 specs, all passing.
`pre-commit run --all-files` clean.

Real product bugs the migration surfaced, all fixed on the branch (the old
specs hid them by running as Administrator or by asserting on the wrong
request):

- Task Status and Priority were never saved on desktop. The options carry an
  `onClick` for the mobile `Dropdown`, but frappe-ui's `Select` ignores it, so
  the desktop control changed the label and wrote nothing.
- Picking a task assignee saved twice. The combobox emits `null` while its
  search text is cleared, which unassigned the task (and logged an activity)
  before the real choice landed.
- Moving a discussion left the URL and sidebar on the old space. The redirect
  omitted the slug, which pushed the router off its local fast path onto a
  server lookup it caches for a second — answering with the pre-move copy and
  bouncing the URL straight back.
- Live timeline updates never reached ordinary users. `log_activity` published
  `new_activity` with no room, which falls back to the site room that only Desk
  (System User) sockets join; Gameplan members are Website Users. It now
  publishes into the document's room and the comment components subscribe to it.

## Step 3 — Fill coverage gaps (NOT STARTED)

Each area lands as a vertical slice: backend feature file + one E2E happy path.
Priority order:

1. Invitations (`features/test_invitations.py` — create/accept/expire, role
   assignment, `accept_invitation` endpoint; security-sensitive, currently an
   empty stub).
2. Polls (vote/retract/stop/one-vote guard + E2E create-vote-stop).
3. Notifications (mention/reply → GP Notification; badge; mark-all-read; E2E).
4. Reactions + bookmarks E2E (backend already covered by guest work).
5. Guest access E2E (invite guest, guest's scoped read-only-plus-participation
   view).
6. Discussion lifecycle backend (pin/close/comment-count/last_post side
   effects).
7. Pages (edit content, private vs space visibility + E2E).
8. Profile/settings (bento cards, custom emoji, quick reactions + E2E).
9. Search page E2E (filters; index hooks backend).
10. Space membership E2E (join/leave/follow, mark-space-read).
11. Mobile variants: create discussion + comment on iphone-6 viewport.
12. Remaining `api.py` endpoint tests (`onboarding`, `unread_notifications`,
    `can_access_gameplan`, `get_search_filter_options`).

## Step 4 — CI guardrails (NOT STARTED)

- Coverage report on backend runs (visible, not a gate).
- Nightly no-retry Cypress lane to surface flakes (PR lane keeps retries=2).
- Shard `ui-test.yml` by top-level spec folder once suite grows (~30 specs).
- Optional: minimal Vitest setup if Step 3 surfaces awkward-to-E2E pure logic.

## Environment notes (local)

- Tests run ONLY on site `gameplan-demo.test` (disposable; `enable_ui_tests`).
  Never `gameplan.frappe.test`.
- Backend tests need the bench Redis daemons (ports 13000/11000) running.
- 2026-07-24: removed stale `gameplan-settings-exploration` line from bench
  `sites/apps.txt` (fork of gameplan; its module name could never import and it
  broke `frappe.init` for all test runs). The fork stays in `apps/` on disk.
