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
- `create_discussion`, `create_comment`, `create_task`, `create_page`
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

#### Guest policy (2026-07-24)

Guests are participants, not read-only viewers. In a space they've been granted
access to, a guest **can** edit their own content, react to any post or comment, and
comment on discussions. A guest **cannot** touch anyone else's content (the matrix
rows are for member-owned content, so guest `write`/`delete` there are `False`), and
gets nothing at all outside the spaces they were granted. The full spec lives in
`features/test_guest_participation.py`. Note: whether a guest may delete their own
content is an open product question — current behavior (cannot) is characterized
there, not asserted as intended.

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

| Scenario                   | Seeds                                                                                         | Returned ids                                        |
| -------------------------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| `onboarded`                | Community "Acme" with an auto-created General space                                           | `community`, `space`                                |
| `space_with_discussion`    | Public space "Engineering" with a discussion "Welcome thread"                                 | `community`, `space`, `discussion`                  |
| `private_space_with_guest` | Private space "Secret Plans" (member is a space member, guest has access); `space` is General | `community`, `space`, `private_space`, `discussion` |
| `two_communities`          | Communities "Alpha"/"Beta", one public space each                                             | `communities` (2), `spaces` (2)                     |

Log in as a persona with `cy.loginAs(persona)` where persona is one of `admin`,
`member`, `secondMember`, `guest`, `outsider` (all seeded with password `admin`).

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

## 4. CI

- **Server tests** run the full backend suite twice: on MariaDB (`server-tests.yml`)
  and on SQLite (`server-tests-sqlite.yml`), both via
  `bench --site gameplan.test run-tests --app gameplan`.
- **UI tests** (`ui-test.yml`) run Cypress and produce JUnit results. A markdown
  report is built from the JUnit XML and posted as a sticky comment on the PR
  (`ui-test-report.yml` handles fork PRs, where the token is read-only).
- Cypress retries failed specs twice in run mode (`retries.runMode: 2`).

## 5. Migration status

The foundation for the new layout is in place (this step). The legacy tests are still
present and green; they migrate into the new layout in Step 2.

Still present:

- Flat backend files: `gameplan/tests/test_*.py`
- Per-doctype tests: `gameplan/gameplan/doctype/*/test_gp_*.py`
- `gameplan/test_api.py` — the legacy seed endpoint (`clear_data`), used by the
  existing specs. It gets deleted in Step 2.
- 21 flat specs directly under `cypress/e2e/`.

Step 2 moves these into the grouped layout above and removes `test_api.py`.
