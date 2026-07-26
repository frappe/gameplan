# Testing Gameplan

This guide explains how Gameplan is tested, what belongs in each layer, and how to
run and extend the tests.

## 1. Test layers and ownership

Each layer owns a different kind of check. Put a test in the layer that owns it.

| Layer                              | What it runs on        | Owns                                                                  |
| ---------------------------------- | ---------------------- | --------------------------------------------------------------------- |
| Backend (Frappe integration tests) | Real database          | Business rules, permissions, edge cases, API contracts                |
| Cypress E2E                        | Real browser + backend | User journeys, one happy path per feature, UI/routing/mobile behavior |
| Vitest (planned, not set up yet)   | Node                   | Pure frontend logic only (no DOM, no network)                         |

The rule:

- Permission matrices and edge cases **never** go in E2E. They live in the backend
  suite, where they are fast, exhaustive, and run against the real database.
- E2E covers the happy path a user actually walks through. If an E2E test would need
  a permission check or an edge case to be correct, that check belongs in the backend
  instead. Punting a flaky E2E detail down to a backend test is by design, not a
  workaround.

## 2. Backend tests

Backend tests are Frappe integration tests. They create data, act as a user, and
assert against the real database, rolling everything back after each test.

### Layout

```
gameplan/tests/
  base.py         # GameplanTestCase: personas + permission assertions
  fixtures.py     # builders (create_community, create_space, ...)
  features/       # per-feature behavior tests
  permissions/    # the permission matrix and permission tests
  platform/       # cross-cutting platform tests (search, migrations, ...)
```

### Personas

`GameplanTestCase` creates the standard cast fresh in every test and rolls it back in
`tearDown`. Each is available on `self`.

| Persona         | Email                | Role            | Represents                             |
| --------------- | -------------------- | --------------- | -------------------------------------- |
| `admin`         | admin@example.com    | Gameplan Admin  | Global admin                           |
| `member`        | member@example.com   | Gameplan Member | Owner of the test content              |
| `second_member` | member2@example.com  | Gameplan Member | Another member in the community        |
| `guest`         | guest@example.com    | Gameplan Guest  | Guest with access only where granted   |
| `outsider`      | outsider@example.com | Gameplan Member | A member outside every community/space |

### Using `GameplanTestCase`

Subclass it, use the personas on `self`, run code as a user with `as_user`, and assert
permissions with `assert_allowed` / `assert_not_allowed`.

```python
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_space, create_discussion


class TestExample(GameplanTestCase):
    def setUp(self):
        super().setUp()
        self.community = create_community("Acme", members=[self.member])
        self.space = create_space("Engineering", self.community)

    def test_member_can_edit_own_discussion(self):
        discussion = create_discussion("Hello", self.space, owner=self.member)

        # Run a block as a specific persona
        with self.as_user(self.member):
            ...

        # Assert who may do what
        self.assert_allowed(discussion, "write", self.member)
        self.assert_not_allowed(discussion, "delete", self.outsider)
```

### Builders (fixtures.py)

Builders use product language (Community/Space), which maps to the old schema names
(`GP Team` = Community, `GP Project` = Space). Each accepts either a doc or a name
wherever a linked record is expected.

- `create_user`, `create_admin`, `create_member`, `create_guest`
- `create_community` (GP Team) and `create_space` (GP Project)
- `create_discussion`, `create_comment`, `create_task`, `create_page`, `create_poll`
- `grant_guest_access`
- `set_owner` (re-own a doc after insert, so content can belong to a persona)

### The permission matrix

`permissions/test_permission_matrix.py` is the executable spec of Gameplan's
permission model. A single table (`EXPECTATIONS`) maps space kind → actor →
`(read, write, delete)`, and the test walks every content doctype for every actor and
action. When the rules change, change the table.

To extend it:

- **New doctype** — build it in the world in `setUp` (add it to the `self.content`
  dict), and the matrix will assert it for every actor automatically.
- **New actor or space** — add rows/blocks to `EXPECTATIONS` with the expected
  `(read, write, delete)` tuple.

#### Permission tiers

The content doctypes model three tiers, and it matters which one a check is about:

- **read = view.** Can the user see this content's space?
- **write = interact.** Anyone who can reach a space — members and granted guests
  alike — holds `write` on its content. `write` means "may participate" (react,
  comment), _not_ "may edit anything". This is why the matrix shows guest `write` as
  `True` on member-owned content, and why `react()`'s plain `save()` succeeds for a
  guest. The gate lives in `permissions.content_has_permission`'s write branch: for a
  non-editor it allows the save only when nothing beyond interaction-safe fields
  (the `reactions` child table) changed. That helper (`_protected_fields_changed`)
  must work in two contexts — a **clean** doc (the permission gate / UI checks report
  "no changes" so guests pass) and a **dirty** in-memory doc at save time (it reads
  the stored row and diffs to catch a real edit) — so it never relies on
  `has_value_changed()`/`get_doc_before_save()` alone.
- **edit-others and delete = business rules.** Editing someone else's content is
  blocked at save time by the write branch above (via `can_edit_content`); deleting is
  gated by `can_delete_content`. These are the genuinely restricted actions.

#### Guest policy (2026-07-24)

Guests are participants, not read-only viewers. In a space they've been granted
access to, a guest **can** edit their own content, **delete** their own content, react
to any post or comment, comment on discussions, create and vote in polls, and record
space visits. A guest **cannot** edit or delete anyone else's content, and gets
nothing at all outside the spaces they were granted. The full spec lives in
`features/test_guest_participation.py`, `features/test_polls.py`, and
`features/test_spaces.py`.

### When a test fails

A red test means one side is wrong — the test or the code — and you decide which
against product intent, not against whichever is easier to change. If the code
violates the intended behavior, fix the code; never bend a passing assertion onto
buggy behavior just to go green. Only update a test when the intended behavior itself
changed (cite the decision in the commit message, as the guest policy above did).

### How to run

Always run against the local demo site, never a dev site with real data.

```bash
# Full backend suite
bench --site gameplan-demo.test run-tests --app gameplan

# Just the permission matrix
bench --site gameplan-demo.test run-tests --module gameplan.tests.permissions.test_permission_matrix
```

## 3. E2E tests (Cypress)

E2E specs drive a real browser against a real backend. They cover the happy path a
user walks through, one path per feature.

### Layout

Specs live in `frontend/cypress/e2e/`, grouped by area:

```
journeys/       # end-to-end smoke journeys (the smoke suite)
discussions/
comments/
polls/
spaces/
communities/
members/
tasks/
pages/
search/
notifications/
profile/
shell/
mobile/
```

### Seeding data

Reset and seed data with `resetData(scenario)` from `cypress/support/seed.ts`. One call
logs in as Administrator, wipes all Gameplan data, resets the persona users, and seeds
the scenario. It yields the ids of the seeded records.

```ts
import { resetData } from "../support/seed";

resetData("space_with_discussion").then(({ space, discussion }) => {
  // ... use the seeded ids
});
cy.loginAs("member");
```

Every scenario's community includes `member` and `member2`, so both personas can reach it
without any join step. Content is created **as its owner**, which also settles unread state:
a discussion is unread for every space member except the person who wrote it.

| Scenario                   | Seeds                                                                                                                                 | Returned ids                                                             |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `onboarded`                | Community "Acme" with an auto-created General space                                                                                   | `community`, `space`                                                     |
| `space_with_discussion`    | Public space "Engineering" with a discussion "Welcome thread" by `member`; General is left empty                                      | `community`, `space`, `general_space`, `discussion`, `discussion_slug`   |
| `private_space_with_guest` | Private space "Secret Plans" (member is a space member, guest has access) plus a public discussion in General; both mention "roadmap" | `community`, `space`, `private_space`, `discussion`, `public_discussion` |
| `search_page`              | Six "roadmap" results across two communities, spaces, authors, doctypes, and tags for exercising every search filter                  | `community`, `space`, `discussion`                                       |
| `two_communities`          | Communities "Alpha"/"Beta", one public space each                                                                                     | `communities` (2), `spaces` (2)                                          |
| `unread_discussion`        | Community "Acme" with General + "Product"; a discussion in General written by `member2`, so it is unread for `member`                 | `community`, `space`, `second_space`, `discussion`                       |

For a search test, call `gameplan.ui_test_helpers.rebuild_search_index` after seeding — the
SQLite index is built on demand, not by the seed.

Log in as a persona with `cy.loginAs(persona)` where persona is one of `admin`,
`member`, `secondMember`, `guest`, `outsider` (all seeded with password `admin`).

**Switching personas mid-test:** once a page has been loaded, use
`cy.switchUser(persona)` instead of `cy.loginAs`. Frappe re-sets the `sid` cookie on
every response for the session that request ran under
(`CookieManager.init_cookies`), so a request the old page still has in flight can land
after the login and hand the previous user's cookie back — the next `cy.visit` then
boots as the old user and the test fails on whatever it asserts about the new one.
`switchUser` unloads the page first (aborting those requests) and only continues once
the server names the acting user.

### Acting as a second user while a page is open

`cy.request` shares the browser's cookie jar, so it always acts as whoever the open
page is logged in as. When a spec needs _someone else_ to change something while the
page under test stays loaded, use the `requestAsUser` Node task
(`cypress.config.ts`), which logs in and calls the API in a session of its own:

```ts
cy.task("requestAsUser", {
  user: "member@example.com",
  path: `/api/v2/document/GP Discussion/${discussion}/method/close_discussion`,
});
```

`discussions/realtime-activity.cy.ts` uses it for the live-update path.

**Realtime on a local bench:** genuine delivery works when both web ports resolve to
the demo site. Under `developer_mode`,
`apps/frappe/realtime/utils.js::get_url` rewrites the socket origin's port to
`common_site_config.json`'s `webserver_port` (`:8000`). Cypress drives the
demo-pinned server on `:8002`, while the socket server validates its sid against the
demo-pinned server on `:8000`. The earlier SameSite theory was wrong: the cookie is
sent; it was being validated against a different site.

`discussions/realtime-activity.cy.ts` has a behavioral preflight with distinct
failure messages for all three required processes:

- `:8002` must respond as `gameplan-demo.test` (start with
  `bench --site gameplan-demo.test serve --port 8002`);
- `:8000`, the realtime authentication target, must also respond as
  `gameplan-demo.test` (start with
  `bench --site gameplan-demo.test serve --port 8000`);
- Socket.IO must accept a polling handshake on `:9000` (start with
  `bench socketio`).

After seeding, the preflight mints a new persona session on each web port and resolves
the acting user immediately in the same Cypress task. It does not inspect process
names, and it never carries a sid from one Cypress step to another.

Three traps matter when checking this manually:

1. `frappe.realtime.get_user_info` returns `{}` unless the request includes
   `X-Frappe-Socket-Secret`; `{}` means “missing secret,” not “Guest” or “wrong
   site.” Get the secret with
   `bench --site gameplan-demo.test execute frappe.realtime.get_socketio_secret`.
2. Test-suite pressure can expire sessions within minutes. Mint the sid and resolve
   it in the same step; otherwise `session_expired` / `Guest` can be misdiagnosed as
   a site-routing failure.
3. `bench browse --user X --sid` is unavailable in Frappe v16.28. Log in with
   `POST /api/method/login` and password `admin`. Curl stores the HttpOnly sid on a
   `#HttpOnly_` line; extract it from the cookie jar with
   `awk -F'\t' '$6=="sid"{print $7}' jar`.

Known Frappe limitation, deliberately without a PR yet: in `developer_mode`,
`get_url` discards the request origin's port unconditionally. The rewrite is needed
when the origin is Vite on `:8080`, which is not a Frappe server, but a bench serving
two sites on two real web ports can authenticate sockets for only the site on
`webserver_port`. A future fix should prefer an origin that answers as a Frappe site
and fall back to `webserver_port`; Faris chose to raise that upstream later.

A genuine two-browser version remains an explicit follow-up. Cypress has no native
multi-session support, so it would need `cy.session` juggling or an iframe and would
be the most flake-prone spec in the suite. The current reliable version keeps one
browser watching while a separate server-side session makes the change.

### Conventions

- **No bare `cy.wait(ms)`.** Wait on an intercept alias instead. The only exception is
  a test whose subject _is_ a debounce (then the wait is the thing under test).
- **Selectors: roles and aria first.** Query by role/aria/text the way a user would.
  `data-testid` is an escape hatch, used only when there is no accessible selector.
- **One happy path per feature.** Edge cases and permission checks belong in the
  backend suite.
- **Journeys are the smoke suite.** The `journeys/` specs walk the core flows
  end-to-end and are the first signal that something is broken.

### How to run

```bash
cd frontend && yarn test
```

- Run only against `gameplan-demo.test`, never another local site.
- The target site needs `enable_ui_tests: 1` in its `site_config.json`.
- **Warning:** the seed/reset endpoints wipe ALL Gameplan data on whichever site the
  request resolves to. Confirm the request actually reaches the demo site before
  running.
- **The server must be running current code.** A long-lived `frappe serve` keeps the
  Python it booted with, so a spec covering a backend change made after the server
  started fails in a way that looks like a product or spec defect. `clear-cache` does
  not help — only a restart does. When a spec fails on an assertion the backend suite
  proves, check the server's age before touching the spec:

  ```bash
  ps -o lstart= -p "$(ss -ltnp | grep -oP ':8001.*pid=\K[0-9]+' | head -1)"
  git log -1 --format=%cd   # newer than the server? restart it, then re-run
  ```

## 4. CI

- **Server tests** run the full backend suite twice: on MariaDB (`server-tests.yml`)
  and on SQLite (`server-tests-sqlite.yml`), both via
  `bench --site gameplan.test run-tests --app gameplan`.
- **UI tests** (`ui-test.yml`) run Cypress and produce JUnit results. A markdown
  report is built from the JUnit XML and posted as a sticky comment on the PR
  (`ui-test-report.yml` handles fork PRs, where the token is read-only).
- Cypress retries failed specs twice in run mode (`retries.runMode: 2`).

## 5. Migration status

The migration is done. Everything described above is the current state, not a plan:

- Backend tests all live under `gameplan/tests/{features,permissions,platform}/`. No
  `test_*.py` remains beside a doctype, and the old `tests/utils.py` is gone — builders
  live in `fixtures.py`.
- All 33 specs sit in the grouped folders under `cypress/e2e/`, seed through
  `resetData(scenario)`, and log in with `cy.loginAs(persona)`.
- `gameplan/test_api.py` is deleted. `gameplan/ui_test_helpers.py` is the only seed
  surface, and like its predecessor every entry point is gated on `enable_ui_tests`.

What is not done yet is coverage: Step 3 of `TEST_SUITE_PLAN.md` lists the features that
still have no test at either layer.
