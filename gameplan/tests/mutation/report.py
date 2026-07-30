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
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from . import journal as journal_mod
from .config import (
	JOURNAL_PATH,
	KILLED_STATUSES,
	NON_SCORING_STATUSES,
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


def load_results(journal_path: Path, verify_path: Path | None = None) -> list[dict]:
	"""Merge stage-1 results with any stage-2 verdicts, which supersede them.

	The journal is append-only and legitimately contains re-runs of the same mutant, so
	the last record for a key wins. The returned list is ordered by the position of each
	winning record, which is what lets :func:`summarise` tell "this module was skipped,
	then later measured" apart from "this module was measured, then later skipped".
	"""
	merged: dict[str, dict] = {}
	for record in journal_mod.read_records(journal_path):
		key = record.get("key")
		if key:
			# pop-then-set moves the key to the end: plain reassignment would keep the
			# first occurrence's position and lose the ordering this function promises.
			merged.pop(key, None)
			merged[key] = record

	if verify_path and verify_path.exists():
		for key, record in journal_mod.latest_by_key(verify_path).items():
			# A verify run that errored or never reached the suite carries no verdict, so
			# it must not overwrite the stage-1 result for that mutant.
			if record.get("status") in NON_SCORING_STATUSES and key in merged:
				continue
			merged.pop(key, None)
			merged[key] = record
	return list(merged.values())


def summarise(records: list[dict]) -> dict:
	by_module: dict[str, Counter] = defaultdict(Counter)
	survivors: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
	# A red baseline is journalled under the fixed key "baseline:<path>", and a later
	# GREEN baseline writes nothing to clear it, so the skip record is immortal. Track
	# where each skip and each mutant verdict sits in journal order: a skip only still
	# describes the module if nothing was measured for that module afterwards.
	skip_reason: dict[str, str] = {}
	last_skip_at: dict[str, int] = {}
	last_mutant_at: dict[str, int] = {}

	for position, record in enumerate(records):
		module = record.get("module") or record.get("file") or "?"
		status = record.get("status", "?")
		if status == STATUS_BASELINE_SKIP:
			skip_reason[module] = record.get("reason", "")
			last_skip_at[module] = position
			continue
		last_mutant_at[module] = position
		by_module[module][status] += 1
		if status == STATUS_SURVIVED:
			survivors[record.get("file", module)][record.get("function") or "<module>"].append(record)

	skipped = {
		module: reason
		for module, reason in skip_reason.items()
		if last_skip_at[module] > last_mutant_at.get(module, -1)
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
		}

	overall_scored = sum(s["scored"] for s in scores.values())
	overall_unscored = sum(s["unscored"] for s in scores.values())
	overall_killed = sum(s["killed"] for s in scores.values())

	return {
		"modules": scores,
		"survivors": {f: {fn: rs for fn, rs in fns.items()} for f, fns in survivors.items()},
		"baseline_skipped": skipped,
		"unmeasured_modules": sorted(m for m, s in scores.items() if s["score"] is None),
		"overall": {
			"total": sum(s["total"] for s in scores.values()),
			"scored": overall_scored,
			"unscored": overall_unscored,
			"killed": overall_killed,
			"score": round(overall_killed / overall_scored, 4) if overall_scored else None,
		},
	}


def format_score(score: float | None) -> str:
	"""Render a score, or "n/a" when there was nothing to measure."""
	return "n/a" if score is None else f"{score:.0%}"


def render_text(summary: dict) -> str:
	lines: list[str] = ["Mutation report", "=" * 60, ""]

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

	if summary["baseline_skipped"]:
		lines += ["", "Skipped (red baseline)", "-" * 60]
		for module, reason in sorted(summary["baseline_skipped"].items()):
			lines.append(f"{module}: {reason}")

	lines += ["", "Survivors", "-" * 60]
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
	lines = ["# Mutation report", "", "## Scores", ""]
	lines += ["| Module | Score | Killed | Scored | No verdict |", "| --- | --- | --- | --- | --- |"]
	for module in sorted(summary["modules"]):
		info = summary["modules"][module]
		label = f"`{module}`"
		if info["baseline_skip"]:
			label += " (stale: skipped, red baseline)"
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

	if summary["baseline_skipped"]:
		lines += ["", "## Skipped (red baseline)", ""]
		for module, reason in sorted(summary["baseline_skipped"].items()):
			lines.append(f"- `{module}` - {reason}")

	lines += ["", "## Survivors", ""]
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
) -> int:
	"""Render the report and return the gate verdict.

	The three outcomes are kept distinct on purpose - see the exit code constants above.
	Rendering always happens first: the numbers are the point, the exit code only decides
	whether a machine should act on them.
	"""
	journal_path = journal_path or JOURNAL_PATH
	records = load_results(journal_path, verify_path or verify_path_for(journal_path))
	if not records:
		print(f"[mutation] no results in {journal_path}")
		# An empty journal is the purest form of "nothing measured": exiting 0 here would
		# let a nightly whose campaign never started report a passing mutation score.
		return EXIT_NOTHING_MEASURED
	summary = summarise(records)
	if fmt == "json":
		print(json.dumps(summary, indent=2, sort_keys=True))
	elif fmt == "md":
		print(render_markdown(summary), end="")
	else:
		print(render_text(summary), end="")
	return gate(summary, fail_under)


def gate(summary: dict, fail_under: float | None = None) -> int:
	"""Turn a summary into an exit code, explaining any non-zero one on stdout."""
	score = summary["overall"]["score"]
	if score is None:
		print(
			"[mutation] FAIL: nothing was measured - every mutant produced a non-verdict "
			"(broken site, timeouts, or a campaign that never ran). This is not a score of 0%."
		)
		return EXIT_NOTHING_MEASURED
	if fail_under is not None:
		percent = score * 100
		# The score is rounded to 4 decimal places, so compare with a tolerance rather
		# than failing a run that is exactly on the threshold.
		if percent + 1e-9 < fail_under:
			print(f"[mutation] FAIL: overall score {percent:.1f}% is below --fail-under {fail_under:g}%")
			return EXIT_BELOW_THRESHOLD
	return EXIT_OK
