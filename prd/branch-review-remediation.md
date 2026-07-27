# Branch review remediation — `feat/test-foundation`

Work list from an adversarial review of this branch. Written as a handoff: a fresh
session can pick this up with no other context.

**Review base:** `upstream/develop`, merge-base `8658e4a0`. Not `main` — PRs from this
repo target `develop`, and diffing against `main` buries the change under 800+
unrelated upstream commits.

**Scope decision:** all of this goes in the **same PR**. The branch is already large and
these fixes all come from the same review; splitting adds overhead for no benefit.

---

## 1. Current state — verify before starting

The site needs migrating first. This branch adds a `poll` column to `GP Notification`;
without it 26 notification tests error with `Unknown column 'poll'`.

```bash
bench --site gameplan-demo.test migrate
bench --site gameplan-demo.test run-tests --app gameplan   # do NOT pipe to tail
```

Expected today: **exit 1**. 505 tests run, 504 pass, 1 fails.

Two things to know about that command:

- It prints **three** separate unittest summaries (26 + 355 + 124 = 505). Piping to
  `tail` hides the earlier batches *and* replaces the exit code with `tail`'s. Always
  read the whole output and check `$?`.
- `TEST_SUITE_PLAN.md:603` claims "505 tests, exit 0". That claim is currently false and
  should be corrected once the suite is green again.

---

## 2. Blockers

### B1 — Deleting a discussion fails if it contains another member's poll

**Confirmed by reproduction.** Adding a `has_permission` hook for `GP Poll` puts
`can_delete_content` in front of the delete cascade, and the cascade runs without
`ignore_permissions`.

Exact chain:

```
delete_doc(GP Discussion) -> on_trash -> gameplan/mixins/on_delete.py:14
  -> delete_doc(GP Poll) -> check_permission_and_not_submitted -> PermissionError
```

A control discussion with no poll deletes fine, which isolates the cause to the poll
cascade.

Effect: a discussion owner can no longer delete their own thread once anyone else has
posted a poll in it. The whole delete rolls back.

Relevant files: `gameplan/gameplan/doctype/gp_poll/gp_poll.py:199`,
`gameplan/hooks.py:135`, `gameplan/mixins/on_delete.py:13-18`.

`gameplan/tests/features/test_polls.py:498` asserts the *direct* denial (a non-owner
cannot delete someone else's poll). That is correct and must keep passing. Nothing
covers the cascade.

**Fix:** prefer honouring the `from_gameplan_delete_cascade` flag that the branch
already threads through — exempt cascaded deletes inside `can_delete_content`. If that
flag turns out not to actually reach the check, fall back to passing
`ignore_permissions=True` in `on_delete.on_trash`'s cascade (the parent delete is
already authorised, and `GP Comment` already behaves this way). Say which route was
taken and why.

**Acceptance:** a regression test where member A owns the discussion, member B owns a
poll inside it, and A deletes the discussion successfully. `test_polls.py:498` still
passes.

### B2 — `test_reading_the_row_count_does_not_trip_the_guard` fails

`gameplan/tests/platform/test_search_isolation.py:138-156`.

**The production helper is correct.** Verified directly: `row_count()`'s
`sqlite3.connect("file:...?mode=ro&immutable=1")` creates neither `-wal` nor `-shm`
when they don't already exist. Do not change `gameplan/tests/search_isolation.py:113-130`.

**The test is wrong.** Its own setup writer (lines 144-149) opens the db, sets
`journal_mode = WAL`, writes, and closes. On Python 3.14 / SQLite 3.51 (macOS) that
close leaves `-wal` and `-shm` on disk. The test then asserts those files don't exist
and blames `row_count` for files that predate it.

Why CI is green: CI pins Python 3.14 but runs on Ubuntu, whose bundled SQLite is older
and cleans the WAL up on close. So this is red locally and green in CI.

**Fix:** make the test measure what it claims. Either checkpoint and delete the sidecars
after the setup writer closes and before calling `row_count`, or snapshot which sidecars
exist before the call and assert `row_count` added none. Keep the intent — the guard
must not leave residue in the site directory.

---

## 3. Decisions already made

These are settled. Do not relitigate them; implement as written.

| # | Question | Decision |
|---|---|---|
| 1 | Multi-answer poll percentages | Divide by **distinct voters**, not vote rows. Keep showing the percentage. Totals may exceed 100% — that is the standard for "select all that apply" (Google Forms, SurveyMonkey both do this). |
| 2 | Who may stop/edit a poll | **Owner only** (owner or admin, matching the existing `can_delete_content` rule), enforced **server-side**. Hiding the button is not enough. |
| 3 | Guests seeing the community member roster | **Leave as-is.** No work. |
| 4 | Community admin reading private spaces | They **should not** be able to. The code and the test matrix are already correct; the docstring above the matrix contradicts them and is what needs fixing. |
| 5 | Voting twice | **Changing your vote should be allowed.** Today a second vote returns success and is silently ignored. |
| 6 | "Leave space" on a private space | **Keep it everywhere, add a confirm dialog.** On a private space the dialog warns you will not be able to rejoin on your own. Also hide the control from guests. |
| 7 | Excluding the test helper from production | **Not possible via packaging** — see below. Harden at runtime instead. |
| 8 | PR split | **One PR.** |

### Note on decision 7

`env/lib/python3.14/site-packages/gameplan.pth` points straight at the repo directory.
Bench installs apps by cloning the git repo and putting that directory on `sys.path`, so
**every file in the repo is present on every production server**. `MANIFEST.in` only
affects built distributions, which Frappe apps don't use. Excluding
`ui_test_helpers.py` there accomplishes nothing.

The real lever is runtime gating. Frappe already ships
`frappe.tests.utils.whitelist_for_tests` (`apps/frappe/frappe/tests/utils/__init__.py:12`),
which refuses unless `frappe.in_test`, or `frappe._dev_server and frappe.conf.allow_tests`,
or `os.environ.get("CI")`. A production server is none of those, so the helpers become
dead there regardless of site config.

### Note on decision 6 — the dialog copy

```
Public space                        Private space
+------------------------------+    +----------------------------------+
| Leave "General"?             |    | Leave "Leadership"?              |
| You can rejoin at any time.  |    | This space is private. You won't |
|          [Cancel] [Leave]    |    | be able to rejoin unless a       |
+------------------------------+    | member adds you back.            |
                                    |          [Cancel] [Leave]        |
                                    +----------------------------------+
```

---

## 4. Work groups

Grouped so that **no two groups touch the same file**. They can be done in parallel or
in any order. The file list for each group is the ownership boundary — if a group needs
to change a file it does not own, it should report that rather than edit it.

### Group A — Polls (backend + frontend + poll tests)

**Owns:** `gameplan/gameplan/doctype/gp_poll/gp_poll.py`, `gameplan/mixins/on_delete.py`,
`gameplan/permissions.py`, `frontend/src/components/Poll.vue`,
`gameplan/tests/features/test_polls.py`

1. **B1 above** — the cascade delete fix, plus a regression test.
2. **Percentage denominator** (decision 1). `update_tallies` currently divides each
   option's votes by `total_votes`, which on a multi-answer poll is the number of answer
   *rows*. Change it to distinct voters for `multiple_answers` polls. Single-answer polls
   are unaffected because voters and votes are the same number.
   `test_polls.py:177-198` currently asserts the old behaviour and its class docstring
   rationalises it — rewrite both.
   Check the result reads correctly against `Poll.vue`'s existing label, which already
   says "N answers from M people".
3. **Owner-only poll actions** (decision 2). Today `stop_poll` checks ownership, but any
   member can bypass it with `PUT /api/v2/document/GP Poll/<name>` because
   `can_edit_content` returns true for them and `_protected_fields_changed` is never
   reached. The same PUT can replace the `votes` child table — other people's ballots.
   Protect `stopped_at`, `votes`, `options` and `total_votes` against non-owner writes.
   Add tests that a plain PUT by a non-owner member is rejected.
4. **Allow vote change** (decision 5). `submit_vote` currently returns early when
   `has_voted()`. Make a second vote replace the first for single-answer polls.
   Multi-answer already toggles per option — verify that and leave it alone.
   `Poll.vue:81` disables the controls once `participated`; that has to be relaxed for
   single-answer polls so a change is possible. Rewrite `test_polls.py:75-84`, which
   pins the silent no-op.
5. **Fix a test that cannot fail.** `test_polls.py:320-326` uses `frappe.get_doc`, which
   performs no permission check, so it passes even if archiving revoked read access
   entirely. Use `check_permission("read")` — `test_archived_spaces.py:172-177` shows the
   correct pattern.

### Group B — Test harness and coverage

**Owns:** `gameplan/tests/base.py`, `gameplan/tests/fixtures.py`,
`gameplan/tests/test_get_request_transactions.py`,
`gameplan/tests/permissions/test_content_access.py`,
`gameplan/tests/permissions/test_permission_matrix.py`,
`gameplan/tests/features/test_discussions.py`, `test_drafts.py`, `test_profiles.py`,
`test_unread.py`, `test_email_digest.py`

1. **Rollback runs in the wrong place.** `base.py:41` puts `frappe.db.rollback()` in
   `tearDown`. `unittest` skips `tearDown` when `setUp` raises, so a half-built persona
   set stays in an open transaction — and the next test class's `setUpClass` calls
   `frappe.db.commit()`, making it permanent on the site.
   Move it to `self.addCleanup(frappe.db.rollback)` at the top of `setUp`. Note that
   `base.py:32` already uses `addCleanup` for the index guard, with a comment explaining
   this exact hazard.
2. **Five files override `tearDown` without rolling back:** `test_discussions.py:84`,
   `test_drafts.py:16`, `test_profiles.py:63`, `test_unread.py:307`, and
   `test_email_digest.py` (which has no `tearDown` at all). Rows written by one test
   method are visible to the next. Give them a rollback or move them onto
   `GameplanTestCase`.
3. **The POST-only guard is a hardcoded list.** `test_get_request_transactions.py:19-48`
   is a 28-entry literal dict, and the test iterates only that dict. A new mutating
   endpoint never joins it — which is the exact bug class the file exists to catch
   (Frappe rolls back the transaction at the end of any GET request, so a mutation
   reachable via GET silently no-ops in production).
   Invert it: enumerate every `@frappe.whitelist()` in `gameplan/` and assert each one
   declares `methods=["POST"]` unless it is in an explicit read-only allowlist. This
   passes today — all 17 currently-bare endpoints are genuine reads, plus two deliberate
   GET mutations (`api.accept_invitation` and `email_digest.open_digest_preferences`,
   both targets of links in outbound email, both of which commit explicitly and must
   stay GET).
4. **Lost coverage.** `permissions/test_content_access.py::TestUnsavedContent` loops over
   GP Comment, GP Page and GP Task. `GP Discussion` was never added, and it has its own
   hook (`gameplan/hooks.py:132`). That unsaved path is the create-time gate, so a
   regression letting a guest create a discussion in a space they were never granted
   would ship green. Add `GP Discussion` to the loop and assert `"write"` alongside
   `"read"` — the create gate is a write check in practice.
5. **Unread counts are essentially untested.** Nothing covers `get_unread_count`,
   `get_participating_unread_count`, `mark_all_as_read_for_project`, or the
   create/delete unread-record paths. In particular, add: the author is excluded from
   their own discussion's unread records, marking as read is idempotent, and the count a
   user sees is scoped to them.
6. **Fix the contradictory docstring** in `permissions/test_permission_matrix.py`. Per
   decision 4 the matrix is right and the docstring is wrong.

### Group C — Security and Cypress config

**Owns:** `gameplan/ui_test_helpers.py`, `frontend/cypress/support/seed.ts`,
`frontend/cypress.config.ts`, `.github/helper/site_config.json`, `AGENTS.md`, `TESTING.md`

1. **Layer the gates on `ui_test_helpers`.** Today the only thing standing between a
   logged-in user and a full site wipe is one truthy site-config key
   (`ui_test_helpers.py:34`). Add frappe's test-mode gate (see decision 7 note), and use
   `cint(frappe.conf.enable_ui_tests)` so the string `"0"` or `"false"` in
   `site_config.json` cannot enable it.
   **Care needed:** Cypress runs against a `bench start` dev server, so the frappe gate
   needs `allow_tests` in the site config. Update `.github/helper/site_config.json` and
   document any new key in `AGENTS.md` / `TESTING.md`. Confirm the specs still pass
   before calling this done.
   A role gate (e.g. `frappe.only_for("System Manager")`) is desirable on the destructive
   helpers, but check who Cypress actually calls `reset` as first — if a role gate breaks
   the specs, report that instead of breaking them.
2. **`create_invitation` is a privilege-escalation primitive.**
   `ui_test_helpers.py:302-321` takes a caller-controlled `role`, inserts with
   `ignore_permissions=True`, and returns the invitation `key`. `api.accept_invitation`
   is `allow_guest` and GET-reachable, and calls `user.append_roles(self.role)`. So on
   any site with the flag set, any authenticated user — including a Gameplan Guest — can
   mint themselves an invitation for `Gameplan Admin` and accept it.
   Restrict the accepted roles to `Gameplan Member` and `Gameplan Guest`, and reject
   `Gameplan Admin`. That kills the escalation while keeping the invitation specs
   working.
3. **`resetData` has no site pin.** `seed.ts:42-51` fires
   `POST /api/method/gameplan.ui_test_helpers.reset` at whatever site answers `baseUrl`.
   That endpoint deletes every row of every Gameplan doctype *and* every framework `User`
   except Administrator, Guest and the four personas.
   The branch already wrote a fail-closed site probe — `assertDemoSite` in
   `cypress.config.ts:44-107` — but wired it only into `realtimePreflight`, which only
   the realtime spec calls. Expose it as a task and call it from `resetData`, or once in
   `support/e2e.ts`.
4. **`SKIP_REALTIME_E2E` silently deletes realtime coverage.** `cypress.config.ts:176-181`
   makes the preflight return `available: false`, which turns the only genuine
   socket-delivery spec into `this.skip()`. Nothing asserts the variable is unset; the
   only protection is a YAML comment. Make the preflight **throw** when the variable is
   set in CI, so re-adding it reddens the run instead of quietly passing.

### Group D — Search isolation test

**Owns:** `gameplan/tests/platform/test_search_isolation.py`

**B2 above.** Test-only change. Do not touch `gameplan/tests/search_isolation.py` — the
production helper is correct.

### Group E — Remaining backend and CI reporting

**Owns:** `gameplan/mixins/mentions.py`, `gameplan/demo/seeder.py`, `gameplan/demo/demo.py`,
`.github/scripts/nightly_junit_to_markdown.py`

1. **`@everyone` query storm.** `mentions.py:36-52` fans out to every enabled Gameplan
   Admin/Member and calls `can_view_content(user_email, self)` for each one. Each call
   costs 2-3 queries, so an `@everyone` post on a 500-member site adds roughly 1,500
   synchronous queries inline in the POST that creates the discussion.
   The permission check itself is correct and closes a real title leak — keep it, but
   resolve the audience in one query, or move the fan-out to a background job.
   **Do not edit `gameplan/permissions.py`** (Group A owns it). If a batch helper belongs
   there, implement it locally or report it.
2. **`Seeder.validate_events` does not prevent the failure it was added for.**
   `demo/demo.py:51-62` and `seeder.py:56-89` validate only JSON parseability, a known
   `type`, a matching handler, and the timestamp format. Cross-references are left to the
   replay — but a dangling reference is the most likely way to break a hand-edited
   fixture. Today, deleting a `space` line while leaving discussions that point at it
   passes validation, then `clear()` runs and **commits**, then the replay raises and
   rolls back, leaving the site empty with no demo data.
   Add a static reference pass: collect every `id`, then check that every `on`, `space`,
   `community` and actor reference resolves within the log, before anything is cleared.
3. **Skipped specs are scored as passing.** `nightly_junit_to_markdown.py:17-21` only
   looks for `<failure>` and `<error>`, so a spec whose every test is skipped rolls up
   into "all iterations passed". Count `<skipped>` and surface it.

### Group F — Leave space UI

**Owns:** `frontend/src/pages/SpaceDiscussions.vue`, `frontend/src/data/spaces.ts`,
`frontend/cypress/e2e/spaces/membership.cy.ts`

Implement decision 6.

Background: `SpaceDiscussions.vue:163-171` adds a Join/Leave item gated on
`canEditSpace`, which is only `!readOnlyMode && !isArchived` (`data/spaces.ts:74`).
Nothing considers privacy or membership, and it fires immediately with no dialog — while
the neighbouring `archiveSpace` and `unarchiveSpace` both use `dialog.confirm`. The
comment at `data/spaces.ts:66` even says `canEditSpace` is for "non-destructive edits".

For a private space, `can_view_space` is exactly `is_space_member`
(`gameplan/permissions.py:94-95`), so leaving makes `join()`'s `require_view_access()`
start failing. Recovery needs another member (any member of a private space passes
`can_manage_space`) or, if you were the sole member, a global admin.

Also: the item is dead for guests. `get_joined_spaces` unions member rows with
`GP Guest Access` rows, so `hasJoined()` is true for a guest's granted space — a guest
sees "Leave space", clicks it, and nothing happens, ever. This branch shipped
`260e924e fix(sidebar): hide space controls from guests` and missed this one.

The existing spec at `membership.cy.ts` only exercises the public space "General", where
leaving is reversible, so it cannot catch any of this. Update it for the dialog and add
private-space coverage.

---

## 5. Rules for whoever implements this

- **Do not run the test suite in parallel.** `bench run-tests` against
  `gameplan-demo.test` uses one database and one search index. Two concurrent runs
  collide on the personas and on `setUpClass`'s commit. Serialize verification.
- **Never run Cypress against anything but `gameplan-demo.test`.** The specs call
  `gameplan.ui_test_helpers.reset`, which deletes all Gameplan data on whichever site the
  request resolves to. Confirm `frappe serve` actually resolves the demo site first —
  host aliasing can route it to the default dev site.
- **Tests are the spec.** When a test surfaces a real bug, fix the bug. Do not make a
  test pass by encoding the buggy behaviour as the expectation. The expectation changes
  here are legitimate only because section 3 records the product intent.
- Python: tabs, double quotes, line length 110 (ruff). Frontend: Prettier.
  `pre-commit run --all-files`.
- Commit small, complete pieces as the work progresses. If work is parallelised, have one
  process do the committing — concurrent agents committing to the same branch race on the
  git index.

## 6. Done when

- `bench --site gameplan-demo.test migrate` then
  `bench --site gameplan-demo.test run-tests --app gameplan` exits 0.
- `cd frontend && yarn build` succeeds.
- `pre-commit run --all-files` is clean.
- Cypress passes against `gameplan-demo.test`.
- `TEST_SUITE_PLAN.md` and `TESTING.md` test counts match reality.

---

## 7. Checked and found fine — do not re-review

Recorded so nobody spends time here again:

- Cypress retries are genuinely off (`runMode: 0`, `openMode: 0`), no `CYPRESS_RETRIES`
  anywhere, and the action adds none.
- No `continue-on-error`, no swallowed test exit codes. The nightly gate fails closed
  even when its output is empty.
- The search-index redirect in `gameplan/tests/__init__.py` is airtight — no `test_*.py`
  exists outside `gameplan/tests/`, so it is imported before any test module.
- No `.only`, no `it.skip`, no `cy.wait(<number>)` anywhere in the Cypress tree.
- Every mutating frontend call carries `method: 'POST'`. Only two `useCall` sites exist
  and both are correct.
- The gray-shades-only styling rule is respected; no color-shade classes were introduced.
- No memory leaks — socket listeners, watchers and timers all have teardown.
- Poll vote state is server-authoritative against double-click and empty-vote races.
- The search project-filter change is a genuine **security fix**: a caller-supplied
  filter used to overwrite the permission filter and can now only narrow it.
- The test-suite reorg was near coverage-neutral: of ~75 deleted backend behaviours, 69
  are covered and 3 weakened; all 42 old Cypress `it()` blocks have successors. The only
  real loss is item B.4 above.
