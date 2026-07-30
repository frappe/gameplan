"""Unit tests for the mutation report renderer.

Pure unit tests: synthetic journals written to a tempdir, no bench and no site. What
they pin is the one property the report exists to guarantee - an absence of evidence is
never rendered as a result. A module nobody could measure must not look like a module
that scored badly, and a non-verdict must never overwrite a real one.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from gameplan.tests.mutation import report as report_mod
from gameplan.tests.mutation.config import (
	JOURNAL_PATH,
	KILLED_STATUSES,
	NON_SCORING_STATUSES,
	STATUS_BASELINE_SKIP,
	STATUS_INFRA_ERROR,
	STATUS_KILLED,
	STATUS_KILLED_BY_OTHER_SUITE,
	STATUS_SURVIVED,
	VERIFY_PATH,
)


def _record(key: str, status: str, module: str = "gameplan/foo.py", **extra: object) -> dict:
	record = {
		"key": key,
		"status": status,
		"module": module,
		"file": module,
		"function": "fn",
		"line": 1,
		"mutator": "return-none",
		"original_segment": "return True",
		"mutated_segment": "return None",
	}
	record.update(extra)
	return record


class MutationReportTest(unittest.TestCase):
	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.tmp = Path(self._tmp.name)

	def write_journal(self, records: list[dict], name: str = "journal.jsonl") -> Path:
		path = self.tmp / name
		with open(path, "w", encoding="utf-8") as handle:
			for record in records:
				handle.write(json.dumps(record, sort_keys=True) + "\n")
		return path

	def summarise(self, records: list[dict], verify: list[dict] | None = None) -> dict:
		journal = self.write_journal(records)
		verify_path = None
		if verify is not None:
			verify_path = self.write_journal(verify, name="journal.verify.jsonl")
		return report_mod.summarise(report_mod.load_results(journal, verify_path))

	# --- dedup -----------------------------------------------------------------

	def test_last_record_for_a_key_wins(self):
		"""The journal is append-only and re-runs a mutant, so only the last verdict counts."""
		summary = self.summarise(
			[
				_record("k1", STATUS_SURVIVED),
				_record("k2", STATUS_KILLED),
				_record("k1", STATUS_KILLED),  # re-run: k1 is now a kill
			]
		)
		info = summary["modules"]["gameplan/foo.py"]
		self.assertEqual(info["total"], 2)
		self.assertEqual(info["killed"], 2)
		self.assertEqual(info["counts"], {STATUS_KILLED: 2})
		self.assertEqual(summary["survivors"], {})

	def test_dedup_keeps_position_of_the_last_occurrence(self):
		"""Ordering is load-bearing: baseline supersession is decided by journal position."""
		journal = self.write_journal(
			[
				_record("k1", STATUS_SURVIVED),
				_record("k2", STATUS_KILLED),
				_record("k1", STATUS_KILLED),
			]
		)
		keys = [r["key"] for r in report_mod.load_results(journal)]
		self.assertEqual(keys, ["k2", "k1"])

	def test_dedup_matches_an_independent_count(self):
		records = [_record(f"k{i % 7}", STATUS_KILLED if i % 2 else STATUS_SURVIVED) for i in range(30)]
		merged = report_mod.load_results(self.write_journal(records))
		expected = {}
		for record in records:
			expected[record["key"]] = record["status"]
		self.assertEqual({r["key"]: r["status"] for r in merged}, expected)
		self.assertEqual(len(merged), 7)

	# --- no verdict is not a zero score ----------------------------------------

	def test_module_with_no_verdicts_has_no_score_rather_than_zero(self):
		summary = self.summarise(
			[
				_record("a1", STATUS_INFRA_ERROR, module="gameplan/bar.py"),
				_record("a2", STATUS_INFRA_ERROR, module="gameplan/bar.py"),
				_record("b1", STATUS_SURVIVED, module="gameplan/foo.py"),
				_record("b2", STATUS_SURVIVED, module="gameplan/foo.py"),
			]
		)
		unmeasured = summary["modules"]["gameplan/bar.py"]
		genuinely_zero = summary["modules"]["gameplan/foo.py"]
		self.assertIsNone(unmeasured["score"])
		self.assertEqual(unmeasured["scored"], 0)
		self.assertEqual(unmeasured["unscored"], 2)
		self.assertEqual(genuinely_zero["score"], 0.0)
		self.assertEqual(summary["unmeasured_modules"], ["gameplan/bar.py"])

	def test_unmeasured_and_zero_scoring_modules_render_differently(self):
		summary = self.summarise(
			[
				_record("a1", STATUS_INFRA_ERROR, module="gameplan/bar.py"),
				_record("b1", STATUS_SURVIVED, module="gameplan/foo.py"),
			]
		)
		text = report_mod.render_text(summary)
		lines = text.splitlines()
		bar_score = lines[lines.index("gameplan/bar.py") + 1]
		foo_score = lines[lines.index("gameplan/foo.py") + 1]
		self.assertIn("n/a", bar_score)
		self.assertIn("NOT MEASURED", bar_score)
		self.assertNotIn("0%", bar_score)
		self.assertIn("0%", foo_score)
		self.assertIn("gameplan/bar.py", text.split("WARNING:")[-1])

		markdown = report_mod.render_markdown(summary)
		bar_row = next(line for line in markdown.splitlines() if "`gameplan/bar.py`" in line)
		foo_row = next(line for line in markdown.splitlines() if "`gameplan/foo.py`" in line)
		self.assertIn("n/a", bar_row)
		self.assertNotIn("0%", bar_row)
		self.assertIn("0%", foo_row)

	def test_overall_score_is_none_when_nothing_was_measured(self):
		summary = self.summarise([_record("a1", STATUS_INFRA_ERROR), _record("a2", STATUS_INFRA_ERROR)])
		self.assertIsNone(summary["overall"]["score"])
		self.assertEqual(summary["overall"]["unscored"], 2)
		text = report_mod.render_text(summary)
		self.assertIn("OVERALL: n/a", text)
		self.assertNotIn("OVERALL: 0%", text)

	def test_format_score_renders_none_as_na(self):
		self.assertEqual(report_mod.format_score(None), "n/a")
		self.assertEqual(report_mod.format_score(0.0), "0%")

	# --- baseline skip precedence ----------------------------------------------

	def test_baseline_skip_is_superseded_by_later_mutant_records(self):
		"""A green re-run journals no 'baseline OK' record, so later mutants must clear it."""
		summary = self.summarise(
			[
				_record("baseline:gameplan/foo.py", STATUS_BASELINE_SKIP, reason="red baseline"),
				_record("k1", STATUS_KILLED),
				_record("k2", STATUS_SURVIVED),
			]
		)
		self.assertEqual(summary["baseline_skipped"], {})
		self.assertIsNone(summary["modules"]["gameplan/foo.py"]["baseline_skip"])
		self.assertEqual(summary["modules"]["gameplan/foo.py"]["score"], 0.5)
		text = report_mod.render_text(summary)
		self.assertNotIn("Skipped - measured nothing this run", text)

	def test_baseline_skip_after_the_mutants_marks_the_score_stale(self):
		summary = self.summarise(
			[
				_record("k1", STATUS_KILLED),
				_record("k2", STATUS_SURVIVED),
				_record("baseline:gameplan/foo.py", STATUS_BASELINE_SKIP, reason="red baseline"),
			]
		)
		self.assertEqual(summary["baseline_skipped"], {"gameplan/foo.py": "red baseline"})
		self.assertEqual(summary["modules"]["gameplan/foo.py"]["baseline_skip"], "red baseline")
		text = report_mod.render_text(summary)
		self.assertIn("STALE", text)
		self.assertIn("Skipped - measured nothing this run", text)
		self.assertIn("(stale: skipped, red baseline)", report_mod.render_markdown(summary))

	def test_baseline_skip_alone_still_reported(self):
		summary = self.summarise(
			[_record("baseline:gameplan/foo.py", STATUS_BASELINE_SKIP, reason="import error")]
		)
		self.assertEqual(summary["baseline_skipped"], {"gameplan/foo.py": "import error"})
		self.assertEqual(summary["modules"], {})
		self.assertIn("import error", report_mod.render_text(summary))

	def test_baseline_skip_is_never_counted_as_a_mutant(self):
		summary = self.summarise(
			[
				_record("baseline:gameplan/bar.py", STATUS_BASELINE_SKIP, module="gameplan/bar.py"),
				_record("k1", STATUS_KILLED),
			]
		)
		self.assertEqual(summary["overall"]["total"], 1)
		self.assertNotIn("gameplan/bar.py", summary["modules"])

	# --- verify stage ------------------------------------------------------------

	def test_verify_verdict_supersedes_a_stage_one_survivor(self):
		summary = self.summarise(
			[_record("k1", STATUS_SURVIVED)],
			verify=[_record("k1", STATUS_KILLED_BY_OTHER_SUITE)],
		)
		self.assertEqual(summary["overall"]["killed"], 1)
		self.assertEqual(summary["survivors"], {})

	def test_non_verdict_never_supersedes_a_real_verdict(self):
		for status in sorted(NON_SCORING_STATUSES):
			with self.subTest(status=status):
				summary = self.summarise(
					[_record("k1", STATUS_SURVIVED)],
					verify=[_record("k1", status)],
				)
				self.assertEqual(summary["modules"]["gameplan/foo.py"]["counts"], {STATUS_SURVIVED: 1})
				self.assertEqual(summary["overall"]["unscored"], 0)
				self.assertEqual(summary["overall"]["score"], 0.0)

	def test_verify_path_is_derived_from_the_journal_path(self):
		"""A custom journal must not be contaminated by the default campaign's verify file."""
		self.assertEqual(report_mod.verify_path_for(JOURNAL_PATH), VERIFY_PATH)
		custom = self.tmp / "archived.jsonl"
		self.assertEqual(report_mod.verify_path_for(custom), self.tmp / "archived.verify.jsonl")
		self.assertNotEqual(report_mod.verify_path_for(custom), VERIFY_PATH)

	# --- arithmetic ---------------------------------------------------------------

	def test_overall_score_arithmetic_excludes_non_verdicts_from_both_sides(self):
		summary = self.summarise(
			[
				_record("a1", STATUS_KILLED, module="gameplan/foo.py"),
				_record("a2", STATUS_KILLED, module="gameplan/foo.py"),
				_record("a3", STATUS_SURVIVED, module="gameplan/foo.py"),
				_record("a4", STATUS_INFRA_ERROR, module="gameplan/foo.py"),
				_record("b1", STATUS_KILLED_BY_OTHER_SUITE, module="gameplan/bar.py"),
				_record("b2", STATUS_SURVIVED, module="gameplan/bar.py"),
				_record("b3", STATUS_SURVIVED, module="gameplan/bar.py"),
			]
		)
		foo = summary["modules"]["gameplan/foo.py"]
		self.assertEqual((foo["total"], foo["scored"], foo["unscored"], foo["killed"]), (4, 3, 1, 2))
		self.assertAlmostEqual(foo["score"], 0.6667, places=4)
		overall = summary["overall"]
		self.assertEqual((overall["total"], overall["scored"], overall["unscored"]), (7, 6, 1))
		self.assertEqual(overall["killed"], 3)
		self.assertEqual(overall["score"], 0.5)
		self.assertIn("3/6 killed", report_mod.render_text(summary))

	def test_every_killed_status_counts_toward_the_score(self):
		records = [_record(f"k{i}", status) for i, status in enumerate(sorted(KILLED_STATUSES))]
		summary = self.summarise(records)
		self.assertEqual(summary["overall"]["killed"], len(KILLED_STATUSES))
		self.assertEqual(summary["overall"]["score"], 1.0)

	def test_summary_is_json_serialisable(self):
		summary = self.summarise([_record("a1", STATUS_INFRA_ERROR), _record("a2", STATUS_KILLED)])
		payload = json.loads(json.dumps(summary, sort_keys=True))
		self.assertEqual(payload["overall"]["score"], 1.0)


class MutationReportExitCodeTest(unittest.TestCase):
	"""The report is a CI gate, so its exit code has to carry the same honesty as its text.

	Four outcomes, four codes: measured-and-good, measured-and-below-threshold,
	measured-and-got-no-verdict, and nothing-to-report. Collapsing any of the last two into
	either of the first is how a nightly ends up reporting a healthy suite for a run in
	which nothing was ever executed - or how a pull-request job turns "my one measurement
	timed out" into "this pull request changed no mutable behaviour".
	"""

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.tmp = Path(self._tmp.name)

	def run_report(self, records: list[dict] | None, **kwargs: object) -> tuple[int, str]:
		"""Run the report over a synthetic journal. ``None`` means "no journal at all"."""
		journal = self.tmp / "journal.jsonl"
		if records is not None:
			with open(journal, "w", encoding="utf-8") as handle:
				for record in records:
					handle.write(json.dumps(record, sort_keys=True) + "\n")
		buffer = io.StringIO()
		errors = io.StringIO()
		# stdout is the report itself (it is piped into a job summary and into json.load),
		# so every human-facing notice must be on stderr. Captured separately here so a
		# regression that puts chatter back on stdout fails a test instead of a CI job.
		with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(errors):
			code = report_mod.report(journal_path=journal, **kwargs)
		self.stdout = buffer.getvalue()
		self.stderr = errors.getvalue()
		return code, self.stdout

	def test_exit_codes_are_four_distinct_values(self):
		codes = {
			report_mod.EXIT_OK,
			report_mod.EXIT_BELOW_THRESHOLD,
			report_mod.EXIT_NOTHING_MEASURED,
			report_mod.EXIT_NOTHING_TO_REPORT,
		}
		self.assertEqual(len(codes), 4)
		self.assertEqual(report_mod.EXIT_OK, 0)
		self.assertNotEqual(report_mod.EXIT_NOTHING_MEASURED, report_mod.EXIT_BELOW_THRESHOLD)

	def test_measured_and_good_exits_zero(self):
		code, out = self.run_report([_record("k1", STATUS_KILLED), _record("k2", STATUS_SURVIVED)])
		self.assertEqual(code, report_mod.EXIT_OK)
		self.assertIn("OVERALL: 50%", out)

	def test_nothing_measured_does_not_exit_zero(self):
		"""The bug this closes: 'OVERALL: n/a - NOTHING MEASURED' used to exit 0."""
		code, out = self.run_report([_record("k1", STATUS_INFRA_ERROR), _record("k2", STATUS_INFRA_ERROR)])
		self.assertEqual(code, report_mod.EXIT_NOTHING_MEASURED)
		self.assertIn("NOTHING MEASURED", out)
		self.assertIn("FAIL", self.stderr)

	def test_missing_journal_has_nothing_to_report_and_does_not_succeed(self):
		code, out = self.run_report(None)
		self.assertEqual(code, report_mod.EXIT_NOTHING_TO_REPORT)
		self.assertNotEqual(code, report_mod.EXIT_OK)
		self.assertIn("no results", self.stderr)
		# Rendered, not silent: both CI gates parse this stdout, and a step that prints
		# nothing forces its caller to guess whether the report was empty or crashed.
		self.assertIn("Nothing to report", out)

	def test_empty_journal_has_nothing_to_report_and_does_not_succeed(self):
		code, _out = self.run_report([])
		self.assertEqual(code, report_mod.EXIT_NOTHING_TO_REPORT)
		self.assertNotEqual(code, report_mod.EXIT_OK)

	def test_an_empty_result_set_and_a_verdictless_one_do_not_share_a_code(self):
		"""They license opposite statements: "nothing to say" vs "the measurement broke"."""
		empty, _ = self.run_report([])
		verdictless, _ = self.run_report([_record("k1", STATUS_INFRA_ERROR)])
		self.assertNotEqual(empty, verdictless)

	def test_report_still_renders_when_it_gates(self):
		"""The numbers are the point; the exit code only decides whether a machine acts."""
		for fmt in ("text", "md", "json"):
			with self.subTest(fmt=fmt):
				code, out = self.run_report([_record("k1", STATUS_SURVIVED)], fmt=fmt, fail_under=50)
				self.assertEqual(code, report_mod.EXIT_BELOW_THRESHOLD)
				self.assertIn("gameplan/foo.py", out)

	# --- --fail-under ------------------------------------------------------------

	def test_fail_under_fails_a_regressed_score(self):
		records = [_record("k1", STATUS_KILLED), _record("k2", STATUS_SURVIVED)]
		code, out = self.run_report(records, fail_under=80)
		self.assertEqual(code, report_mod.EXIT_BELOW_THRESHOLD)
		self.assertIn("below --fail-under 80%", self.stderr)

	def test_fail_under_passes_a_score_that_meets_it(self):
		records = [_record("k1", STATUS_KILLED), _record("k2", STATUS_SURVIVED)]
		self.assertEqual(self.run_report(records, fail_under=50)[0], report_mod.EXIT_OK)
		self.assertEqual(self.run_report(records, fail_under=25)[0], report_mod.EXIT_OK)

	def test_fail_under_does_not_fail_a_score_exactly_on_the_threshold(self):
		"""The score is rounded to 4 places, so an exact threshold must not fail on noise."""
		records = [_record(f"k{i}", STATUS_KILLED if i < 2 else STATUS_SURVIVED) for i in range(3)]
		self.assertAlmostEqual(report_mod.summarise(records)["overall"]["score"], 0.6667, places=4)
		self.assertEqual(self.run_report(records, fail_under=66.67)[0], report_mod.EXIT_OK)

	def test_without_fail_under_a_low_score_is_not_a_failure(self):
		"""Reporting is not gating: --fail-under is opt-in, nothing-measured is not."""
		code, _out = self.run_report([_record("k1", STATUS_SURVIVED)])
		self.assertEqual(code, report_mod.EXIT_OK)

	def test_could_not_measure_outranks_the_threshold_gate(self):
		"""A broken run must not be reported as a score regression: they need different fixes."""
		code, out = self.run_report([_record("k1", STATUS_INFRA_ERROR)], fail_under=90)
		self.assertEqual(code, report_mod.EXIT_NOTHING_MEASURED)
		self.assertNotIn("below --fail-under", out)

	def test_gate_is_usable_on_a_summary_directly(self):
		measured = report_mod.summarise([_record("k1", STATUS_KILLED)])
		unmeasured = report_mod.summarise([_record("k1", STATUS_INFRA_ERROR)])
		with contextlib.redirect_stdout(io.StringIO()):
			self.assertEqual(report_mod.gate(measured), report_mod.EXIT_OK)
			self.assertEqual(report_mod.gate(measured, fail_under=100), report_mod.EXIT_OK)
			self.assertEqual(report_mod.gate(unmeasured), report_mod.EXIT_NOTHING_MEASURED)
			self.assertEqual(report_mod.gate(unmeasured, fail_under=0), report_mod.EXIT_NOTHING_MEASURED)


if __name__ == "__main__":
	unittest.main()
