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

Frontend coverage is collected from the Cypress layer, not from Vitest — see
§ 2 "Coverage". There is still no unit-test runner; `src/utils` and `src/composables`
together are ~970 of 32k frontend lines, which is why one has not earned its keep.

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

Always run against a disposable test site, never a dev site with real data.

`<site>` in every command below is your bench's test site. Resolve it once: run
`ls sites/` and pick the site whose `site_config.json` has `"allow_tests": true`.
CI uses `gameplan.test`.

```bash
# Full backend suite
bench --site <site> run-tests --app gameplan

# Just the permission matrix
bench --site <site> run-tests --module gameplan.tests.permissions.test_permission_matrix
```

### Coverage

Both layers are measured, and both are **informational** — no minimum is enforced
and no check fails on coverage. Both emit Cobertura XML, so one script renders both;
`--profile` picks the denominator, area map and caveat.

```bash
# Backend — writes sites/coverage.xml
# (needs coverage in the bench env: env/bin/pip install coverage)
bench --site <site> run-tests --app gameplan --coverage
python .github/scripts/coverage_report.py ../../sites/coverage.xml \
  --profile backend

# Frontend — needs an instrumented build, then the usual Cypress run
cd frontend && GAMEPLAN_COVERAGE=1 yarn build   # from the bench: GAMEPLAN_COVERAGE=1 bench build --app gameplan
yarn test
yarn coverage:merge
python ../.github/scripts/coverage_report.py coverage/cobertura-coverage.xml \
  --profile frontend
```

#### The two numbers are not comparable

The backend number comes from unit and integration tests that assert on what they
execute. The frontend number comes from Cypress driving an instrumented build, so a
line counts as covered when it **ran** — a happy-path spec marks everything it
renders past, asserted or not. Read the frontend number to find untouched areas, not
as a quality score, and do not read the gap between the two as a quality gap. The
report footer says so on every frontend comment.

#### What is excluded, and why the denominator is honest

`coverage_report.py` measures **product code only**. For the backend this matters a
lot: `frappe.coverage` points coverage at the whole app directory, so an unfiltered
report counts the test suite itself — ~100% covered by construction — and inflates
the headline (87.6% unfiltered against 83.7% real, when this was written). Each
profile's `excluded` tuple is the filter, and the report footer always names what it
dropped.

The frontend has the mirror-image trap. 32 routes are lazy `() => import(...)`, so a
page no spec visits never registers in `window.__coverage__` and would drop out of
the report entirely — flattering the percentage by shrinking the denominator rather
than counting the file as 0%. `frontend/vite.config.ts` therefore writes a zeroed
baseline of every instrumented file at build time, and `yarn coverage:merge` merges
it *under* the runtime data. Untouched files count as 0%, which is the honest number.

`GAMEPLAN_COVERAGE=1` is what enables instrumentation. Only `ui-test.yml` sets it:
it roughly doubles bundle size and slows every expression, so no production build
should ever carry it.

One more trap, specific to CI. `bench get-app` **clones** the repo into the bench
rather than symlinking it, so the instrumented build writes its baseline under
`~/frappe-bench/apps/gameplan/frontend` while Cypress writes `.nyc_output` in the
workspace checkout — two trees. The recorded coverage paths belong to the bench
tree, and nyc silently discards every entry outside its own cwd, so merging from
the workspace yields `0/0` and a report with nothing in it rather than an error.
`COVERAGE_ROOT` (consumed by `coverage:merge`) points nyc at the tree the paths
name. Locally it is unset and everything is one tree, which is exactly why this
only ever breaks in CI.

#### Where the numbers show up

Both consumers are self-contained — no Codecov, no shields.io:

- **Pull requests** get exactly one **Test report** comment, plus the same content in
  each job summary. Server Tests and UI Tests finish at different times and each knows
  only half the story, so `.github/scripts/pr_comment.py` gives each a named section of
  one comment rather than a comment each. Every workflow rewrites only its own section.

  The comment is written to be skimmed: one status line per layer, the failing tests
  named in full underneath it, and everything that passed folded into a `<details>`.
  Nobody should have to expand anything to learn whether the run is red or which test
  broke.

  Two workflows editing one comment can race — the API has no compare-and-swap — so
  each writer verifies its section survived and re-applies it if not. Both writers
  doing this is what makes the comment converge.

  Fork PRs are served by the `*-report.yml` companions, which run in the trusted base
  repo. Those jobs resolve which PR to comment on from the `workflow_run` event's
  `head_sha` and `head_repository` via the API — never from an uploaded artifact,
  which a fork controls and could point at any PR in the repo. A commit can belong to
  several open PRs, so the match must be exactly one or the job comments nowhere.

  Those jobs also parse artifacts the fork produced — both coverage XML and JUnit
  XML — so every read goes through `.github/scripts/safe_xml.py`, which caps size
  per document and across a directory and refuses any document declaring XML
  entities (a few nested ones expand to gigabytes). It is shared rather than
  reimplemented per renderer precisely because a guard only one of them remembers
  to apply is not a guard. Note it asks expat rather than scanning bytes for
  `<!ENTITY`: XML declares its own encoding, so the same declaration in UTF-16
  shares no bytes with an ASCII needle and would slip straight past.
- **The README badges** are `coverage.svg` on the orphan `badges-backend` and
  `badges-frontend` branches, linked by raw URL. `server-tests.yml` and `ui-test.yml`
  republish them on pushes to `develop`, and only when the rendered SVG actually
  changed, via `.github/scripts/publish_badge.sh`. They are kept off `develop` on
  purpose: a commit per coverage change is noise in the history people read. Each
  branch is force-pushed to a single commit, so neither accumulates, and they are
  separate branches because both workflows fire on the same push and a shared branch
  would have them clobbering each other. The badges therefore always show `develop`,
  not the branch you are reading.

  Publishing lives in a **separate `badge` job** in each workflow, gated on a push
  to `develop` and holding the only `contents: write` in the file. The test job
  stays `contents: read` and hands the rendered SVG over as an artifact, because
  it checks out and executes pull-request code — `install.sh`, the frontend build,
  the specs — and a repo-write token there would be a write credential handed to
  code under review. Note that a job-level `permissions:` block *replaces* the
  workflow-level one rather than adding to it, so a job needing both has to say
  both.

  The badge jobs are deliberately not `continue-on-error`. The first version was,
  and it reported success while a 403 published nothing, leaving the README badge
  404ing with no signal anywhere. By the time they run the suite has passed, so a
  red run blocks nobody and is the only thing that says the badge is stale.

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

### Enabling the seed API

`gameplan/ui_test_helpers.py` deletes every Gameplan row and every framework `User`
except the personas. Bench installs an app by putting its repo directory on `sys.path`,
so that file exists on every server that runs Gameplan and packaging cannot exclude it.
It is therefore gated at runtime, three ways, and **all three must hold** or the seed
call throws and every spec fails in its `beforeEach`:

| Gate                                                 | Where it comes from                           | How to satisfy it locally                                                                                |
| ---------------------------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Test mode (`frappe.tests.utils.whitelist_for_tests`) | test run, dev server + `allow_tests`, or `CI` | `allow_tests: 1` in `site_config.json` **and** a dev server (see below)                                  |
| `enable_ui_tests`                                    | `site_config.json`, read with `cint`          | `enable_ui_tests: 1` — a number or JSON boolean, not the quoted string `"true"`, which `cint` reads as 0 |
| System Manager                                       | `frappe.only_for`                             | nothing to do: Cypress seeds as Administrator, whom `only_for` waves through                             |

The dev-server part is the one that bites. `frappe._dev_server` is read from the
`DEV_SERVER` environment variable, which `bench start` sets and a bare
`bench --site … serve` does not. So start the local Cypress target as either:

```bash
bench start                                                     # sets DEV_SERVER itself
DEV_SERVER=1 bench --site <site> serve --port 8002              # standalone server
```

CI needs no special handling: GitHub Actions exports `CI`, the workflow runs
`bench start`, and `.github/helper/site_config.json` carries both `allow_tests` and
`enable_ui_tests`.

`create_invitation` will only mint `Gameplan Member` and `Gameplan Guest` invitations.
`gameplan.api.accept_invitation` is `allow_guest` and GET-reachable and appends the
invitation's role to the accepting user, so an unrestricted role here would let anyone
grant themselves `Gameplan Admin`.

### Seeding data

Reset and seed data with `resetData(scenario)` from `cypress/support/seed.ts`. One call
proves the responding site is the one `baseUrl` names, logs in as Administrator, wipes
all Gameplan data, resets the persona users, and seeds the scenario. It yields the ids
of the seeded records.

The site check is the `assertConfiguredSite` Node task in `cypress.config.ts`: it asks
the server for its own site name rather than trusting the URL, so host aliasing, a
`--site`-pinned server or a stale `default_site` cannot silently route the wipe at a
site with real data. It is memoized per origin, so it costs one request per run.

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

### Test targets and ports (authoritative)

This is the source of truth for Cypress site/port routing:

- **Local:** `frontend/cypress.config.ts` defaults to
  `http://gameplan-demo.test:8002`, which is one developer's site name. On any other
  bench, override it with `CYPRESS_BASE_URL=http://<site>:8002`. Start the server with
  `DEV_SERVER=1 bench --site <site> serve --port 8002` — without
  `DEV_SERVER` the seed API's test-mode gate refuses (see "Enabling the seed API"
  above). All local Cypress runs and seed/reset calls use this disposable test site.
- **Local realtime authentication:** `:8000` is a second
  `<site>`-pinned Frappe server used by Socket.IO to authenticate the
  browser session. Start it with
  `DEV_SERVER=1 bench --site <site> serve --port 8000`. Socket.IO itself
  listens on `:9000` (`bench socketio`). Do not point Cypress or seed/reset calls at
  `:8000`; it is an authentication target, not the configured local test runner.
- **CI:** `.github/workflows/ui-test.yml` overrides `CYPRESS_BASE_URL` with
  `http://gameplan.test:8000`. CI runs `bench start`, whose Procfile starts Socket.IO,
  so the realtime spec runs for real. `SKIP_REALTIME_E2E` is deliberately **not** set:
  the preflight throws when it is set and `CI` is set, because a skipped spec rolls up
  as a passing one and the variable would silently delete the suite's only genuine
  socket-delivery coverage. Locally the variable still just skips the spec — a bench
  without `bench socketio` running is a normal state.
- **Retired:** `:8001` was a historical local runner. It is not part of the current
  setup and must not be used.

**Realtime on a local bench:** genuine delivery uses the three local processes
listed above. Under `developer_mode`,
`apps/frappe/realtime/utils.js::get_url` rewrites the socket origin's port to
`common_site_config.json`'s `webserver_port`. The earlier SameSite theory was wrong:
the cookie is sent; it was being validated against a different site.

`discussions/realtime-activity.cy.ts` has a behavioral preflight with distinct
failure messages for the configured Cypress server, realtime authentication
target, and Socket.IO server.

The site and web port come from `CYPRESS_BASE_URL`; the authentication and socket
ports default to `:8000` and `:9000` and can be overridden with
`GAMEPLAN_REALTIME_AUTH_PORT` and `GAMEPLAN_SOCKET_PORT`.

After seeding, the preflight mints a new persona session on each web port and resolves
the acting user immediately in the same Cypress task. It does not inspect process
names, and it never carries a sid from one Cypress step to another.

Three traps matter when checking this manually:

1. `frappe.realtime.get_user_info` returns `{}` unless the request includes
   `X-Frappe-Socket-Secret`; `{}` means “missing secret,” not “Guest” or “wrong
   site.” Get the secret with
   `bench --site <site> execute frappe.realtime.get_socketio_secret`.
2. Test-suite pressure can expire sessions within minutes. Mint the sid and resolve
   it in the same step; otherwise `session_expired` / `Guest` can be misdiagnosed as
   a site-routing failure.
3. `bench browse --site <site> --user X --sid` prints a session id for that user and
   exits. It needs `developer_mode: 1` in `site_config.json` for any user but
   Administrator, and `--sid` without `--user` exits with an error. Where that command
   is not available, log in with `POST /api/method/login` and password `admin`. Curl
   stores the HttpOnly sid on a `#HttpOnly_` line; extract it from the cookie jar with
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

- Run only against the disposable test site, never a site with real data.
- The target site needs `enable_ui_tests: 1` and `allow_tests: 1` in its
  `site_config.json`, and its server must have been started with `DEV_SERVER` set —
  see "Enabling the seed API" above.
- **Warning:** the seed/reset endpoints wipe ALL Gameplan data on whichever site the
  request resolves to. `resetData` proves the responding site's identity first and
  fails the spec if it is not the site `baseUrl` names, but do not rely on that alone
  when running anything by hand.
- **The server must be running current code.** A long-lived `frappe serve` keeps the
  Python it booted with, so a spec covering a backend change made after the server
  started fails in a way that looks like a product or spec defect. `clear-cache` does
  not help — only a restart does. When a spec fails on an assertion the backend suite
  proves, check the server's age before touching the spec:

  ```bash
  ps -o lstart= -p "$(pgrep -fo 'serve --port 8002')"
  git log -1 --format=%cd   # newer than the server? restart it, then re-run
  ```

## 4. CI

- **Server tests** run the full backend suite three times: on MariaDB
  (`server-tests.yml`), on SQLite (`server-tests-sqlite.yml`), and on MariaDB against
  Frappe `version-16` (`server-tests-v16.yml`), all via
  `bench --site gameplan.test run-tests --app gameplan`.
- **Backend coverage** is collected only in the canonical MariaDB lane
  (`server-tests.yml`), which runs with `--coverage`. SQLite and v16 stay cheaper
  compatibility lanes rather than measuring the same Python lines three times.
- **Frontend coverage** rides on `ui-test.yml`, which builds with
  `GAMEPLAN_COVERAGE=1` so Cypress drives an instrumented bundle.
- Both post a sticky PR comment and a job summary (`server-tests-report.yml` and
  `ui-test-report.yml` handle fork PRs, where the token is read-only), and on pushes
  to `develop` both republish their README badge. See § 2 "Coverage" for what the
  numbers do and do not count, and why they are not comparable to each other.
- **UI tests** (`ui-test.yml`) run Cypress and produce JUnit results. A markdown
  report is built from the JUnit XML and posted as a sticky comment on the PR
  (`ui-test-report.yml` handles fork PRs, where the token is read-only).
- Cypress does not retry failed tests in run mode (`retries.runMode: 0`), so a
  journey that passes only on a later attempt cannot report green.

## 5. Migration status

The migration is done. Everything described above is the current state, not a plan:

- Most backend tests live under `gameplan/tests/{features,permissions,platform}/`, and
  no `test_*.py` remains beside a doctype. New builders live in `fixtures.py`. The old
  `tests/utils.py` is still there, used only by `tests/test_v16_api_compat.py` and
  `tests/test_get_request_transactions.py`, which also still sit at the top level.
- All 39 specs sit in the grouped folders under `cypress/e2e/`, seed through
  `resetData(scenario)`, and log in with `cy.loginAs(persona)`.
- `gameplan/test_api.py` is deleted. `gameplan/ui_test_helpers.py` is the only seed
  surface, and every entry point is behind the three gates described in
  "Enabling the seed API" above.

What is not done yet is coverage: Step 3 of `TEST_SUITE_PLAN.md` lists the features that
still have no test at either layer.
