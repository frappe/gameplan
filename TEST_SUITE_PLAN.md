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

1. **Multiple-answer polls stay and get a complete UI.** `PollEditor` exposes the
   `multiple_answers` toggle, poll options behave like checkboxes, and each answer
   can be retracted. The existing backend behavior is a supported product path,
   not dead schema.
2. **A plain reply does not create a bell notification.** The bell means someone
   addressed you specifically (Mention, Reaction, or Rich Quote). Replies reach
   the discussion owner through `GP Unread Record` and the email digest, avoiding
   duplicate unread signals and an unusably noisy bell.
3. **Global and community admins may stop someone else's poll.** Stopping and
   deleting a poll have the same authority; keeping stop owner-only was an
   unintended asymmetry.
4. **Bookmarks are strictly private, including from global admins.** A reading
   list is personal and follows the draft model rather than Gameplan's usual
   global-admin query exception.
5. **Polls are guest participation.** A guest with access to a Space may create a
   poll on a reachable discussion and vote in polls there, alongside the existing
   rights to comment, react, edit/delete their own content, and record visits.
   Guests still get nothing outside Spaces explicitly granted to them.
6. **Pin, close, and reopen stay available to any non-guest member who can reach
   the Space.** These are community content edits, not owner- or admin-only
   moderation actions.
7. **The reka-ui dropdown body-lock defect stays for now.** It leaves the page
   mouse-inert for a measured 14–330 ms after a selection because
   `DismissableLayer` releases the lock only when the menu unmounts. The tests
   wait for unmount; changing `modal` or opening an upstream issue is deferred.
8. **A multiple-answer poll counts answer rows and labels them “answers.”**
   Percentages therefore continue to total 100%, while wording such as “3 answers
   from 2 people” avoids presenting answer rows as voter count.
9. **Reacting to a poll should notify its author.** `GP Notification` needs a
   `poll` link plus reaction-notification wiring equivalent to discussions and
   comments; this requires a schema change and migration.
10. **Mentioning someone who cannot see the Space stays silent.** This prevents
    inaccessible Space information leaking through notifications. Warning the
    author that the mention was suppressed is a known UX gap, not work for this
    branch.
11. **The frappe `LinkTableField.apply_join` defect is already fixed on
    `develop`, but not in this bench's `version-16`.** The notification workaround
    stays until the bench runs a frappe version that folds permission conditions
    into the JOIN's `ON` clause. Requesting a version-16 backport remains Faris's
    decision.
12. **Draft loading blocks editing.** The composer is non-editable and clearly
    says the draft is loading until the fetch settles, eliminating the race in
    which typing could be lost or overwrite the saved draft.
13. **Guests see neither “New space” nor “Sort spaces.”** A guest cannot create a
    Space, and neither affordance belongs in their navigation.
14. **Poll actions use `/api/v2`.** `Poll.vue` moves off the legacy
    `run_doc_method` resource API in line with the frontend API convention.
15. **Two discussion lifecycle behaviors are intentional.** Deleting the only
    reply makes the discussion itself the last post again, and a closed
    discussion rejects new polls as well as new comments.
16. **Archived Spaces stay viewable while participation freezes.** Their action
    menu offers neither Join nor Leave, and polls retain the read-only “Show
    results” and “Copy link” actions. Voting and stopping are blocked.
17. **The remaining mutating endpoints without explicit POST methods move to a
    dedicated later branch.** Each call site must be audited before flipping its
    endpoint; this test-suite branch does not bulk-change the roughly 41
    outstanding methods. The working checklist lives in `audit-post-methods.md`.
18. **Install and run `pre-commit` before pushing.** The documented lint command
    has not run on this machine because `pre-commit` is absent; final branch
    delivery owns installing and running it.
19. **Realtime must be exercised genuinely end to end on this machine.** The
    frame-injection simulation is temporary and must be replaced after fixing the
    local demo-site socket authentication path.
20. **Step 4 CI guardrails remain out of scope.** Finish Step 3, then hand the
    branch over without expanding into coverage/nightly/sharding work.
21. **Four Space mutation methods are explicit POST-only exceptions to decision
    17.** `GPProject.track_visit`, `join`, `leave`, and `mark_all_as_read` stay
    POST-only. The other mutating `GP Project` methods remain in the later audit;
    the doctype is only half-flipped.
22. **Space following is removed.** It had no notification, digest, or other
    product consumer, so its endpoints, composable, and menu affordance stay
    deleted. The `GP Followed Project` DocType remains only until a migration
    explicitly removes it.
23. **Archived Spaces are enforced at the backend for pages and tasks.** Create,
    update, direct delete, and moves into or out of an archived Space are refused.
    Reads, comments, and the parent Space's delete cascade remain available.
24. **Guests may record Space visits.** A guest may track a visit only in a Space
    they were granted; following no longer exists.
25. **Tests must not change product layout or the live search index.**
    `ProfileBentoEditorPanel` keeps its `lg` breakpoint and the profile spec uses a
    1280×900 viewport. Search suites redirect `GameplanSearch.INDEX_NAME` so they
    never drop or rebuild the site's real `gameplan_search.db`.

The permission tier supporting these decisions treats frappe `write` on content
as “may interact” (react, comment, vote). Who may edit or delete content is
business logic in `content_has_permission`: editors pass outright; interactors
pass only when no protected field changes. The diff handles both clean document
permission checks and dirty save-time checks.

Rejected along the way (do not resurrect): a generic `gameplan.api.react`
endpoint and an upstream frappe `permission_type` change. The permission tier
made both unnecessary.

Known archive limitation: discussion creation is blocked, but existing
discussions can still be renamed or deleted, and comments can still be added to
discussions and tasks. Whether archiving should freeze those actions remains a
separate product decision.

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

## Step 3 — Fill coverage gaps (IN PROGRESS)

Each area lands as a vertical slice: backend feature file + one E2E happy path.
Priority order:

1. Invitations — DONE (2026-07-24). Backend `features/test_invitations.py`
   (18 tests: create/accept/expire, role assignment, `accept_invitation`
   endpoint routing) + E2E `members/accept-invitation.cy.ts` (invitee accepts
   the link → user minted → password-setup redirect), with a `create_invitation`
   seed helper. Both green.
   - Local env note: on this devbox `:8000` serves the dev site
     (`serve_default_site`), so Cypress must run against a demo-pinned server
     (`bench --site gameplan-demo.test serve --port 8001`), and the demo site
     needs `mute_emails:1` (its `frappe serve` has no `dev_server`, so invite
     emails 501 on the missing outgoing account). Full suite there: **52/53
     passing, 1 pending, 0 failing** (see "Pre-existing failures resolved" below).

### Pre-existing failures resolved (2026-07-25)

Four Step-2-era failures were root-caused (all against the demo site on `:8001`):

- **`spaces/move-and-archive.cy.ts`** — the pin-cleanup assertion did a `POST`
  `frappe.client.get_list` after `cy.visit` had installed a session CSRF token;
  a `cy.request` `POST` doesn't send that token, so Frappe rejected it with
  `CSRFTokenError`. Switched the read to `GET` (reads aren't CSRF-checked). 2/2 green.
- **`discussions/discussion-actions.cy.ts`** (rename + close) — the timeline only
  refreshed on the realtime `new_activity` echo, even for the acting user's own
  action. That echo never arrives in local dev: the app (`:8080`) and socketio
  (`:9000`) are different origins, so the `SameSite` session cookie is dropped on
  the socket handshake and the tab connects as Guest. Product fix: `CommentsArea`
  now reloads activities whenever the acting client's own action changes the
  discussion doc (a new `activityVersion` prop bound to `discussion.doc.modified`),
  instead of depending on the socket. Backend activity creation was verified
  correct (`log_title_update` / `close_discussion`). 6/6 green.
- **`tasks/task-actions.cy.ts`** — real frappe-ui Dialog focus bug (reka-ui
  `DialogOverlay`'s `@pointerdown.left.prevent` cancels click-to-focus on nested
  fields; verified in real Chrome). Fix belongs upstream (committed locally on
  `forge/fix-dialog-click-focus`); test is `it.skip` until a fixed frappe-ui ships.
  This is the one pending test.
- **`members/member-management.cy.ts`** (invite) — same frappe-ui overlay root
  cause, but *not* a real user bug: the Users tab is a reka Tabs trigger that
  activates on `mousedown`; Cypress fires `pointerdown` first, the overlay cancels
  it, and Cypress then suppresses the synthetic `mousedown`. Native mouse and
  keyboard both work, so real users are fine. The test now activates the tab with
  `{enter}` (a real a11y path, forward-compatible with the frappe-ui fix). 2/2 green.
2. Polls — DONE (2026-07-26). Backend `features/test_polls.py` (34 tests: tally
   math, one-vote guard, retraction, anonymous polls, multiple-answer polls,
   stopping, and who may vote/stop/delete) + E2E `polls/poll-lifecycle.cy.ts`
   (member creates a poll → votes → tally updates → stops it), with a
   `create_poll` builder. Both green.
   - Product bugs fixed on the way: GP Poll had **no** `has_permission` /
     `permission_query_conditions` hook, so any Gameplan user could read and vote
     on polls in spaces they cannot see; `submit_vote` accepted options that were
     not in the poll (and divided by zero on an anonymous poll's first bad vote);
     `multiple_answers` was stored and rendered but never honoured; and
     stopped polls did not consistently reject later participation.
   - Follow-up fix (review): the vote methods run over `run_doc_method`, which
     builds the doc from the caller's own JSON and checks only `read`, and the vote
     then saves with `ignore_permissions` — so any reader (a guest included) could
     rewrite a poll's title, options and flags, or clear `stopped_at` to vote on an
     ended poll, by tampering with the payload. All three whitelisted methods now
     call `GPPoll.discard_client_state()` (a reload) first, so only server-computed
     state reaches the write. Locked by `TestTamperedVotePayload` (4 tests) and
     `test_guest_voting_cannot_rewrite_the_poll`.
   - Assumptions taken (see commit message): voting is participation, so guests
     may vote (and create a poll) in a space they've been granted; anonymous
     polls stay one-vote-per-voter even with `multiple_answers`, since an
     anonymous vote row carries no option; `total_votes` counts vote rows, so
     percentages still total 100% on a multiple-answer poll.
   - Still owner-only: `stop_poll`. A global/community admin can delete a poll but
     cannot stop it — flagged for a product decision, not changed here.
   - Not reachable from the UI yet: multiple-answer polls (`PollEditor` has no
     toggle and `Poll.vue` disables the options after the first vote). Poll.vue
     also still uses the legacy `run_doc_method` resource API rather than v2.
3. Notifications — DONE (2026-07-26). Backend `features/test_notifications.py`
   (23 tests: mention in a post/comment, @everyone, rich quote, no duplicate on
   edit, no self-notification, reaction notifications, the `unread_notifications`
   count, `mark_all_notifications_as_read` and `clear_notifications` scoping) +
   E2E `notifications/notifications.cy.ts` (member2 mentions member → unread
   badge → list → mark all read → badge clears). Both green.
   - Product decision taken (see commit message), needs Faris's confirmation:
     **a plain reply creates no GP Notification.** GP Notification is "someone
     addressed you" (Mention / Rich Quote / Reaction); a reply reaches the
     discussion owner through GP Unread Record, which is also how the email
     digest splits its two sections (`get_unread_notifications` vs
     `get_unread_discussions`). A `Reply` type would duplicate every unread count
     and drown the bell on a busy thread. The plan line above said
     "mention/reply → GP Notification", hence the flag.
   - Product bugs fixed on the way:
     - Mentioning yourself notified you. Reacting to your own post notified you,
       and your own reaction was counted in "N people reacted to your post".
     - @everyone notified every active Gameplan user, and the mention picker
       offers every active user, so both could notify people with no access to
       the space — leaking the discussion title into their bell and handing them
       a dead link. Both now gated on `can_view_content`.
     - The notification list was **empty for every user** (a 2026-06-24
       regression), and "Mark all as read" never marked anything: the `useCall`
       URL was relative (`gameplan.api.…` → POST `/g/gameplan.api.…`, which the
       SPA route answers with its own HTML and a 200), and the list joined
       `discussion.title` **and** `task.title` in one query while a notification
       only ever links one of the two (see the frappe bug below).
   - Upstream (frappe, not fixed here): `LinkTableField.apply_join` in
     `frappe/database/query.py` LEFT JOINs a linked doctype but adds that
     doctype's `permission_query_conditions` to the outer WHERE, so every row
     whose link is NULL is filtered out. The condition belongs on the ON clause
     (or needs an `OR <link> IS NULL`). Until it lands, Notifications.vue fetches
     the target titles per doctype; the workaround names the cause.
4. Reactions + bookmarks — DONE (2026-07-26). Backend `features/test_bookmarks.py`
   (19 tests: add/remove/idempotence, per-user `is_bookmarked`, privacy, the
   `feed_type: "bookmarks"` feed, delete cascade) + `features/test_reactions.py`
   (18 tests: the `react` operation contract — (user, emoji) identity, batches,
   junk payloads, reactions surviving an edit; who may react stays in
   `test_guest_participation.py` and what a reaction notifies in
   `test_notifications.py`) + E2E `discussions/reactions.cy.ts` (react to the post
   and to a reply, both survive a reload) and `discussions/bookmarks.cy.ts`
   (bookmark → find it under Bookmarks → remove it). All green.
   - Product bugs fixed on the way (GP Bookmark had **no** `has_permission` /
     `permission_query_conditions` hook at all):
     - Every Gameplan user could list, read and delete **everyone else's**
       bookmarks through the generic list/document API, and could create a bookmark
       in someone else's name. Bookmarks are now scoped to their `user` the way
       drafts are scoped to their owner.
     - A discussion anyone else had bookmarked could not be deleted at all:
       `on_trash` removed only the acting user's bookmark, so frappe's link check
       refused the delete (`LinkExistsError`). It now clears every user's bookmark
       for that discussion (privileged cascade of an already-authorised delete).
   - Assumption taken: no global-admin exception on the bookmark scoping — a
     reading list is personal, nothing in Gameplan reads another user's, and the
     closest precedent (`draft_query_conditions`) has none either.
   - Local env note: the demo server on `:8001` is a long-running `frappe serve`
     with no code reload, so it still runs the Python it started with. The two new
     specs were written to need no backend change (the reply in `reactions.cy.ts`
     is created through the v2 API before the first `cy.visit`, rather than by a
     new seed scenario). Whoever restarts that server should also run
     `bench --site gameplan-demo.test clear-cache` so the new hooks are picked up.
     Both specs have since been re-run against a fresh server (see item 5) and
     stay green with the new hooks live.
5. Guest access E2E — DONE, verified (2026-07-26). E2E
   `members/guest-access.cy.ts` walks the guest's whole scoped view on the
   `private_space_with_guest` scenario: lands in the community of their granted
   space, sees "Secret Plans" but neither "General" nor its post, opens the
   member's discussion, comments, reacts, and finds no Edit / Pin / Close / Move
   in Discussion Options. Backend gap it leans on is now closed:
   `permissions/test_guest_access.py` gained the two query-level tests the UI
   depends on (a guest's GP Project list is exactly their granted spaces; their
   discussion feed drops posts from spaces they were never granted) — the file
   only had `has_permission` checks, which a list query can bypass. Full backend
   suite green (288 tests across the three batches, exit 0).
   - Spec is green: **1/1, exit 0**, and the full Cypress suite alongside it is
     **27 specs / 58 tests, 58 passing, 0 failing, 0 pending**.
   - **The stale-runner trap that first made it look broken** (worth knowing, it
     will recur): the spec was initially written against the `:8001` demo server,
     a `frappe serve` started **Jul 23 01:50** — before
     `0d6270a fix(permissions): guests see communities of their granted spaces`
     (Jul 24 02:54). A running server never re-imports a changed module, so it
     kept answering a guest's GP Team list with the pre-fix `Team.name == ""` —
     empty. The guest had no community, `/g` resolved to `/g/onboarding`, and
     every guest route 404'd exactly as the old bug did. The failure looked like
     a spec or product defect and was neither.
     - Proof of the diagnosis: as `guest@example.com` over HTTP,
       `GET /api/v2/document/GP Team` returned `{"data": []}` on the Jul-23
       server and `[{"name": "acme"}]` on a server started from the same working
       tree. `bench clear-cache` does **not** fix it — the stale code is in the
       process, not the cache.
     - Resolution: ran the suite against a freshly started demo-pinned server
       (`bench --site gameplan-demo.test serve --port 8002`) instead. That also
       puts the Jul 24-26 backend work in front of the browser for the first
       time — guest team scoping, GP Poll and GP Bookmark permission hooks — so
       the 58/58 above is the first genuinely current green baseline. The earlier
       "52/53, 1 pending" number was measured against pre-Jul-23 backend code.
     - The spec is deliberately **not** `it.skip`'d: it passes on current code,
       which is what CI runs. Quarantining it would have hidden real coverage to
       accommodate a stale local process.
     - `:8001` is still stale and should be killed by whoever owns that process;
       an agent cannot (`kill` is refused by the permission classifier). Until
       then, start your own runner rather than trusting `:8001`, and see the
       runner-freshness check in TESTING.md § "How to run".
6. Discussion lifecycle backend — DONE (2026-07-26). Backend-only slice: the E2E
   happy paths (comment, rename, close, move) already live in
   `discussions/discussion-actions.cy.ts`, so no new spec.
   `features/test_discussions.py` gained 41 tests in five classes — `TestPinning`
   (scope Category vs Space, who pinned it, idempotent re-pin, unpin, activity
   log, a guest cannot pin, pinning is not a post), `TestClosingAndReopening`
   (closed_at/closed_by, activities, a closed thread refuses comments *and*
   polls, close/reopen idempotence, a guest cannot close), `TestCommentsCount`
   (add/delete a comment, polls count too, an edit does not),
   `TestLastPost` (a comment/poll becomes the last post, newest wins, deleting
   the newest falls back to the previous) and `TestParticipants` (distinct
   posters incl. the author, guests count, deleting someone's only comment drops
   them). Full backend suite green (338 tests across the three batches, exit 0);
   `discussions/` + `comments/` specs re-run green (20/20) against the
   demo-pinned `:8002` server.
   - Product bugs fixed on the way:
     - Deleting the only reply left the thread pointing at it: the delete cascade
       nulls `last_post`/`last_post_type`, but `update_last_post` had no branch
       for an empty thread, so `last_post_at` (the feed's sort key) and
       `last_post_by` (its author line) stayed at the deleted comment. The
       discussion is now its own last post again.
     - A closed discussion still accepted **polls**. `GPComment.before_insert`
       refuses a comment, but nothing refused a poll — the rule was enforced only
       by the UI hiding the composer. `GPPoll.before_insert` now checks it too.
   - Test-local helper (not a fixture): comments are inserted *as* their author,
     because participants/last-post bookkeeping keys off `owner` and
     `create_comment(owner=...)` rewrites the owner only after those side effects
     have run.
   - Assumption taken: pinning/closing are edits, so the existing
     `can_edit_content` gate (any member who can reach the space; guests never)
     is the rule — matching the frontend's `canEditDiscussion` affordance gate.
7. Realtime activity broadcast — DONE, with one documented simulation
   (2026-07-26). The `new_activity` room bug (fixed in Step 2) had shipped
   unnoticed because the only thing exercising the path was an incidental
   assertion in `discussions/discussion-actions.cy.ts`.
   - Backend: `features/test_realtime_activity.py` (17 tests) mocks
     `frappe.publish_realtime` and pins the broadcast on three axes: the **room**
     (`doctype`/`docname` set → the document room; no `user=`; `after_commit`),
     the **payload** (`reference_doctype` + a _stringified_ `reference_name`,
     which is what the listeners compare against), and **coverage** (close,
     reopen, pin, unpin, rename, move, a task value change — plus: one broadcast
     per activity row, nothing for a save that writes no activity, nothing for a
     rejected action). Removing `doctype=`/`docname=` from the mixin fails 9 of
     the 17, so the exact regression is pinned.
   - E2E: `discussions/realtime-activity.cy.ts`. `member2` opens the discussion,
     `member` closes it from a session of their own, and the timeline entry
     appears with no reload; navigating away unsubscribes. Both socket-room
     emits (`doc_subscribe` on mount, `doc_unsubscribe` on unmount) are asserted
     against a spy on the app's own socket
     (`#app.__vue_app__.config.globalProperties.$socket`).
   - The second session runs through a new `requestAsUser` Cypress **Node task**
     (`cypress.config.ts`), not `cy.request`: `cy.request` shares the browser's
     cookie jar, so it can only ever act as whoever the open page is logged in
     as. Reusable by any future spec that needs "someone else did this while I
     was looking at it".
   - **Simulated hop (bench limitation, not a product gap):** the socket cannot
     authenticate for `gameplan-demo.test` on this devbox. Under `developer_mode`
     the realtime server validates every session against
     `common_site_config.json`'s `webserver_port`
     (`frappe/realtime/utils.js::get_url`), i.e. `:8000` — and that server is pinned to `default_site`
     (`gameplan.localhost`) by `frappe/utils/bench_helper.py::get_sites`. The
     demo-site `sid` is unknown there, so the tab connects as **Guest** and is
     refused the document room. Verified with the same demo-site session:
     `get_user_info` on `:8002` identifies `member2@example.com`, while the
     realtime server's `:8000` authentication target identifies it as Guest.
     (The earlier "SameSite cookie is dropped on the handshake" theory in the
     Step-2 notes is wrong — the cookie is sent; it is validated against the
     wrong site.) The spec therefore hands the frame to the page's engine
     (`socket.io.engine.emit('data', …)`), so the real decoder, namespace routing
     and listener dispatch still run and only the network hop is skipped.
     Disabling `CommentsArea`'s `new_activity` handler makes the spec fail, so the
     client realtime path is load-bearing, not decorative. Fixing the environment
     needs a restart of the `:8000` server (or of the realtime server after a
     `webserver_port` change), which is Faris's call.
8. Pages (edit content, private vs space visibility + E2E).
9. Profile/settings (bento cards, custom emoji, quick reactions + E2E).
10. Search page E2E (filters; index hooks backend).
11. Space membership — DONE (2026-07-26). Backend
    `features/test_spaces.py` has 22 tests: join/leave behavior, guest visit
    allow/deny, both existing-visit timestamp update branches, the four approved
    POST-only instance methods, and the removed follow API contract. E2E
    `spaces/membership.cy.ts` has two paths: join → visible joined state → mark
    read → the actual sidebar unread count clears → leave, plus archived spaces
    exposing read actions but no Join/Leave.
    - The dead follow/unfollow methods, bulk endpoints, composable, menu actions,
      virtual field, generated type, and demo-seed writer are removed.
      `GP Followed Project` itself stays until a migration explicitly deletes the
      DocType/table; remaining references are its own controller/schema plus
      legacy cascade/team-sync/migration cleanup.
    - The review-prescribed document-scoped visit call exposed a real integration
      bug: Frappe v2 maps a POST document method to `write`, while `GP Project`
      write means space-management access. A visible member who has not joined
      therefore gets 403. The POST-only `track_visits` controller endpoint stays
      because it applies the method's explicit view-access gate; its frontend call
      uses a dedicated `useDoctype` instance so it cannot race with join/leave.
    - Verification: focused backend 22/22, E2E 2/2 at `retries=0`, frontend build
      green, and full backend 422/422 (16 + 295 + 111), all exit 0.
12. Mobile variants: create discussion + comment on iphone-6 viewport.
13. Remaining `api.py` endpoint tests (`onboarding`, `unread_notifications`,
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
