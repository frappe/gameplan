# Mutation testing — handoff

**Written:** 2026-07-29
**Updated:** 2026-07-31 — harness fixed, corpus re-measured honestly, nightly CI landed, ten product bugs closed.
**Status:** harness trustworthy, CI running, seven modules re-measured with zero no-verdict rows.

---

## 1. Environment

| Thing | Value |
|---|---|
| Bench | `~/frappe-bench` (a **second, SQLite-only** bench built for this work) |
| Site | `gp-sqlite.test`, admin password `admin`, `allow_tests: true` |
| frappe | `netchampfaris/frappe` @ `fix/sqlite-last-query` |
| gameplan | branch `feat/mutation-testing` |
| Harness | `gameplan/tests/mutation/` |
| Journal | `.mutation/journal.jsonl` |
| Node | 24.x via nvm, bench via pipx |

`AGENTS.md` names `gameplan-demo.test`; that site does **not** exist in this bench. Use
`gp-sqlite.test` here.

**The frappe branch is not optional.** It carries `fix(sqlite): publish last_query on the SQLite
driver`. Stock develop will likely fail on SQLite.

Every session needs:

```bash
export NVM_DIR=$HOME/.nvm; . $NVM_DIR/nvm.sh; nvm use 24
export PATH=$HOME/.local/bin:$PATH
cd ~/frappe-bench
```

---

## 2. How the harness works

Two stages, by design:

- **Stage 1 (`run`)** — mutates a source file in place, runs *only that module's own tests*, restores
  the file. Answers: *does this module's own test file pin its behaviour?*
- **Stage 2 (`verify`)** — re-runs each stage-1 survivor against the *full* suite, to catch survivors
  that some other module's tests kill.

```bash
env/bin/python -m gameplan.tests.mutation run    [--tier 1|2|all] [--module PATH] [--site NAME]
                                                 [--timeout N] [--limit N] [--budget-seconds N]
                                                 [--order round-robin] [--journal PATH] [--yes]
env/bin/python -m gameplan.tests.mutation report [--journal PATH] [--format text|md|json]
env/bin/python -m gameplan.tests.mutation verify [--journal PATH] [--site NAME] [--timeout N]
env/bin/python -m gameplan.tests.mutation restore   # recover source files after a hard crash
```

Run it with the bench python from `~/frappe-bench`. Execution is **serial on purpose**: every worker
shares one source tree, so concurrent in-place mutation would corrupt other workers' runs.

### The status vocabulary is the load-bearing part

`config.py` defines one source of truth and two aliases of it:

```
NO_VERDICT_STATUSES & KILLED_STATUSES == frozenset()   never counted as a kill
NO_VERDICT_STATUSES <= NON_SCORING_STATUSES            never reaches the score
NO_VERDICT_STATUSES <= RETRYABLE_STATUSES              never cached as done
```

Anything that is *not* a judgement made by the test suite — a timeout, a wedged site, a mutant that
broke the import, a run that died mid-flight — belongs in `NO_VERDICT_STATUSES`. Adding a status
anywhere else is how the original inflation bug happened (§3). The three relations above are
asserted by `gameplan/tests/platform/test_mutation_classification.py`; if you add a status, that test
tells you where it belongs.

Exit codes: `0` ok, `1` aborted, `2` usage, `3` nothing measured, `4` budget exhausted. `4` is
**green** — stopping on budget is the intended nightly outcome. `3` is not: it means the run burned
its budget without landing a single verdict.

---

## 3. The harness was inflating its own score

Every number in this document's earlier drafts came from a harness that counted infrastructure
failures as kills. Timeouts, wedged sites, any subprocess output containing the substring
`ImportError`, and mid-run deaths were all recorded as permanent, non-retryable **kills** — the most
favourable verdict, cached forever, never retried. The circuit breaker that was supposed to catch a
run going bad watched statuses the code never wrote, so it could not fire.

Fixed in `79e5ba98` (15 defects). "No verdict from the suite" is now its own class: never scored,
always retried, and it trips the breaker after `MAX_CONSECUTIVE_NO_VERDICT`.

**Consequence: every number measured before `79e5ba98` is an upper bound of unknown tightness.**
Do not retype a table into this file — regenerate it:

```bash
env/bin/python -m gameplan.tests.mutation report --format md
```

### Re-measured under the fixed harness

Five modules, 485 mutants, **zero no-verdict rows** — every mutant got a real verdict from the
suite, so these are honest stage-1 floors rather than low-denominator artefacts.

| Module | Mutants | Killed | Score | Old figure |
|---|---|---|---|---|
| `permissions.py` | 273 | 171 | 63% | 44% |
| `gp_discussion/api.py` | 74 | 65 | 88% | 82% |
| `gp_poll.py` | 54 | 45 | 83% | 87% |
| `gp_project.py` | 46 | 30 | 65% | 42% |
| `mixins/reactions.py` | 38 | 32 | 84% | 81% |

Three things the deltas hide, and none of them should be dropped when quoting the numbers:

- **The denominators changed for four of five modules**, so the percentages are not like-for-like.
  `mutators.py` gained new mutator kinds in the same branch, and three source files changed.
- **`gp_poll` did not regress.** It dropped because the fix *added* code: 9 new mutants. On the 45
  mutants common to both runs the score went *up* (89% vs 87%), and the one old survivor that
  disappeared is exactly the boundary comparison the fix replaced.
- **`gp_project` 42% → 65% is about half real.** The genuine gain is in `get_unread_count`. But
  deleting `as_dict` and `get_meta_tags` took 8 never-killed survivors out of the denominator.
  Deleting untested code raises a mutation score without testing anything — watch for this, it is
  the easiest way to fake progress here.

And one negative result worth keeping: **`permissions.py` did not move.** Its verdict set is
identical to the pre-branch run, function by function and status by status. The 235 lines of tests
added to its two mapped test files killed **zero** additional mutants. The 44% → 63% jump is
entirely the harness getting honest.

After the coverage round, two modules were re-measured again: `mixins/reactions.py` reached
**100% (38/38)** and `gp_project.py` **83% (38/46)**, both with zero no-verdict rows.

### The prediction that failed

Seven `ignore_permissions=True → False` mutants survived across `gp_project.py` and
`reactions.py`. The reasoning was sound as far as it went — *a surviving mutant on a security flag
is the harness asking whether the flag does anything* — and following it found a real problem: four
per-user doctypes were not scoped to their user, so their rows were reachable through the generic
document and list routes regardless of whose they were (§5).

The prediction that followed was that fixing those permissions would make the mutants killable.
**It was measured, and it was wrong: zero of the six in `gp_project.py` died.** Those call sites
only ever write the *caller's own* row — `track_visit` and `mark_all_as_read` both build it from
`frappe.session.user` — so the new hook permits them either way. What the hooks close is the
neighbouring surface where the row belongs to somebody else, which those lines never touch.

Two things to take from this. The mutants were a good *pointer* and a bad *test*: they told you
where to look and could not tell you whether the fix worked, and only a re-measure separated those.
And the same re-measure caught the fix having missed `GP Pinned Project`, a doctype of exactly the
same shape — including a new survivor of the same kind in the `archive()` line this branch had just
rewritten. Predict what a change will do to the score, then go and check; the gap between the two is
where the information is.

Two things about the numbers that were already wrong before that, and are worth knowing as a
cautionary tale: the first table grouped by *basename*, silently merging the two files named
`api.py`, and it claimed `mixins/reactions.py` was 100% when the journal said 59%. `reactions.py`
was then dropped from the work list on the strength of that wrong number — and it turned out to hold
a real product bug (§5, notification bug).

**Read stage-1 scores as a floor, not a verdict.** They mean "not caught by this module's own test
file", which is weaker than "not caught by anything".

---

## 4. Coverage gaps closed

### Digest login links — `fd92a2ef`

`gameplan/email_digest.py:144` — `open_digest_preferences` is `@frappe.whitelist(allow_guest=True)`
and calls `frappe.local.login_manager.login_as(user)`. Its second gate,
`is_valid_digest_login_link`, had **0 of 15 mutants killed**: every branch could be inverted
silently, including "expired link accepted" and "disabled user accepted".

This was never a live vulnerability — `verify_request()`'s HMAC check is the primary defence and
nobody can forge a link without the site secret. What it meant is that the defence-in-depth layer
had nothing holding it in place: a refactor could delete the expiry or `enabled` check and the whole
suite would stay green.

`TestDigestLoginLink` in `gameplan/tests/features/test_email_digest.py` closes it — 12 tests, all 23
digest-link mutants dead.

Two of those tests need explaining, because the obvious version of each does not kill its mutant:

- **`assertIs(result, False)`, not `assertFalse`.** The `return-none` mutator turns `return False`
  into `return None`, and `assertFalse(None)` passes. Three mutants hinge on this (L517, L521, L525).
  (The commit message for `fd92a2ef` says six; three is correct.)
- **The `or -> and` mutant needs the clock stubbed.** Under the mutant, a missing `expires` falls
  through to `get_datetime(None) < now_datetime()` — "now" compared against a "now" sampled
  microseconds later — so it still returns False *by accident* and survives a plain assertion. The
  test patches `gameplan.email_digest.now_datetime` and asserts it is **never called**: a missing
  field must be rejected on its own merits, before the clock is consulted. That is the real
  invariant, and it happens to be what kills the mutant.

### The rest — `8d6eda90`

Coverage across six backend modules, plus the harness's own first tests
(`gameplan/tests/platform/test_mutation_*.py` — classification, safety, mutators, report, cli, ci).
The harness had none before; it was measuring the codebase while being unmeasured itself.

Suite went 545 → 1067 tests over this branch.

---

## 5. Product bugs found by triage

Triaging survivors turned up real defects, not just missing assertions. That is the argument for
this whole exercise: a survivor is a question about the code, and sometimes the answer is that the
code is wrong. Details in the commits; the notable shapes:

- **`get_unread_count` could not run on SQLite at all** — `query1 + query2` renders a parenthesised
  compound `UNION`, which SQLite rejects. It only looked fine because the empty case short-circuits
  first.
- **`get_joined_spaces` returned duplicates** — one query plucked the id as an `int`, the other as a
  `str`, so `{33, "33"}` has two elements and `set()` deduped nothing.
- **`merge_with_project` did not check the merge target** — the v2 route checks write on the source
  only, and `validate_rename=False` skipped the framework's "you need write permission on the target
  to merge" check. A user who could manage one Space could merge it into a Space they had no rights
  to.
- **Poll close boundary disagreed between two modules** — at the exact instant of `stopped_at` the
  feed hid a poll the doctype would still accept a vote on.
- **Withdrawing a reaction re-lit the post owner's bell** — `notify_reactions` used
  `len(previous) == len(self)` as a proxy for "someone reacted". Removal changes the length too, so
  it notified again; and an emoji *swap* keeps the length equal, so a genuine new reaction notified
  nobody.
- **Client-supplied `order_by` with no allow-list** — an arbitrary field reached the query builder,
  and a three-token value made the tuple unpack raise, i.e. a 500 on a whitelisted endpoint.

Three of these (merge permission, poll boundary, reaction notification) were deliberately left
**un-tested** by triage, because the only test that kills the mutant is one that pins the bug. When
a survivor is telling you the code is wrong, write the fix, not the assertion.

Two more turned up in the second pass, and both are worth understanding as *shapes* rather than as
individual bugs:

- **Cross-user state was readable and writable by anyone.** `GP Notification`, `GP Project Visit`
  and `GP Discussion Visit` granted Member and Guest read/write/create with `if_owner` unset and had
  no permission hooks, so any signed-in user could read, enumerate and overwrite anyone else's
  notifications, visit history and read-state through the generic `/api/v2` document route. What
  pointed at it was seven surviving `ignore_permissions=True → False` mutants: **a surviving mutant
  on a security flag is the harness asking whether the flag does anything**, and here it did not —
  the role already held everything the flag could have been suppressing. Fixed with query-condition
  and `has_permission` hooks in `per_user_state.py`, not `if_owner`, which is actively wrong here
  because a notification's `owner` is whoever *triggered* it.
- **`archive()` orphaned other users' pins**, regenerating the exact invalid state that an existing
  cleanup patch was written to fix.

Both were found by reading the line a survivor pointed at, not by the mutant itself proving them.
That is the honest description of what this technique does: it does not find bugs, it tells you
which lines nobody has ever checked, and a surprising number of those turn out to be wrong.

### And two that did not survive scrutiny

Reported by triage, then disproved on re-derivation. Both are recorded because the *reason* they
were wrong generalises:

- **"Guests can enumerate every Community on the site."** Does not reproduce. The report was based
  on `frappe.get_all`, which defaults to `ignore_permissions=True` and is not a route any client can
  reach. Every user-facing door — `frappe.get_list`, `frappe.client.get_list`, and the
  `get_list_query` path — filters correctly. It was a coverage gap, not a leak.
- **"`content_has_permission`'s trailing `return True` is unreachable."** It is reachable and
  load-bearing: `frappe.permissions.get_doc_permissions` calls the hook with `ptype=None` to build
  the whole permission dict, and returning False there collapses it to `{None: 0}`.

Before acting on any claim that something is dead or leaking, reproduce it through a route a client
can actually take. `get_all` and `get_list` differ in exactly the way that matters.

---

## 6. CI — `2d12798e`

Two jobs.

**`.github/workflows/mutation-nightly.yml`** — cron, `--budget-seconds 2700` (~45 min), resuming
from a cached journal and rotating least-recently-measured modules first, so the corpus is covered
over several nights rather than one ~2h job pinned against the Actions ceiling. `timeout-minutes: 90`
is a backstop only: the budget is enforced *inside* the harness, between mutants, never mid-mutant —
a SIGKILL at the wrong moment is exactly what the restore guard exists to prevent. Gated on
`github.repository_owner == 'frappe'` so forks do not run it.

**`.github/workflows/mutation-pr.yml`** — mutates only the targets the diff touches and reports into
`$GITHUB_STEP_SUMMARY` rather than gating on a score. A percentage threshold on a five-minute sample
gets gamed or ignored; the useful artefact is the list of survivors in code the author just wrote.

Two flaws that adversarial review caught before merge, both worth remembering because they are the
same class of mistake:

- **Never cache the `.mutation/` directory — only the journal files.** Caching the directory
  transplanted crash sidecars and the campaign lock onto the next runner. A cancelled run left them
  behind, an `always()` save cached them, and the next night's fresh clone refused to start. Self-
  sustaining, and red on every PR too, under a gate message blaming the circuit breaker.
- **Mutant identity is derived from source, so nothing invalidated a verdict when the *tests*
  changed.** Deleting an assertion would never be re-measured; the nightly would look green while
  doing less work every night, blind to the one regression it exists to catch. Verdicts now carry a
  fingerprint of the test modules that produced them — including the shared helpers in
  `tests/base.py` and `tests/fixtures.py` that decide what those tests actually assert
  (`scope.py::_support_closure` resolves first-party imports transitively).

A third review found skip records were immortal: currency was inferred from *position* in a list
callers could filter, so the PR job resurrected weeks-old red baselines. Currency is data now — a
module that measures writes a record superseding its own skip.

`scope.py` deliberately has zero relative imports, so CI can run it as a plain script against a bare
checkout.

---

## 7. Claims from the first draft that did not survive checking

Recorded because they cost time, and because the pattern (a plausible mechanism, asserted once, then
inherited as fact) is worth recognising.

- **"An unexplained 6.4-hour stall in verify."** No such stall exists. The hypothesis was an orphan
  holding the SQLite lock — but that is self-contradicting: an orphan blocking the run would *produce*
  the `killed-timeout` record whose absence was the evidence. `communicate(timeout=)` is passed on
  both halves of the call. Probes at 3s, 8s and 30s caps were honoured to within 0.4s with zero
  orphans. What actually blocked stage 2 was mundane: **the test suite was red** (two
  `OutgoingEmailError` failures, since fixed).
- **"verify costs ~56 hours."** ~27h. The estimate used a stale suite time.
- **`mixins/reactions.py` at 100%.** 59%.
- **`permissions.py` has 433 mutable sites.** 412.
- **"545 tests."** 557 at the time; 960 now.

---

## 8. Gotchas

- **Assets must be built, or modules skip silently.** A missing `sites/assets/assets.json` makes
  `bundled_asset()` return `None.get(...)`, which makes `test_email_digest` red — and a red baseline
  makes the harness **skip the whole module** (`baseline RED -> skipping module`). It journals a
  `baseline-skip` row and moves on, so the campaign *looks* like it ran. Fix: `bench build --app
  frappe` (~7s). Check for `baseline-skip` rows before trusting any score.
- **A journal key is derived from source only** (`mutant_key`: path, mutator, function, segments,
  ordinal). The test fingerprint added in `2d12798e` handles CI invalidation, but for a one-off
  local re-measure the simplest route is still `--journal <fresh-path>`, then append those rows to
  the main journal — last record wins per key, so the re-run supersedes cleanly. To re-run one
  specific mutant, seed a journal with every row *except* that key and let resume leave it pending.
- **Never `bench migrate` a SQLite site.** `frappe/patches/v16_0/hash_oauth_bearer_tokens.py:51`
  calls `multisql` with no sqlite branch and no `*` fallback, and dies. It never fires on a *fresh*
  site because `installer.py::set_all_patches_as_completed()` marks patches done without running
  them — so always `bench new-site`, never migrate an old one. Not worth fixing upstream: CI creates
  sites fresh.
- **Node must be ≥ 24.** frappe v17-dev's engine check rejects 20, and `--skip-assets` does not skip
  `yarn install --check-files`, so the check still fires during `bench get-app`.
- **Do not edit tests, or any mutation target, while a campaign is running.** The tests are the
  measuring instrument; changing them mid-run makes mutants evaluated before and after
  incomparable. And the restore guard has the *source* files checked out — an edit lands inside its
  window and gets reverted.
- **Watch out for self-matching `pgrep`.** `pgrep -f "bench init"` inside an ssh command matches the
  ssh command's own string and kills your session.
- **String-constant mutation is off by default** (`--mutate-strings`). In this codebase strings are
  field and doctype names; mutating them is pure noise — over half of `permissions.py`'s mutable
  sites are strings.

---

## 9. Check the target map before writing a test

`config.py` maps each target module to the test modules the harness runs against its mutants. A
stale map reports gaps that are not real — nine survivors existed only because the killing test
already existed and was not mapped. That is worse than a low score, because it sends people to write
tests that are already there.

The map is deliberately narrow, and should stay narrow: stage 1 answers "does this module's own
tests pin it?", and widening the map toward the full suite turns stage 1 into stage 2 and makes the
campaign unaffordable. The rule now written into `config.py` is that a test module earns a place
only if it is the *primary or sole* place some behaviour of the target is asserted. Several
candidates were measured and rejected on cost.

Cost is not per-mutant: `run_one_mutant` runs the list in order and returns on the first
non-survivor, so a mapped module is only paid for on mutants that survived everything before it.

## 10. What to do next

1. **Let the nightly run for a week** and check it is actually rotating. The failure mode to watch
   for is a cache that never invalidates, which looks identical to success from the outside.
2. **Triage the remaining survivors**, re-derived from a fresh journal rather than from old counts.
   The largest untouched pockets are `gp_user_profile.get_list` (23) and `get_last_post` (9) —
   nothing calls either — `gp_draft.get_my_drafts` (26), and `email_digest.summarized_names` (18).
3. **Two known clusters that are not test gaps.** ~21 survivors across the corpus are equivalent
   mutants (`return False → None`, `as_dict=1 → 2`, `limit+1 → limit+2`); chasing them buys
   `assertIs` noise and nothing else. And every remaining `gp_project` survivor is an
   `ignore_permissions` flip that **cannot** be killed as written — see §3, "the prediction that
   failed". Record them as equivalent rather than leaving them to look like debt.
4. **Verify strategy.** Full-suite-per-survivor is ~27h and mostly wasted. The cheapest answer in
   practice: when a survivor sits in code nothing else exercises, stage 1 *is* the answer, and
   writing the assertion costs less than proving you needed to. Reach for `verify` only on survivors
   you are about to act on. If a broad number is ever wanted, stratified sampling across modules
   *and* mutator classes beats a full run by an order of magnitude.
5. **Deferred, found along the way, not chased:** `GP Project Visit` has no unique constraint on
   `(user, project)` and `track_visit` is a get-then-insert, so duplicate rows are reachable and
   inflate unread counts (`COUNT DISTINCT` makes the read side robust, but the root cause stands).
   `GPProjectVisit.get_list_query` is dead — its only dispatcher is commented out in `hooks.py`.
   And `gameplan.extends.client.get_list` passes `ignore_permissions=True`, so for doctypes with no
   `get_list_query` nothing scopes that endpoint; worth an audit.

Useful queries against the journal:

```bash
# survivors by module
python3 -c "
import json,collections
rows=[json.loads(l) for l in open('.mutation/journal.jsonl')]
s=[r for r in rows if r['status']=='survived']
print(collections.Counter(r['file'] for r in s).most_common())"

# survivors in one function
python3 -c "
import json
rows=[json.loads(l) for l in open('.mutation/journal.jsonl')]
for r in rows:
    if r['status']=='survived' and r.get('function')=='can_edit_content':
        print(r['line'], r['mutator'], r['original_segment'], '->', r['mutated_segment'])"
```
