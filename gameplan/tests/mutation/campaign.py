"""Campaign orchestration: baseline gate, mutant loop, and the stage-2 verify pass.

Execution is strictly serial. Every worker would mutate the same single source tree,
so any parallelism would have workers overwriting each other's mutants and reporting
verdicts for code that was never actually under test.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from . import journal as journal_mod
from . import mutators, safety, scope
from .config import (
	APP_ROOT,
	BACKUP_DIR,
	JOURNAL_PATH,
	MAX_CONSECUTIVE_NO_VERDICT,
	MODULE_STATUSES,
	NO_VERDICT_STATUSES,
	RETRYABLE_STATUSES,
	STATUS_BASELINE_SKIP,
	STATUS_ERROR,
	STATUS_INCOMPLETE,
	STATUS_INFRA_ERROR,
	STATUS_KILLED,
	STATUS_KILLED_BY_OTHER_SUITE,
	STATUS_KILLED_IMPORT_ERROR,
	STATUS_MODULE_CURRENT,
	STATUS_MODULE_SKIP,
	STATUS_SURVIVED,
	STATUS_TIMEOUT,
	STATUS_UNCONFIRMED,
	VERIFY_PATH,
	target_map,
)
from .runner import RunResult, run_tests

# Exit codes. A nightly job keys off these, so they are part of the interface: a run
# that measured nothing must never share a code with a run that measured everything and
# liked what it saw. See ``_campaign_exit_code``. report.py mirrors these numbers.
EXIT_OK = 0
EXIT_ABORTED = 1
EXIT_USAGE = 2
EXIT_NOTHING_MEASURED = 3
# The wall-clock budget ran out with mutants still pending. A *fourth* outcome on purpose:
# folding it into 0 makes a nightly that is falling behind indistinguishable from one that
# finished the corpus, and folding it into a failure pages a human every single night for
# the design working exactly as intended.
EXIT_BUDGET_EXHAUSTED = 4


def _log(message: str) -> None:
	print(f"[mutation] {message}", flush=True)


def classify(result: RunResult, mutated_file: str | None = None) -> str:
	"""Map a test-run outcome to a mutant status.

	A "killed" status is a claim that the TEST SUITE DETECTED the mutation. Anything
	that did not come from the suite making that judgement resolves to a non-verdict:
	it is an absence of evidence, not evidence of coverage. See the invariant in
	config.py for why that distinction is load-bearing (non-verdicts stay out of the
	score and are retried; kills are cached forever).

	``mutated_file`` is the repo-relative path currently holding the mutant. Without
	it an import failure cannot be attributed to the mutant, so it is not scored.
	"""
	if result.timed_out:
		# Never a kill. A mutant that spun forever and a box that was merely busy (or a
		# site still holding a lock from the previous run) produce identical evidence:
		# a process we killed before it said anything about anything. Telling them
		# apart would need a control re-run costing another full timeout per mutant and
		# would still misjudge a loaded machine. So: no verdict, retry it later.
		return STATUS_TIMEOUT
	if result.passed:
		# Exit 0 with the runner never announcing a result is not a survivor; it is a
		# bench invocation that never reached the suite.
		return STATUS_SURVIVED if result.reached_verdict else STATUS_INFRA_ERROR
	if result.mutant_broke_import(mutated_file):
		return STATUS_KILLED_IMPORT_ERROR
	if result.suite_reported_failure:
		return STATUS_KILLED
	# Non-zero exit and the suite never declared a failure. Tests had started -> it died
	# mid-flight; no tests at all -> it never started. Neither judged the mutant.
	return STATUS_INCOMPLETE if result.tests_ran else STATUS_INFRA_ERROR


def _describe_orphan(manifest: dict) -> None:
	state = safety.orphan_state(manifest)
	_log(f"  {manifest['path']}  [{state}]")
	if state in {"mutated", "unknown"}:
		for line in safety.orphan_diff(manifest).splitlines():
			print(f"      {line}", flush=True)
	if state == "unknown":
		_log("    ^ this file matches neither the pristine backup nor the mutant we wrote.")
		_log("      It has been edited since the crash. Restoring would destroy those edits.")


def check_orphans(assume_yes: bool = False) -> bool:
	"""Handle backups left behind by a hard crash. Returns True if it is safe to proceed."""
	orphans = safety.find_orphaned_backups()
	if not orphans:
		return True
	_log(f"found {len(orphans)} orphaned backup(s) from a previous crashed run:")
	for manifest in orphans:
		_describe_orphan(manifest)
	if any(safety.orphan_state(m) == "unknown" for m in orphans):
		_log("refusing to auto-restore: at least one target has been edited since the crash.")
		_log("resolve it by hand, then re-run.")
		return False
	if not assume_yes:
		if not sys.stdin.isatty():
			_log("refusing to run with orphaned backups present.")
			_log("run 'python -m gameplan.tests.mutation restore' first.")
			return False
		answer = input("[mutation] restore these files now? [y/N] ").strip().lower()
		if answer not in {"y", "yes"}:
			_log("aborting; source files may still contain mutants.")
			return False
	for manifest in orphans:
		try:
			safety.restore_orphan(manifest)
		except safety.RestoreError as exc:
			_log(f"FAILED: {exc}")
			return False
		_log(f"restored {manifest['path']}")
	return True


def restore_command(assume_yes: bool = True) -> int:
	owner = safety.lock_owner()
	if owner is not None and owner != os.getpid():
		_log(f"a mutation run (pid {owner}) is using this working tree right now.")
		_log("its backups are not orphans; restoring them would strand its mutant. aborting.")
		return 1
	orphans = safety.find_orphaned_backups()
	if not orphans:
		_log("no orphaned backups; working tree is clean.")
		return 0
	failures = 0
	for manifest in orphans:
		_describe_orphan(manifest)
		try:
			safety.restore_orphan(manifest)
		except safety.RestoreError as exc:
			failures += 1
			_log(f"FAILED: {exc}")
		else:
			_log(f"restored {manifest['path']}")
	return 1 if failures else 0


def _baseline_ok(site: str, test_modules: list[str], timeout: int) -> tuple[bool, str]:
	"""Run the mapped tests unmutated. Mutation scores against a red baseline are noise."""
	for module in test_modules:
		result = run_tests(site, module, timeout)
		if result.timed_out:
			return False, f"{module} timed out after {timeout}s"
		if not result.passed:
			tail = result.output.strip().splitlines()[-5:]
			return False, f"{module} failed (exit {result.returncode}): {' | '.join(tail)}"
		if result.tests_ran in (0, None):
			return False, f"{module} ran no tests"
	return True, ""


def run_campaign(
	tier: str = "1",
	only_module: str | None = None,
	site: str = "",
	timeout: int = 120,
	limit: int | None = None,
	mutate_strings: bool = False,
	assume_yes: bool = False,
	journal_path: Path | None = None,
	budget_seconds: float | None = None,
	changed_files: list[str] | None = None,
) -> int:
	from .config import DEFAULT_SITE, DEFAULT_TIMEOUT

	site = site or DEFAULT_SITE
	timeout = timeout or DEFAULT_TIMEOUT
	journal_path = journal_path or JOURNAL_PATH

	targets = target_map(tier)
	if only_module and changed_files is not None:
		_log("--module and --changed-files-from both narrow the target set; pass only one.")
		return EXIT_USAGE
	if only_module:
		rel = only_module
		if rel not in targets:
			merged = target_map("all")
			if rel not in merged:
				_log(f"no test mapping for {rel!r}; add it to config.TIER1/TIER2 first.")
				return EXIT_USAGE
			targets = {rel: merged[rel]}
		else:
			targets = {rel: targets[rel]}
	if changed_files is not None:
		targets = scope.changed_targets(changed_files, targets)
		if not targets:
			# Not a failure and not a silent pass: there is genuinely nothing in this diff
			# that this harness can measure. Returning before the lock keeps the common
			# frontend-only pull request fast.
			_log(f"none of the {len(changed_files)} changed file(s) map to a mutation target.")
			_log("nothing to measure.")
			return EXIT_OK
		_log(f"diff-scoped to {len(targets)} target(s): {', '.join(targets)}")

	# Started here rather than inside the lock so setup done on our behalf - orphan
	# recovery, the git cleanliness check - is spent from the same allowance. A budget the
	# clock only starts on the first mutant is not a wall-clock budget.
	budget = scope.Budget(budget_seconds)
	if budget_seconds is not None:
		_log(f"budget: {budget_seconds:g}s of mutation work")

	try:
		lock = safety.CampaignLock()
		lock.acquire()
	except safety.LockError as exc:
		_log(f"refusing to run: {exc}")
		return 1

	try:
		return _run_campaign_locked(
			targets=targets,
			site=site,
			timeout=timeout,
			limit=limit,
			mutate_strings=mutate_strings,
			assume_yes=assume_yes,
			journal_path=journal_path,
			budget=budget,
		)
	finally:
		lock.release()


def _guard_for(abs_path: Path) -> safety.FileGuard:
	"""FileGuard for one target, with any crashed run's leftover mutant already undone.

	``install_backup`` is the only thing that recovers the original from an existing
	sidecar backup, so it must run before anything else looks at the file. Reading the
	source or running the baseline first would measure the previous run's mutant, and a
	module with nothing pending would return without ever calling it - leaving the mutant
	on disk for the rest of the campaign and for whoever next opens the file.
	"""
	guard = safety.FileGuard(abs_path)
	guard.install_backup()
	return guard


def _module_record(rel_path: str, status: str, reason: str, tests_sha: str) -> dict:
	"""A journal record about a MODULE rather than a mutant, keyed "baseline:<path>".

	Two things are said with it, and the second exists only to retract the first:

	A SKIP says "this module produced no measurement, and here is why". Every path that
	drops a module has to leave one. The report's only way to notice a module that fell out
	of the corpus is the journal, so a skip that only ever reached stdout is a module that
	goes quietly unmeasured for ever while its stale verdicts keep counting toward the
	published score.

	STATUS_MODULE_CURRENT says "this module has a current score". It is written whenever a
	run establishes that, and it is the only thing that can retire a skip.

	The key is FIXED per module and identical for both, so the journal's last-wins merge
	leaves exactly one of them and it is authoritative. That is the whole design: currency
	is a fact recorded under the key it supersedes, not something the reader infers from
	how far down the file a mutant record happens to sit. See STATUS_MODULE_CURRENT.
	"""
	return {
		"key": f"baseline:{rel_path}",
		"module": rel_path,
		"file": rel_path,
		"line": 0,
		"col": 0,
		"function": "",
		"mutator": "",
		"original_segment": "",
		"mutated_segment": "",
		"status": status,
		"duration_s": 0.0,
		"killed_by_test_module": None,
		"tests_sha": tests_sha,
		"reason": reason,
	}


def _campaign_exit_code(
	targeted: int,
	skipped: int,
	pending: int,
	evaluated: int,
	aborted: bool,
	limit: int | None = None,
	budget_stopped: bool = False,
	budget_seconds: float | None = None,
) -> int:
	"""Exit code for a finished campaign.

	Success has to mean "we measured what we set out to measure", not merely "nothing
	raised". A nightly whose site is down skips every module and evaluates nothing, which
	to any caller checking for exit 0 is indistinguishable from a clean sweep. So the two
	ways of ending with an empty scoreboard get different codes: having nothing to do
	because every mutant is already journalled is a real success, while measuring nothing
	because the environment is broken is a failure.

	The order of the checks is the contract, strongest evidence of breakage first:

	1. an abort outranks everything - the circuit breaker fired, nothing else is credible;
	2. then "measured nothing", including when the budget is what stopped us. A run that
	burned its whole allowance without landing a single verdict is a broken site, not a
	budget working as designed, and it must page someone rather than report "stopped early,
	resuming tomorrow" for a week;
	3. then the budget - work remains, but real work was done;
	4. otherwise success.

	Note the shape of rule 2: it fires on ``budget_stopped`` even when ``pending`` is 0.
	``pending`` only counts modules the loop actually reached, so a budget that expired
	before the FIRST module was inspected reports 0 pending and would otherwise slip
	through as "stopped on budget, resuming tomorrow" - green, for ever, having run no
	tests at all.
	"""
	if aborted:
		return EXIT_ABORTED
	if targeted and skipped == targeted:
		return EXIT_NOTHING_MEASURED
	# ``--limit 0`` and ``--budget-seconds 0`` are explicit requests to evaluate nothing,
	# so neither is a failure.
	if (pending or budget_stopped) and not evaluated and limit != 0 and budget_seconds != 0:
		return EXIT_NOTHING_MEASURED
	if budget_stopped:
		return EXIT_BUDGET_EXHAUSTED
	return EXIT_OK


def _run_campaign_locked(
	targets: dict[str, list[str]],
	site: str,
	timeout: int,
	limit: int | None,
	mutate_strings: bool,
	assume_yes: bool,
	journal_path: Path,
	budget: scope.Budget | None = None,
) -> int:
	budget = budget or scope.Budget(None)
	if not check_orphans(assume_yes=assume_yes):
		return 1

	# Pre-flight: a dirty file means a hard crash could not be undone with git.
	clean, dirty = safety.git_is_clean(list(targets))
	if not clean:
		_log("refusing to run: these target files have uncommitted changes:")
		for rel in dirty:
			_log(f"  {rel}")
		_log("commit or stash them so a crash is always recoverable via 'git checkout --'.")
		return 1

	safety.install_handlers()
	BACKUP_DIR.mkdir(parents=True, exist_ok=True)

	# What each module's verdicts were produced BY. A verdict is only settled while the
	# tests that produced it are unchanged; see scope.test_fingerprint for the reasoning
	# and for the cost this deliberately accepts.
	fingerprints = {rel: scope.test_fingerprint(tests, APP_ROOT) for rel, tests in targets.items()}
	done = journal_mod.completed_keys(
		journal_path, exclude_statuses=RETRYABLE_STATUSES, fingerprints=fingerprints
	)
	# Least-recently-measured first. Only matters under a budget, where the tail of the
	# list never gets reached - see scope.round_robin_order. NO module-level record counts
	# as a measurement: a skip would sort the module the gate wants re-measured last, and a
	# "score is current" record written just before the budget expired would do the same to
	# a module whose mutants never ran.
	order = scope.round_robin_order(
		list(targets),
		scope.last_measured_positions(
			journal_mod.read_records(journal_path), ignore_statuses=MODULE_STATUSES
		),
	)
	evaluated = 0
	pending_total = 0
	# (module, reason) for every module that produced no measurement, so the tail of the
	# run can name them instead of printing a count nobody can act on.
	skipped: list[tuple[str, str]] = []
	consecutive_no_verdict = 0
	aborted = False
	budget_stopped = False

	with journal_mod.Journal(journal_path) as journal:
		for rel_path in order:
			test_modules = targets[rel_path]
			if budget.expired:
				# Checked before the module rather than only before each mutant: a
				# baseline pass is several minutes of test runs, and starting one with no
				# allowance left overruns the budget by more than a mutant would.
				_log(f"budget exhausted ({budget.describe()}); stopping before {rel_path}")
				budget_stopped = True
				break
			abs_path = APP_ROOT / rel_path
			if not abs_path.exists():
				reason = f"{rel_path} does not exist (renamed or deleted without updating config.py)"
				_log(f"skipping missing file {rel_path}")
				skipped.append((rel_path, reason))
				journal.append(_module_record(rel_path, STATUS_MODULE_SKIP, reason, fingerprints[rel_path]))
				continue

			_log(f"=== {rel_path} ===")
			try:
				guard = _guard_for(abs_path)
			except (safety.LockError, safety.RestoreError, OSError) as exc:
				_log(f"skipping {rel_path}: {exc}")
				reason = f"could not take a restorable backup: {exc}"
				skipped.append((rel_path, reason))
				journal.append(_module_record(rel_path, STATUS_MODULE_SKIP, reason, fingerprints[rel_path]))
				continue

			safety.register(guard)
			try:
				# Read the source through the guard, after _guard_for has had its chance to
				# undo a crashed run's leftover mutant. Sites collected from mutated source
				# get content-derived keys that match nothing on a clean tree, so every
				# mutant would be re-evaluated under a key the journal can never resume.
				sites = mutators.collect_sites(guard.source, rel_path, mutate_strings=mutate_strings)
				pending = [s for s in sites if s.key not in done]
				pending_total += len(pending)
				_log(f"{len(sites)} mutant(s), {len(sites) - len(pending)} already journaled")

				# Before the baseline, not after: the baseline exists to make this module's
				# verdicts trustworthy, and a module with no pending mutant produces none.
				# Paying for its test modules anyway is what turns a budgeted nightly into a
				# run that spends most of its allowance re-proving settled work - the whole
				# corpus is ~17 bench invocations of baseline before a single mutation.
				if not pending:
					# Settled, and that has to be SAID: every mutant of this module has a
					# verdict produced by the tests exactly as they are now. Without this
					# record a module that was skipped once and then has nothing pending
					# never runs a baseline again, so nothing can ever clear the skip and
					# the gate stays red for ever - the self-sustaining failure this
					# record exists to make impossible.
					journal.append(
						_module_record(
							rel_path,
							STATUS_MODULE_CURRENT,
							f"all {len(sites)} mutant(s) already settled against the current tests",
							fingerprints[rel_path],
						)
					)
					continue

				_log(f"baseline: {len(test_modules)} test module(s)...")
				ok, reason = _baseline_ok(site, test_modules, timeout)
				if not ok:
					_log(f"baseline RED -> skipping module. {reason}")
					skipped.append((rel_path, f"red baseline: {reason}"))
					journal.append(
						_module_record(rel_path, STATUS_BASELINE_SKIP, reason, fingerprints[rel_path])
					)
					continue
				_log("baseline GREEN")
				# Journalled here, before the mutants rather than after them: this is the
				# record that retires any earlier skip, and it has to survive the run being
				# cut short by the budget, the circuit breaker or a hard kill - which is
				# precisely when a stale skip would otherwise outlive its cause.
				journal.append(
					_module_record(
						rel_path,
						STATUS_MODULE_CURRENT,
						f"baseline green; measuring {len(pending)} pending mutant(s)",
						fingerprints[rel_path],
					)
				)

				for site_obj in pending:
					if limit is not None and evaluated >= limit:
						_log(f"limit of {limit} mutants reached")
						break
					if budget.expired:
						# Between mutants, with the file already restored by the previous
						# iteration's guard.restore(). This is the only place the budget may
						# stop the loop: a check inside _evaluate_mutant would abandon a
						# mutated source file on disk, which is the one failure this harness
						# exists to make impossible.
						_log(f"budget exhausted ({budget.describe()}); stopping cleanly")
						budget_stopped = True
						break
					built = mutators.build_mutant(
						guard.source, site_obj.node_index, site_obj.mutator, site_obj.param
					)
					if built is None:
						continue
					mutated_source, _ = built

					status, killed_by, duration = _evaluate_mutant(
						guard, mutated_source, site, test_modules, timeout, rel_path
					)
					evaluated += 1
					record = site_obj.to_dict()
					record.update(
						{
							"module": rel_path,
							"status": status,
							"duration_s": duration,
							"killed_by_test_module": killed_by,
							# The provenance of this verdict: which test files, at which
							# bytes, produced it. Change them and it stops being settled.
							"tests_sha": fingerprints[rel_path],
						}
					)
					journal.append(record)
					_log(
						f"  L{site_obj.line} {site_obj.mutator}: "
						f"{site_obj.original_segment} -> {site_obj.mutated_segment} = {status} "
						f"({duration}s)"
					)

					# Every non-verdict trips the breaker, not just infra-error: a wedged
					# site shows up as a run of timeouts just as readily as a run of
					# failures to start, and both mean the campaign has stopped
					# measuring anything.
					if status in NO_VERDICT_STATUSES:
						consecutive_no_verdict += 1
						if consecutive_no_verdict >= MAX_CONSECUTIVE_NO_VERDICT:
							_log(
								f"{consecutive_no_verdict} consecutive runs produced no verdict "
								f"(timeouts? locked site? bench broken?). "
								f"Aborting instead of scoring noise."
							)
							aborted = True
							break
					else:
						consecutive_no_verdict = 0
			finally:
				# try/finally is the first line of defence; atexit and the signal
				# handlers cover the paths this cannot reach. It also guarantees that the
				# recovery done by _guard_for is committed even for a module that turned
				# out to have nothing pending.
				guard.release()
				safety.unregister(guard)

			if aborted or budget_stopped or (limit is not None and evaluated >= limit):
				break

	_log(f"done. evaluated {evaluated} mutant(s). journal: {journal_path}")
	code = _campaign_exit_code(
		targeted=len(targets),
		skipped=len(skipped),
		pending=pending_total,
		evaluated=evaluated,
		aborted=aborted,
		limit=limit,
		budget_stopped=budget_stopped,
		budget_seconds=budget.seconds,
	)
	if code == EXIT_BUDGET_EXHAUSTED:
		_log(
			f"STOPPED ON BUDGET: {evaluated} mutant(s) evaluated, work remains. This is not a "
			f"failure - the journal is the resume point and the next run continues from here."
		)
	if code == EXIT_NOTHING_MEASURED:
		_log(
			f"NOTHING MEASURED: {len(skipped)} of {len(targets)} target module(s) were "
			f"skipped and no mutant was evaluated. Reporting failure - a green exit here "
			f"would claim a passing campaign for a run that measured nothing."
		)
	if skipped:
		_log(f"WARNING: {len(skipped)} of {len(targets)} target module(s) were skipped:")
		for rel_path, reason in skipped:
			_log(f"  {rel_path}: {reason}")
	return code


def _evaluate_mutant(
	guard: safety.FileGuard,
	mutated_source: str,
	site: str,
	test_modules: list[str],
	timeout: int,
	rel_path: str,
) -> tuple[str, str | None, float]:
	"""Apply one mutant, run its mapped tests in sequence, restore, and classify."""
	started = time.monotonic()
	try:
		# Inside the try so the restore in `finally` covers a failure during apply too.
		guard.apply(mutated_source)
		for module in test_modules:
			result = run_tests(site, module, timeout)
			status = classify(result, rel_path)
			if status != STATUS_SURVIVED:
				# Only a real kill names a killing module. Attributing a non-verdict to
				# a test module reads as coverage in the journal when it is the exact
				# opposite: that module's run never judged anything.
				blamed = module if status not in NO_VERDICT_STATUSES else None
				return status, blamed, round(time.monotonic() - started, 2)
		return STATUS_SURVIVED, None, round(time.monotonic() - started, 2)
	except Exception as exc:  # noqa: BLE001 - one bad mutant must not end the campaign
		_log(f"  error while evaluating mutant: {exc}")
		return STATUS_ERROR, None, round(time.monotonic() - started, 2)
	finally:
		guard.restore()


def _control_ok(site: str, timeout: int) -> tuple[bool, str, RunResult]:
	"""Run the FULL suite unmutated. Returns (healthy, reason-if-not, result).

	"Healthy" means the suite ran to completion and passed, so any failure seen with a
	mutant applied can be attributed to the mutant rather than to the suite.
	"""
	result = run_tests(site, None, timeout)
	if result.timed_out:
		return False, f"control run timed out after {timeout}s (raise --timeout)", result
	if not result.passed:
		tail = " | ".join(result.output.strip().splitlines()[-5:])
		return False, f"control run is RED (exit {result.returncode}): {tail}", result
	if not result.reached_verdict or result.tests_ran in (0, None):
		return False, "control run never reported a result", result
	return True, "", result


def verify(
	journal_path: Path | None = None,
	verify_path: Path | None = None,
	site: str = "",
	timeout: int = 0,
	limit: int | None = None,
	assume_yes: bool = False,
) -> int:
	"""Stage 2: re-run every survivor against the FULL suite.

	Stage 1 only runs a module's own tests, so a "survivor" may in fact be caught by
	some other module's tests. This separates genuinely untested behaviour from
	merely mis-mapped coverage.
	"""
	from .config import DEFAULT_SITE, DEFAULT_TIMEOUT

	journal_path = journal_path or JOURNAL_PATH
	verify_path = verify_path or VERIFY_PATH
	site = site or DEFAULT_SITE
	explicit_timeout = timeout
	# The whole suite is far slower than one module.
	control_timeout = explicit_timeout or DEFAULT_TIMEOUT * 10

	journalled = journal_mod.latest_by_key(journal_path).values()
	records = [r for r in journalled if r.get("status") == STATUS_SURVIVED]
	if not records:
		_log("no survivors to verify.")
		return 0

	aborted = False
	try:
		lock = safety.CampaignLock()
		lock.acquire()
	except safety.LockError as exc:
		_log(f"refusing to run: {exc}")
		return 1

	try:
		if not check_orphans(assume_yes=assume_yes):
			return 1

		files = sorted({r["file"] for r in records})
		clean, dirty = safety.git_is_clean(files)
		if not clean:
			_log(f"refusing to run: uncommitted changes in {', '.join(dirty)}")
			return 1

		safety.install_handlers()

		# Control run. Without it, a full suite that is red or slow for reasons that have
		# nothing to do with mutation marks every survivor as killed-by-other-suite, and
		# those verdicts supersede stage 1 in the report - producing exactly the
		# "100%, no survivors" result the campaign exists to disprove.
		_log("control: running the FULL suite unmutated...")
		healthy, reason, control = _control_ok(site, control_timeout)
		if not healthy:
			_log(f"{reason}. aborting.")
			_log("fix the suite first; every survivor would be scored against a red baseline.")
			return 1
		# Derive the per-mutant budget from what the suite actually costs rather than a
		# fixed multiple of the per-module default.
		timeout = explicit_timeout or max(int(control.duration_s * 2) + 30, DEFAULT_TIMEOUT)
		_log(
			f"control GREEN: {control.tests_ran} tests in {control.duration_s}s; "
			f"per-mutant timeout {timeout}s"
		)

		already = journal_mod.completed_keys(verify_path, exclude_statuses=RETRYABLE_STATUSES)
		pending = [r for r in records if r["key"] not in already]
		_log(f"{len(records)} survivor(s), {len(pending)} to verify against the full suite")

		count = 0
		consecutive_no_verdict = 0
		sites_cache: dict[tuple[str, str], dict[str, mutators.MutationSite]] = {}
		with journal_mod.Journal(verify_path) as out:
			for record in pending:
				if limit is not None and count >= limit:
					break
				try:
					status = _verify_one(record, site, timeout, sites_cache, out)
				except safety.RestoreError as exc:
					# NOT isolated like the rest. The working tree still holds this
					# mutant: every later survivor would be measured against doubly
					# mutated source, and the next FileGuard for this file would
					# overwrite the pristine backup with the mutant, destroying the
					# only copy that can undo it.
					_log(f"CRITICAL: could not restore {record['file']}: {exc}")
					_log("the working tree is still mutated. Aborting the verify stage.")
					_log("run 'python -m gameplan.tests.mutation restore' before anything else.")
					aborted = True
					break
				except Exception as exc:  # noqa: BLE001 - isolate one bad survivor
					_log(f"  error while verifying {record['key'][:12]}: {exc}")
					failed = dict(record)
					failed.update(
						{
							"status": STATUS_ERROR,
							"stage1_status": record.get("status"),
							"reason": str(exc),
							"killed_by_test_module": None,
						}
					)
					out.append(failed)
					status = STATUS_ERROR
				if status is None:
					continue
				count += 1
				# Same breaker as stage 1. A verify pass is far longer than a campaign,
				# so a suite that degrades halfway through has plenty of time to
				# reclassify every remaining survivor if nothing stops it.
				if status in NO_VERDICT_STATUSES:
					consecutive_no_verdict += 1
					if consecutive_no_verdict >= MAX_CONSECUTIVE_NO_VERDICT:
						_log(
							f"{consecutive_no_verdict} consecutive survivors produced no "
							f"verdict. The suite or the site is unhealthy; aborting."
						)
						aborted = True
						break
				else:
					consecutive_no_verdict = 0
	finally:
		lock.release()

	_log(f"verify done. results: {verify_path}")
	return 1 if aborted else 0


def _verify_sites(
	rel_path: str,
	guard: safety.FileGuard,
	cache: dict[tuple[str, str], dict[str, mutators.MutationSite]],
) -> dict[str, mutators.MutationSite]:
	"""Mutation sites of one file, keyed by mutant key, cached per (file, content sha)."""
	cache_key = (rel_path, guard.original_sha)
	if cache_key not in cache:
		# mutate_strings=True so the lookup covers campaigns that were run with it; the
		# extra sites do not shift any other site's key.
		sites = mutators.collect_sites(guard.source, rel_path, mutate_strings=True)
		cache[cache_key] = {s.key: s for s in sites}
	return cache[cache_key]


def _verify_one(
	record: dict,
	site: str,
	timeout: int,
	sites_cache: dict[tuple[str, str], dict[str, mutators.MutationSite]],
	out: journal_mod.Journal,
) -> str | None:
	"""Re-apply one survivor against the full suite.

	Returns the status journalled for it, or None if the mutant was skipped without
	being evaluated. Lets ``safety.RestoreError`` escape: the caller must treat a
	working tree it could not clean as fatal, never as one bad survivor.
	"""
	abs_path = APP_ROOT / record["file"]
	if not abs_path.exists():
		_log(f"  skipping {record['key'][:12]}: {record['file']} no longer exists")
		return None

	guard = safety.FileGuard(abs_path)
	# Re-derive the site from the current source by its content-based key. The journalled
	# node_index is an index into list(ast.walk(tree)) and shifts whenever the file is
	# edited; build_mutant only type-checks the node, so a shifted index silently mutates
	# a *different* site and the verdict gets filed under this record's key.
	site_obj = _verify_sites(record["file"], guard, sites_cache).get(record["key"])
	if site_obj is None:
		_log(f"  skipping stale mutant {record['key'][:12]} (site no longer exists in {record['file']})")
		return None

	built = mutators.build_mutant(guard.source, site_obj.node_index, site_obj.mutator, site_obj.param)
	if built is None:
		_log(f"  skipping stale mutant {record['key'][:12]} (no longer produces a mutant)")
		return None
	mutated_source, mutated_segment = built
	if record.get("mutated_segment") and mutated_segment != record["mutated_segment"]:
		# Belt and braces: the key matched but the rendered mutation did not.
		_log(
			f"  skipping {record['key'][:12]}: rebuilt mutation {mutated_segment!r} "
			f"!= journalled {record['mutated_segment']!r}"
		)
		return None

	guard.install_backup()
	safety.register(guard)
	started = time.monotonic()
	try:
		guard.apply(mutated_source)
		result = run_tests(site, None, timeout)
		status = classify(result, record["file"])
	finally:
		# Restores first, so the control re-run below measures a pristine tree. If the
		# restore fails this raises out of _verify_one on purpose.
		guard.release()
		safety.unregister(guard)

	if status == STATUS_SURVIVED or status in NO_VERDICT_STATUSES:
		final = status
	else:
		# The full suite claims to kill a mutant that its own module's tests missed, and
		# that verdict permanently supersedes stage 1 in the report. One --failfast run
		# over 500+ tests is not enough evidence: a flaky test, data leaked by an earlier
		# mutant, or a site that degraded mid-pass all look exactly like this. Confirm
		# the suite is still green without the mutant before believing it.
		_log(f"  {record['key'][:12]} looks killed by the full suite; confirming with a control run")
		healthy, reason, _control = _control_ok(site, timeout)
		if healthy:
			final = STATUS_KILLED_BY_OTHER_SUITE
		else:
			_log(f"  control re-run unhealthy: {reason}")
			_log("  the suite, not the mutant, is the variable. Recording no verdict.")
			final = STATUS_UNCONFIRMED

	new_record = dict(record)
	new_record.update(
		{
			"status": final,
			"stage1_status": record["status"],
			"line": site_obj.line,
			"col": site_obj.col,
			"node_index": site_obj.node_index,
			"duration_s": round(time.monotonic() - started, 2),
			"killed_by_test_module": "<full-suite>" if final == STATUS_KILLED_BY_OTHER_SUITE else None,
		}
	)
	out.append(new_record)
	_log(f"  L{site_obj.line} {record['mutator']}: {final}")
	return final
