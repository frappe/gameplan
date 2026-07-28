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
from . import mutators, safety
from .config import (
	APP_ROOT,
	BACKUP_DIR,
	JOURNAL_PATH,
	MAX_CONSECUTIVE_INFRA_ERRORS,
	RETRYABLE_STATUSES,
	STATUS_BASELINE_SKIP,
	STATUS_ERROR,
	STATUS_INFRA_ERROR,
	STATUS_KILLED,
	STATUS_KILLED_BY_OTHER_SUITE,
	STATUS_KILLED_IMPORT_ERROR,
	STATUS_KILLED_TIMEOUT,
	STATUS_SURVIVED,
	VERIFY_PATH,
	target_map,
)
from .runner import RunResult, run_tests


def _log(message: str) -> None:
	print(f"[mutation] {message}", flush=True)


def classify(result: RunResult) -> str:
	"""Map a test-run outcome to a mutant status."""
	if result.timed_out:
		return STATUS_KILLED_TIMEOUT
	if result.passed:
		return STATUS_SURVIVED
	# Non-zero, but a broken import is a much weaker signal than a caught assertion.
	if result.looks_like_import_error:
		return STATUS_KILLED_IMPORT_ERROR
	# Non-zero with no tests run and nothing pointing at the mutant: the suite never
	# happened. Not a verdict, so it is neither killed nor survived.
	if result.looks_like_infra_error:
		return STATUS_INFRA_ERROR
	return STATUS_KILLED


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
) -> int:
	from .config import DEFAULT_SITE, DEFAULT_TIMEOUT

	site = site or DEFAULT_SITE
	timeout = timeout or DEFAULT_TIMEOUT
	journal_path = journal_path or JOURNAL_PATH

	targets = target_map(tier)
	if only_module:
		rel = only_module
		if rel not in targets:
			merged = target_map("all")
			if rel not in merged:
				_log(f"no test mapping for {rel!r}; add it to config.TIER1/TIER2 first.")
				return 2
			targets = {rel: merged[rel]}
		else:
			targets = {rel: targets[rel]}

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
		)
	finally:
		lock.release()


def _run_campaign_locked(
	targets: dict[str, list[str]],
	site: str,
	timeout: int,
	limit: int | None,
	mutate_strings: bool,
	assume_yes: bool,
	journal_path: Path,
) -> int:
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

	done = journal_mod.completed_keys(journal_path, exclude_statuses=RETRYABLE_STATUSES)
	evaluated = 0
	consecutive_infra = 0
	aborted = False

	with journal_mod.Journal(journal_path) as journal:
		for rel_path, test_modules in targets.items():
			abs_path = APP_ROOT / rel_path
			if not abs_path.exists():
				_log(f"skipping missing file {rel_path}")
				continue

			_log(f"=== {rel_path} ===")
			_log(f"baseline: {len(test_modules)} test module(s)...")
			ok, reason = _baseline_ok(site, test_modules, timeout)
			if not ok:
				_log(f"baseline RED -> skipping module. {reason}")
				journal.append(
					{
						"key": f"baseline:{rel_path}",
						"module": rel_path,
						"file": rel_path,
						"line": 0,
						"col": 0,
						"function": "",
						"mutator": "",
						"original_segment": "",
						"mutated_segment": "",
						"status": STATUS_BASELINE_SKIP,
						"duration_s": 0.0,
						"killed_by_test_module": None,
						"reason": reason,
					}
				)
				continue
			_log("baseline GREEN")

			guard = safety.FileGuard(abs_path)
			sites = mutators.collect_sites(guard.source, rel_path, mutate_strings=mutate_strings)
			pending = [s for s in sites if s.key not in done]
			_log(f"{len(sites)} mutant(s), {len(sites) - len(pending)} already journaled")

			if not pending:
				continue

			guard.install_backup()
			safety.register(guard)
			try:
				for site_obj in pending:
					if limit is not None and evaluated >= limit:
						_log(f"limit of {limit} mutants reached")
						break
					built = mutators.build_mutant(
						guard.source, site_obj.node_index, site_obj.mutator, site_obj.param
					)
					if built is None:
						continue
					mutated_source, _ = built

					status, killed_by, duration = _evaluate_mutant(
						guard, mutated_source, site, test_modules, timeout
					)
					evaluated += 1
					record = site_obj.to_dict()
					record.update(
						{
							"module": rel_path,
							"status": status,
							"duration_s": duration,
							"killed_by_test_module": killed_by,
						}
					)
					journal.append(record)
					_log(
						f"  L{site_obj.line} {site_obj.mutator}: "
						f"{site_obj.original_segment} -> {site_obj.mutated_segment} = {status} "
						f"({duration}s)"
					)

					if status == STATUS_INFRA_ERROR:
						consecutive_infra += 1
						if consecutive_infra >= MAX_CONSECUTIVE_INFRA_ERRORS:
							_log(
								f"{consecutive_infra} consecutive runs never executed a test "
								f"(locked site? bench broken?). Aborting instead of scoring noise."
							)
							aborted = True
							break
					else:
						consecutive_infra = 0
			finally:
				# try/finally is the first line of defence; atexit and the signal
				# handlers cover the paths this cannot reach.
				guard.release()
				safety.unregister(guard)

			if aborted or (limit is not None and evaluated >= limit):
				break

	_log(f"done. evaluated {evaluated} mutant(s). journal: {journal_path}")
	return 1 if aborted else 0


def _evaluate_mutant(
	guard: safety.FileGuard,
	mutated_source: str,
	site: str,
	test_modules: list[str],
	timeout: int,
) -> tuple[str, str | None, float]:
	"""Apply one mutant, run its mapped tests in sequence, restore, and classify."""
	started = time.monotonic()
	try:
		# Inside the try so the restore in `finally` covers a failure during apply too.
		guard.apply(mutated_source)
		for module in test_modules:
			result = run_tests(site, module, timeout)
			status = classify(result)
			if status != STATUS_SURVIVED:
				return status, module, round(time.monotonic() - started, 2)
		return STATUS_SURVIVED, None, round(time.monotonic() - started, 2)
	except Exception as exc:  # noqa: BLE001 - one bad mutant must not end the campaign
		_log(f"  error while evaluating mutant: {exc}")
		return STATUS_ERROR, None, round(time.monotonic() - started, 2)
	finally:
		guard.restore()


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
		# nothing to do with mutation marks every survivor as killed-by-other-suite (or
		# killed-timeout), and those verdicts supersede stage 1 in the report - producing
		# exactly the "100%, no survivors" result the campaign exists to disprove.
		_log("control: running the FULL suite unmutated...")
		control = run_tests(site, None, control_timeout)
		if control.timed_out:
			_log(f"control run timed out after {control_timeout}s. Raise --timeout. aborting.")
			return 1
		if not control.passed:
			tail = " | ".join(control.output.strip().splitlines()[-5:])
			_log(f"control run is RED (exit {control.returncode}): {tail}")
			_log("fix the suite first; every survivor would be scored against a red baseline.")
			return 1
		if control.tests_ran in (0, None):
			_log("control run reported no tests. aborting.")
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
		sites_cache: dict[tuple[str, str], dict[str, mutators.MutationSite]] = {}
		with journal_mod.Journal(verify_path) as out:
			for record in pending:
				if limit is not None and count >= limit:
					break
				# One bad survivor must not end the stage, exactly as in stage 1.
				try:
					done = _verify_one(record, site, timeout, sites_cache, out)
				except Exception as exc:  # noqa: BLE001 - isolate per survivor
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
					done = False
				if done:
					count += 1
	finally:
		lock.release()

	_log(f"verify done. results: {verify_path}")
	return 0


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
) -> bool:
	"""Re-apply one survivor against the full suite. Returns True if it was evaluated."""
	abs_path = APP_ROOT / record["file"]
	if not abs_path.exists():
		_log(f"  skipping {record['key'][:12]}: {record['file']} no longer exists")
		return False

	guard = safety.FileGuard(abs_path)
	# Re-derive the site from the current source by its content-based key. The journalled
	# node_index is an index into list(ast.walk(tree)) and shifts whenever the file is
	# edited; build_mutant only type-checks the node, so a shifted index silently mutates
	# a *different* site and the verdict gets filed under this record's key.
	site_obj = _verify_sites(record["file"], guard, sites_cache).get(record["key"])
	if site_obj is None:
		_log(f"  skipping stale mutant {record['key'][:12]} (site no longer exists in {record['file']})")
		return False

	built = mutators.build_mutant(guard.source, site_obj.node_index, site_obj.mutator, site_obj.param)
	if built is None:
		_log(f"  skipping stale mutant {record['key'][:12]} (no longer produces a mutant)")
		return False
	mutated_source, mutated_segment = built
	if record.get("mutated_segment") and mutated_segment != record["mutated_segment"]:
		# Belt and braces: the key matched but the rendered mutation did not.
		_log(
			f"  skipping {record['key'][:12]}: rebuilt mutation {mutated_segment!r} "
			f"!= journalled {record['mutated_segment']!r}"
		)
		return False

	guard.install_backup()
	safety.register(guard)
	started = time.monotonic()
	try:
		guard.apply(mutated_source)
		result = run_tests(site, None, timeout)
		status = classify(result)
		if status == STATUS_SURVIVED:
			final = STATUS_SURVIVED
		elif status in {STATUS_KILLED_TIMEOUT, STATUS_INFRA_ERROR}:
			final = status
		else:
			final = STATUS_KILLED_BY_OTHER_SUITE
	finally:
		guard.release()
		safety.unregister(guard)

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
	return True
