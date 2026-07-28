"""Mutation score and survivor report rendering."""

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


def load_results(journal_path: Path, verify_path: Path | None = None) -> list[dict]:
	"""Merge stage-1 results with any stage-2 verdicts, which supersede them."""
	merged = journal_mod.latest_by_key(journal_path)
	if verify_path and verify_path.exists():
		for key, record in journal_mod.latest_by_key(verify_path).items():
			# A verify run that errored or never reached the suite carries no verdict, so
			# it must not overwrite the stage-1 result for that mutant.
			if record.get("status") in NON_SCORING_STATUSES and key in merged:
				continue
			merged[key] = record
	return list(merged.values())


def summarise(records: list[dict]) -> dict:
	by_module: dict[str, Counter] = defaultdict(Counter)
	survivors: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
	skipped: dict[str, str] = {}

	for record in records:
		module = record.get("module") or record.get("file") or "?"
		status = record.get("status", "?")
		if status == STATUS_BASELINE_SKIP:
			skipped[module] = record.get("reason", "")
			continue
		by_module[module][status] += 1
		if status == STATUS_SURVIVED:
			survivors[record.get("file", module)][record.get("function") or "<module>"].append(record)

	scores = {}
	for module, counts in by_module.items():
		# Mutants whose run never produced a verdict (bench failed, site locked, harness
		# error) are excluded from BOTH sides of the ratio. Counting them as kills
		# reports 100% for a suite that never ran; counting them in the denominator
		# alone punishes the tests for an infrastructure failure.
		total = sum(counts.values())
		unscored = sum(counts[s] for s in NON_SCORING_STATUSES)
		scored = total - unscored
		killed = sum(counts[s] for s in KILLED_STATUSES)
		scores[module] = {
			"total": total,
			"scored": scored,
			"unscored": unscored,
			"killed": killed,
			"score": round(killed / scored, 4) if scored else 0.0,
			"counts": dict(counts),
		}

	overall_scored = sum(s["scored"] for s in scores.values())
	overall_unscored = sum(s["unscored"] for s in scores.values())
	overall_killed = sum(s["killed"] for s in scores.values())

	return {
		"modules": scores,
		"survivors": {f: {fn: rs for fn, rs in fns.items()} for f, fns in survivors.items()},
		"baseline_skipped": skipped,
		"overall": {
			"total": sum(s["total"] for s in scores.values()),
			"scored": overall_scored,
			"unscored": overall_unscored,
			"killed": overall_killed,
			"score": round(overall_killed / overall_scored, 4) if overall_scored else 0.0,
		},
	}


def render_text(summary: dict) -> str:
	lines: list[str] = ["Mutation report", "=" * 60, ""]

	lines.append("Scores")
	lines.append("-" * 60)
	for module in sorted(summary["modules"]):
		info = summary["modules"][module]
		lines.append(f"{module}")
		lines.append(f"  score: {info['score']:.0%}  ({info['killed']}/{info['scored']} killed)")
		if info["unscored"]:
			lines.append(f"  unscored (no verdict): {info['unscored']}")
		for status in sorted(info["counts"]):
			lines.append(f"    {status}: {info['counts'][status]}")
	overall = summary["overall"]
	lines.append("")
	lines.append(f"OVERALL: {overall['score']:.0%}  ({overall['killed']}/{overall['scored']} killed)")
	if overall["unscored"]:
		lines.append(
			f"WARNING: {overall['unscored']} mutant(s) produced no verdict and are excluded "
			f"from the score. Re-run to re-evaluate them."
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
		lines.append(
			f"| `{module}` | {info['score']:.0%} | {info['killed']} | {info['scored']} | "
			f"{info['unscored']} |"
		)
	overall = summary["overall"]
	lines.append(
		f"| **overall** | **{overall['score']:.0%}** | {overall['killed']} | {overall['scored']} | "
		f"{overall['unscored']} |"
	)

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


def report(journal_path: Path | None = None, fmt: str = "text") -> int:
	journal_path = journal_path or JOURNAL_PATH
	records = load_results(journal_path, VERIFY_PATH)
	if not records:
		print(f"[mutation] no results in {journal_path}")
		return 0
	summary = summarise(records)
	if fmt == "json":
		print(json.dumps(summary, indent=2, sort_keys=True))
	elif fmt == "md":
		print(render_markdown(summary), end="")
	else:
		print(render_text(summary), end="")
	return 0
