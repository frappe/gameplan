"""Mutation score and survivor report rendering.

THE RULE THIS FILE EXISTS TO ENFORCE
------------------------------------
The report is the only artefact a human reads, so it must never present an ABSENCE of
evidence as a result. "We could not measure this" and "we measured 0%" are different
claims and must look different: a module whose mutants all timed out or died on infra
has no score at all (``None`` -> rendered "n/a"), never a fabricated 0%. Every mutant
without a verdict is excluded from both sides of the ratio and surfaced as an explicit
count, so a run degraded by infrastructure problems reads as degraded rather than as a
flattering low-denominator score.

THE SECOND RULE: CURRENCY IS DATA, NEVER POSITION
-------------------------------------------------
"This module has no current score" is a claim about NOW, and it is reported if and only if
the module's own latest module-level record says so - whatever filtering a caller applies
(``--new-since``, ``--prune-stale``). It is never inferred from where records sit relative
to each other, because every caller here is free to remove records: a filter that keeps
skips and drops the measurements that retired them turns a dead skip into a live one, and
a fixed-key skip that nothing can retire is red for ever, in every pull request, for a
module nobody touched. :func:`load_results` settles currency once, against the complete
journal, and everything downstream only reads the answer.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Collection, Mapping
from pathlib import Path

from . import journal as journal_mod
from .config import (
	APP_ROOT,
	JOURNAL_PATH,
	KILLED_STATUSES,
	MODULE_STATUSES,
	NON_SCORING_STATUSES,
	SKIP_STATUSES,
	STATUS_BASELINE_SKIP,
	STATUS_SURVIVED,
	VERIFY_PATH,
)

# Exit codes, mirroring campaign.py so a nightly can key off both the same way.
# "We could not measure this" is a third outcome, not a flavour of pass or fail: a gate
# that collapses it into either one reports a healthy suite for a run that never
# happened, or blames the tests for a broken site.
EXIT_OK = 0
EXIT_BELOW_THRESHOLD = 1
EXIT_NOTHING_MEASURED = 3
# The result set held no mutant verdict at all - either it was empty, or it contained only
# module-level statements. Nothing was attempted, so there is nothing to be degraded about.
# Distinct from 3 because the two license opposite statements: 3 means "we tried to measure
# and got no verdict" (a degraded signal that must not be reported as a clean bill of
# health), while 5 means "there was nothing new here", the expected, benign outcome of a
# pull-request run whose mutants were all already settled by the nightly. A caller that
# collapses them prints a claim about the code for a run whose measurement broke - or, in
# the other direction, calls a quiet night a degraded one because one skip record was in
# scope.
EXIT_NOTHING_TO_REPORT = 5


def _notice(message: str) -> None:
	"""Progress chatter for a human, on stderr.

	stdout is the report itself and is piped into ``$GITHUB_STEP_SUMMARY`` and into
	``json.load``, so a stray line there is either noise in the summary or a parse error.
	"""
	print(f"[mutation] {message}", file=sys.stderr, flush=True)


def verify_path_for(journal_path: Path) -> Path:
	"""Stage-2 journal belonging to ``journal_path``.

	Mutant keys are content hashes, so they collide across journals: merging the live
	``.mutation/verify.jsonl`` into a report over an archived or alternate journal would
	convert that campaign's survivors into kills using another campaign's verdicts. Each
	journal therefore gets its own stage-2 sibling, and only the default journal keeps
	the historical ``verify.jsonl`` name.
	"""
	if journal_path.resolve() == JOURNAL_PATH.resolve():
		return VERIFY_PATH
	return journal_path.with_name(f"{journal_path.stem}.verify{journal_path.suffix}")


def module_of(record: Mapping[str, object]) -> str:
	"""Which module a record is about. ``file`` is the pre-``module`` spelling."""
	module = record.get("module") or record.get("file")
	return module if isinstance(module, str) and module else "?"


def _retire_superseded_skips(records: list[dict]) -> list[dict]:
	"""Drop skips that a later measurement of the same module has already answered.

	This is the compatibility half of the currency rule, for journals written before
	STATUS_MODULE_CURRENT existed. Those journals contain a skip and then, further down,
	mutant records for the same module - the measurement that retired it - but nothing
	under the skip's own key to say so.

	It runs HERE and nowhere else, deliberately. Journal position only means "later" over
	the COMPLETE journal, and every caller downstream is free to filter that list
	(``--new-since``, ``--prune-stale``). Deciding currency after a filter is how a dead
	skip came back from the dead: the filter keeps the skip (skips are never filtered) and
	removes the mutant records that aged it out, and the module reads as skipped again -
	permanently, since nothing in a fixed-key skip can ever expire. Settling it once,
	against the unfiltered set, makes the answer immune to whatever any caller does next.
	"""
	last_measured: dict[str, int] = {}
	skip_positions: dict[int, str] = {}
	for position, record in enumerate(records):
		status = record.get("status")
		if status in SKIP_STATUSES:
			skip_positions[position] = module_of(record)
		elif status not in MODULE_STATUSES:
			last_measured[module_of(record)] = position
	return [
		record
		for position, record in enumerate(records)
		if position not in skip_positions or last_measured.get(skip_positions[position], -1) < position
	]


def load_results(journal_path: Path, verify_path: Path | None = None) -> list[dict]:
	"""Merge stage-1 results with any stage-2 verdicts, which supersede them.

	The journal is append-only and legitimately contains re-runs of the same mutant, so
	the last record for a key wins. Module-level records share one fixed key per module, so
	that same rule is what makes "this module has a current score" retire an earlier skip:
	they are two records under one key, and only the later one survives here.

	Stage 2 is merged after currency is settled, on purpose: ``verify`` re-runs old
	survivors against the full suite and says nothing about whether this module is
	measurable today, so it must not be able to retire a skip.
	"""
	merged: dict[str, dict] = {}
	for record in journal_mod.read_records(journal_path):
		key = record.get("key")
		if key:
			# pop-then-set moves the key to the end: plain reassignment would keep the
			# first occurrence's position and lose the ordering this function promises.
			merged.pop(key, None)
			merged[key] = record

	merged = {record["key"]: record for record in _retire_superseded_skips(list(merged.values()))}

	if verify_path and verify_path.exists():
		for key, record in journal_mod.latest_by_key(verify_path).items():
			# A verify run that errored or never reached the suite carries no verdict, so
			# it must not overwrite the stage-1 result for that mutant.
			if record.get("status") in NON_SCORING_STATUSES and key in merged:
				continue
			merged.pop(key, None)
			merged[key] = record
	return list(merged.values())


def only_new_since(records: list[dict], baseline_path: Path | None) -> list[dict]:
	"""Keep the mutants this run actually decided: new keys, and CHANGED verdicts.

	This is how a pull-request job reports on *its own* diff. It runs against a journal
	restored from the nightly, so the resume logic spends its small budget only on mutants
	whose keys are new - and mutant keys are content-derived, so a key that survived from
	the nightly describes code this pull request did not touch. Filtering the report by the
	same set means the summary shows exactly what this run added, not the whole corpus.

	A key whose verdict CHANGED is kept even though the key is not new. That is the whole
	point of the nightly: a mutant that was killed last night and survives tonight is the
	regression the job exists to catch, and it is invisible in a cumulative report of 500+
	survivors. Filtering purely on key would drop it - and now that a test edit invalidates
	and re-measures settled verdicts, dropping it is the common case, not a corner.

	A missing baseline (the first ever run, an evicted cache) filters nothing, so the
	report degrades to "everything measured" rather than to silence.

	Module-skip records are never filtered. Their key is a fixed string per module, not a
	content hash, so the argument above does not apply to them: if the nightly already
	journalled the same skip, subtracting it would delete the only evidence that one of
	the files this pull request changed was never measured, and the summary would show a
	clean score for the other file with no mention of it.

	Keeping them is only safe because :func:`load_results` has already settled which skips
	are current, over the unfiltered journal. Never re-decide that here: this function
	cannot see the records that retire a skip, so anything it concludes about currency is a
	guess made with the evidence removed.
	"""
	if baseline_path is None or not baseline_path.exists():
		return records
	settled = {key: record.get("status") for key, record in journal_mod.latest_by_key(baseline_path).items()}
	return [
		record
		for record in records
		if record.get("key") not in settled
		or settled[record.get("key")] != record.get("status")
		or record.get("status") in SKIP_STATUSES
	]


def drop_stale_sites(
	records: list[dict], app_root: Path, unreadable_files: Collection[str] = ()
) -> tuple[list[dict], int]:
	"""Drop verdicts about mutation sites that no longer exist in the source.

	The journal is cumulative and mutant keys are content-derived, so refactoring a target
	does not delete its old records - it just re-keys the sites and adds new ones. The old
	verdicts stay in both the numerator and the denominator for ever, and their survivor
	entries keep printing line numbers into code that has since moved. One edit to a large
	function re-keys every mutant in that scope, so this is not a slow drift: a single
	refactor can orphan dozens of records at once, and the headline percentage stops being
	a fact about the repository.

	A file that cannot be read or parsed keeps all of its records: "I could not check"
	must never be resolved into "these results are stale". Module-level records are keyed
	per module rather than per site and are always kept - including the record that says a
	module's score is current, which no filter may separate from the skip it retires.

	``unreadable_files`` names repo-relative files whose contents cannot be trusted to
	answer the question - in practice, a file a crashed run left mutated. Their records are
	kept whatever the source says: one applied mutant re-keys every site in its scope, so
	pruning against a mutated tree deletes dozens of perfectly good verdicts and reports
	them as "sites that no longer exist".

	Returns the surviving records and how many were dropped.
	"""
	# Imported here, not at module level: rendering a report must not depend on the AST
	# layer, so a broken mutator can never stop a human reading yesterday's numbers.
	from . import mutators

	live: dict[str, set[str] | None] = {}
	kept: list[dict] = []
	for record in records:
		rel = record.get("file") or record.get("module")
		if not isinstance(rel, str) or not rel or record.get("status") in MODULE_STATUSES:
			kept.append(record)
			continue
		if rel in unreadable_files:
			kept.append(record)
			continue
		if rel not in live:
			try:
				source = (app_root / rel).read_text(encoding="utf-8")
				# mutate_strings=True so a campaign run with it is not read as stale.
				live[rel] = {s.key for s in mutators.collect_sites(source, rel, mutate_strings=True)}
			except (OSError, SyntaxError, ValueError):
				live[rel] = None
		known = live[rel]
		if known is None or record.get("key") in known:
			kept.append(record)
	return kept, len(records) - len(kept)


def current_fingerprints() -> dict[str, str]:
	"""What each target's tests hash to right now, or ``{}`` if that cannot be answered.

	Best effort on purpose: this only adds a marker to a report, so a tree the fingerprint
	cannot be computed against must degrade to "no marker", never to a failed report.
	"""
	try:
		from . import scope
		from .config import target_map

		return {rel: scope.test_fingerprint(tests, APP_ROOT) for rel, tests in target_map("all").items()}
	except Exception:  # noqa: BLE001 - a report must never fail because of this
		return {}


def _provenance(shas: set[str | None], current: str) -> str:
	"""Whether a module's verdicts were produced by the tests as they are now.

	``stale`` is not ``wrong``: the verdicts were true of the suite that produced them. But
	the resume logic has already flagged them for re-measurement, and a big module can take
	several budgeted nights to work through, so for those nights the published number is a
	fact about a suite that no longer exists. Saying so is the difference between a report
	that is out of date and a report that is quietly misleading.
	"""
	if shas == {current}:
		return "current"
	if None in shas:
		# Written before verdicts carried their provenance: we cannot show what produced it.
		return "unknown"
	return "stale"


def summarise(records: list[dict], fingerprints: Mapping[str, str] | None = None) -> dict:
	by_module: dict[str, Counter] = defaultdict(Counter)
	survivors: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
	# The module-level record for each module, i.e. its own statement about whether it has
	# a current score. There is one per module by construction (a fixed key per module, and
	# load_results keeps only the last record for a key), so this reads a FACT. It used to
	# be inferred from where the records sat relative to each other, which silently became
	# a lie as soon as a caller filtered the list - see _retire_superseded_skips.
	module_state: dict[str, dict] = {}
	# Which test files each module's verdicts claim to have been produced by.
	module_shas: dict[str, set[str | None]] = defaultdict(set)

	for record in records:
		module = module_of(record)
		status = record.get("status", "?")
		if status in MODULE_STATUSES:
			module_state[module] = record
			continue
		module_shas[module].add(record.get("tests_sha"))
		by_module[module][status] += 1
		if status == STATUS_SURVIVED:
			survivors[record.get("file", module)][record.get("function") or "<module>"].append(record)

	skipped = {
		module: record.get("reason", "")
		for module, record in module_state.items()
		if record.get("status") in SKIP_STATUSES
	}
	# Every module-level skip, whatever dropped it: a red baseline, a source file that no
	# longer exists, a backup that could not be taken. All three mean the same thing to a
	# reader - this module has no current score - and a gate that only sees one of them
	# lets the other two go green having measured nothing.
	skipped_modules = {
		module: {
			"reason": reason,
			"kind": (
				"red baseline"
				if module_state[module].get("status") == STATUS_BASELINE_SKIP
				else "not measurable"
			),
		}
		for module, reason in skipped.items()
	}

	scores = {}
	for module, counts in by_module.items():
		# Mutants whose run never produced a verdict (bench failed, site locked, timeout,
		# harness error) are excluded from BOTH sides of the ratio. Counting them as kills
		# reports 100% for a suite that never ran; counting them in the denominator alone
		# punishes the tests for an infrastructure failure. When that leaves nothing to
		# divide by, the score is None - "not measured" - never 0.0, which would be
		# indistinguishable from a module whose tests genuinely killed nothing.
		total = sum(counts.values())
		unscored = sum(counts[s] for s in NON_SCORING_STATUSES)
		scored = total - unscored
		killed = sum(counts[s] for s in KILLED_STATUSES)
		scores[module] = {
			"total": total,
			"scored": scored,
			"unscored": unscored,
			"killed": killed,
			"score": round(killed / scored, 4) if scored else None,
			"counts": dict(counts),
			# Set when the module's most recent journal entry is a red-baseline skip:
			# the counts above are then leftovers from an earlier, greener run.
			"baseline_skip": skipped.get(module),
			# "current" / "stale" / "unknown", or absent when nothing was passed to compare
			# against. The score above is only a fact about the suite as it is now when
			# this says "current".
			**(
				{"provenance": _provenance(module_shas[module], fingerprints[module])}
				if fingerprints is not None and module in fingerprints
				else {}
			),
		}

	overall_scored = sum(s["scored"] for s in scores.values())
	overall_unscored = sum(s["unscored"] for s in scores.values())
	overall_killed = sum(s["killed"] for s in scores.values())

	# A skip deliberately creates no entry in ``modules``: it is not a mutant and must
	# never look like one with a score of n/a. ``skipped_modules`` below is where a module
	# that measured nothing is visible, and it is what both CI gates read.
	return {
		"modules": scores,
		"survivors": {f: {fn: rs for fn, rs in fns.items()} for f, fns in survivors.items()},
		# Red baselines only, kept as its own key because it is the one skip whose counts
		# above are a stale score rather than an absent one.
		"baseline_skipped": {
			module: info["reason"]
			for module, info in skipped_modules.items()
			if info["kind"] == "red baseline"
		},
		"skipped_modules": skipped_modules,
		"unmeasured_modules": sorted(m for m, s in scores.items() if s["score"] is None),
		# Modules whose verdicts were produced by a suite that has since changed. They are
		# already queued for re-measurement, but a big module takes several budgeted nights
		# to work through and the headline is computed from them meanwhile.
		"stale_test_modules": sorted(
			m for m, s in scores.items() if s.get("provenance", "current") != "current"
		),
		"overall": {
			"total": sum(s["total"] for s in scores.values()),
			"scored": overall_scored,
			"unscored": overall_unscored,
			"killed": overall_killed,
			"score": round(overall_killed / overall_scored, 4) if overall_scored else None,
		},
	}


def provenance_note(provenance: str) -> str:
	"""Say which of the two ways a module's verdicts fail to describe its current tests.

	They are different facts and must not share a sentence: "the tests were edited and this
	number predates the edit" is a dated measurement, while "nothing records what produced
	this number" is a measurement with no provenance at all.
	"""
	if provenance == "stale":
		return "tests changed since these verdicts were measured"
	return "no record of which tests produced these verdicts"


def format_score(score: float | None) -> str:
	"""Render a score, or "n/a" when there was nothing to measure."""
	return "n/a" if score is None else f"{score:.0%}"


def is_empty(summary: dict) -> bool:
	"""True when there is genuinely nothing to say: no mutant, no module statement."""
	return not summary["modules"] and not summary["skipped_modules"]


def render_text(summary: dict) -> str:
	lines: list[str] = ["Mutation report", "=" * 60, ""]
	if is_empty(summary):
		# Not a table of zeros: an all-zero table with "OVERALL: n/a - NOTHING MEASURED"
		# reads as a broken run, and this is the benign case where nothing was due.
		return "\n".join(lines + ["Nothing to report: no mutant was measured in this view.", ""])

	lines.append("Scores")
	lines.append("-" * 60)
	for module in sorted(summary["modules"]):
		info = summary["modules"][module]
		lines.append(f"{module}")
		if info["score"] is None:
			lines.append(f"  score: n/a - NOT MEASURED ({info['total']} mutant(s), none produced a verdict)")
		else:
			lines.append(f"  score: {info['score']:.0%}  ({info['killed']}/{info['scored']} killed)")
			if info["unscored"]:
				lines.append(f"  unscored (no verdict): {info['unscored']}")
		if info["baseline_skip"]:
			lines.append(
				f"  STALE: the latest run skipped this module (red baseline: "
				f"{info['baseline_skip']}); the counts above predate that run"
			)
		if info.get("provenance", "current") != "current":
			lines.append(
				f"  STALE: {provenance_note(info['provenance'])}; "
				f"this module is queued for re-measurement"
			)
		for status in sorted(info["counts"]):
			lines.append(f"    {status}: {info['counts'][status]}")
	overall = summary["overall"]
	lines.append("")
	if overall["score"] is None:
		lines.append(f"OVERALL: n/a - NOTHING MEASURED ({overall['total']} mutant(s), no verdicts)")
	else:
		lines.append(f"OVERALL: {overall['score']:.0%}  ({overall['killed']}/{overall['scored']} killed)")
	if overall["unscored"]:
		lines.append(
			f"WARNING: {overall['unscored']} mutant(s) produced no verdict and are excluded "
			f"from the score. Re-run to re-evaluate them."
		)
	if summary["unmeasured_modules"]:
		lines.append(
			f"WARNING: {len(summary['unmeasured_modules'])} module(s) have no score at all: "
			f"{', '.join(summary['unmeasured_modules'])}"
		)
	if summary.get("stale_test_modules"):
		lines.append(
			f"WARNING: {len(summary['stale_test_modules'])} module(s) are scored from verdicts "
			f"that cannot be shown to come from their current tests: "
			f"{', '.join(summary['stale_test_modules'])}"
		)

	if summary["skipped_modules"]:
		lines += ["", "Skipped - measured nothing this run", "-" * 60]
		for module, info in sorted(summary["skipped_modules"].items()):
			lines.append(f"{module} [{info['kind']}]: {info['reason']}")

	lines += ["", "Survivors (stage 1: only each module's own mapped tests were run)", "-" * 60]
	if not summary["survivors"]:
		lines.append("none")
	for path in sorted(summary["survivors"]):
		lines.append(f"\n{path}")
		for function in sorted(summary["survivors"][path]):
			lines.append(f"  {function}()")
			for record in sorted(summary["survivors"][path][function], key=lambda r: r.get("line", 0)):
				lines.append(
					f"    line {record.get('line')}: "
					f"{record.get('original_segment')} -> {record.get('mutated_segment')}"
					f"   [{record.get('mutator')}]"
				)
	return "\n".join(lines) + "\n"


def render_markdown(summary: dict) -> str:
	if is_empty(summary):
		return "Nothing to report: no mutant was measured in this view.\n"
	lines = ["# Mutation report", "", "## Scores", ""]
	lines += ["| Module | Score | Killed | Scored | No verdict |", "| --- | --- | --- | --- | --- |"]
	for module in sorted(summary["modules"]):
		info = summary["modules"][module]
		label = f"`{module}`"
		if info["baseline_skip"]:
			label += " (stale: skipped, red baseline)"
		if info.get("provenance", "current") != "current":
			label += f" (stale: {provenance_note(info['provenance'])})"
		score = "**n/a** (not measured)" if info["score"] is None else f"{info['score']:.0%}"
		lines.append(f"| {label} | {score} | {info['killed']} | {info['scored']} | {info['unscored']} |")
	overall = summary["overall"]
	overall_score = (
		"**n/a** (nothing measured)" if overall["score"] is None else f"**{overall['score']:.0%}**"
	)
	lines.append(
		f"| **overall** | {overall_score} | {overall['killed']} | {overall['scored']} | "
		f"{overall['unscored']} |"
	)
	if overall["unscored"]:
		lines += [
			"",
			f"> {overall['unscored']} mutant(s) produced no verdict and are excluded from the "
			f"score. Re-run to re-evaluate them.",
		]
	if summary["unmeasured_modules"]:
		lines += [
			"",
			f"> {len(summary['unmeasured_modules'])} module(s) have no score at all: "
			+ ", ".join(f"`{m}`" for m in summary["unmeasured_modules"]),
		]
	if summary.get("stale_test_modules"):
		lines += [
			"",
			f"> {len(summary['stale_test_modules'])} module(s) are scored from verdicts that "
			f"cannot be shown to come from their current tests, and are queued for "
			f"re-measurement: " + ", ".join(f"`{m}`" for m in summary["stale_test_modules"]),
		]

	if summary["skipped_modules"]:
		lines += ["", "## Skipped - measured nothing this run", ""]
		for module, info in sorted(summary["skipped_modules"].items()):
			lines.append(f"- `{module}` ({info['kind']}) - {info['reason']}")

	lines += ["", "## Survivors", ""]
	lines += [
		"Stage 1 only: each mutant was run against its module's own mapped tests, so a"
		" survivor here may still be caught by another module's suite. `verify` is what"
		" separates the two.",
		"",
	]
	if not summary["survivors"]:
		lines.append("None.")
	for path in sorted(summary["survivors"]):
		lines.append(f"### `{path}`")
		lines.append("")
		for function in sorted(summary["survivors"][path]):
			lines.append(f"**{function}()**")
			lines.append("")
			for record in sorted(summary["survivors"][path][function], key=lambda r: r.get("line", 0)):
				lines.append(
					f"- line {record.get('line')}: `{record.get('original_segment')}` -> "
					f"`{record.get('mutated_segment')}` ({record.get('mutator')})"
				)
			lines.append("")
	return "\n".join(lines) + "\n"


def report(
	journal_path: Path | None = None,
	fmt: str = "text",
	verify_path: Path | None = None,
	fail_under: float | None = None,
	new_since: Path | None = None,
	prune_stale: bool = False,
) -> int:
	"""Render the report and return the gate verdict.

	The outcomes are kept distinct on purpose - see the exit code constants above.
	Rendering always happens first: the numbers are the point, the exit code only decides
	whether a machine should act on them.
	"""
	journal_path = journal_path or JOURNAL_PATH
	records = load_results(journal_path, verify_path or verify_path_for(journal_path))
	if prune_stale:
		mutated = mutated_files(APP_ROOT)
		if mutated:
			_notice(
				f"not pruning {', '.join(sorted(mutated))}: a crashed run left a mutant applied, "
				f"and mutated source re-keys every site in its scope"
			)
		records, dropped = drop_stale_sites(records, APP_ROOT, unreadable_files=mutated)
		if dropped:
			_notice(f"dropped {dropped} verdict(s) about mutation sites that no longer exist")
	if new_since is not None:
		before = len(records)
		records = only_new_since(records, new_since)
		_notice(f"{len(records)} of {before} record(s) are new since {new_since}")
	if not records:
		_notice(f"no results in {journal_path}")
	# Marked, not silently published: between a test edit and the re-measurement it
	# triggers - up to several budgeted nights for a big module - the score is computed
	# from verdicts the harness has itself already flagged as describing a suite that no
	# longer exists.
	summary = summarise(records, fingerprints=current_fingerprints())
	# Rendered even when the result set is empty: the summary is what the CI gates parse,
	# and a step that emits nothing forces its caller to guess whether the report was empty
	# or crashed. render_* prints one honest line for the empty case.
	if fmt == "json":
		print(json.dumps(summary, indent=2, sort_keys=True))
	elif fmt == "md":
		print(render_markdown(summary), end="")
	else:
		print(render_text(summary), end="")
	return gate(summary, fail_under)


def mutated_files(app_root: Path) -> set[str]:
	"""Repo-relative paths a crashed run left mutated, as far as the backup dir knows.

	Best effort by design: this only guards a report from pruning against source it cannot
	trust, so a safety layer that cannot be read must not stop the report rendering.
	"""
	try:
		from . import safety

		orphans = safety.find_orphaned_backups()
	except Exception:  # noqa: BLE001 - a report must never fail because of the safety layer
		return set()
	mutated: set[str] = set()
	for manifest in orphans:
		if safety.orphan_state(manifest) == "clean":
			continue
		try:
			mutated.add(Path(manifest["path"]).resolve().relative_to(app_root.resolve()).as_posix())
		except (KeyError, ValueError):
			continue
	return mutated


def gate(summary: dict, fail_under: float | None = None) -> int:
	"""Turn a summary into an exit code, explaining any non-zero one on stdout."""
	if summary["overall"]["total"] == 0:
		# No mutant record at all in this view - nothing was even attempted, so there is
		# nothing to be degraded about. Deliberately NOT the same code as "we ran mutants
		# and none of them produced a verdict": see EXIT_NOTHING_TO_REPORT. A skip record
		# lands here too, and is surfaced through ``skipped_modules`` rather than through
		# an exit code that would claim the measurement broke.
		_notice("nothing to report: this view contains no mutant verdicts")
		return EXIT_NOTHING_TO_REPORT
	score = summary["overall"]["score"]
	if score is None:
		_notice(
			"FAIL: nothing was measured - every mutant produced a non-verdict "
			"(broken site, timeouts, or a campaign that never ran). This is not a score of 0%."
		)
		return EXIT_NOTHING_MEASURED
	if fail_under is not None:
		percent = score * 100
		# The score is rounded to 4 decimal places, so compare with a tolerance rather
		# than failing a run that is exactly on the threshold.
		if percent + 1e-9 < fail_under:
			_notice(f"FAIL: overall score {percent:.1f}% is below --fail-under {fail_under:g}%")
			return EXIT_BELOW_THRESHOLD
	return EXIT_OK


def work_done(journal_path: Path, since_path: Path | None = None) -> dict:
	"""What a run DID, as opposed to what it decided.

	The two are not the same and a summary that only reports the second is unreadable. A
	night that re-measures 400 mutants because a test file was touched, and confirms every
	single verdict, has decided nothing: ``--new-since`` correctly filters all of it away
	and the summary says "nothing new". So does a night whose campaign never started. A
	reader cannot tell "nothing changed" from "nothing ran" without this, which is exactly
	the state a broken nightly hides in.

	The journal is append-only, so the run's own work is whatever sits past the snapshot
	taken before it started. If the journal is SHORTER than the snapshot it was not
	appended to but replaced, and the honest answer is then "unknown" rather than a
	subtraction that would invent a number.
	"""
	journal_records = journal_mod.read_records(journal_path)
	before = len(journal_mod.read_records(since_path)) if since_path and since_path.exists() else 0
	if len(journal_records) < before:
		return {"unknown": True, "evaluated": 0, "modules": [], "skipped": []}
	added = journal_records[before:]
	modules = {module_of(r) for r in added if r.get("status") not in MODULE_STATUSES}
	skipped = {module_of(r) for r in added if r.get("status") in SKIP_STATUSES}
	return {
		"unknown": False,
		"evaluated": sum(1 for r in added if r.get("status") not in MODULE_STATUSES),
		"modules": sorted(modules),
		"skipped": sorted(skipped),
	}


def render_work(work: dict) -> str:
	"""One line naming the work a run did, for a job summary."""
	if work["unknown"]:
		return "Work this run: unknown - the journal was replaced rather than appended to."
	if not work["evaluated"]:
		line = "Work this run: no mutant was evaluated."
	else:
		line = (
			f"Work this run: {work['evaluated']} mutant(s) evaluated across "
			f"{len(work['modules'])} module(s) ({', '.join(work['modules'])})."
		)
	if work["skipped"]:
		line += f" {len(work['skipped'])} module(s) measured nothing: {', '.join(work['skipped'])}."
	return line
