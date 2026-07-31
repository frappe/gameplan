# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Unit tests for the logic the mutation CI jobs are built on.

The two jobs in ``.github/workflows/mutation-*.yml`` cannot be run here, so everything
they depend on is pushed into pure functions and pinned below. The properties, each one a
way the jobs would silently rot:

* the budget stops the campaign BETWEEN mutants and never inside one - a stop mid-mutant
  leaves a mutated source file on disk, which is the single failure the safety layer
  exists to prevent, and a nightly is exactly the unattended context where nobody notices;
* "stopped on budget" has an exit code of its own - shared with success it hides a nightly
  that is falling behind, shared with failure it pages someone every night forever;
* round-robin ordering actually rotates - a budgeted nightly that restarts at the same
  module every night measures the first module and nothing else, for ever;
* diff scope maps changed paths to targets, including the two boring cases (a pull request
  that touches no target, and one that touches a non-target file) that decide whether the
  pull-request job is fast or wrong;
* WHAT THE CACHE MAY CARRY. The journal is the only transferable state. Caching the
  directory it lives in transplants crash sidecars and the campaign lock onto the next
  runner and wedges the nightly permanently, re-poisoning itself every night;
* WHEN A VERDICT GOES STALE. Mutant keys come from the source AST alone, so without the
  test fingerprint a "killed" is settled for ever and deleting an assertion is invisible
  to the one job whose purpose is to notice it;
* EVERY SKIP IS VISIBLE. A module that drops out of the corpus has to say so in the
  journal, in the report and in the gate - otherwise it goes unmeasured for ever while its
  stale verdicts keep counting toward the published score.

No bench, no site, no network: a synthetic app tree in a tempdir and an injected clock.
The two workflow files are read as YAML and asserted against directly, because the
properties above live half in Python and half in twelve lines of shell.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from gameplan.tests.mutation import campaign, cli, config, mutators, safety, scope
from gameplan.tests.mutation import journal as journal_mod
from gameplan.tests.mutation import report as report_mod

# The campaign-loop fixture (synthetic app tree, patched git/orphan/backup plumbing) is
# reused rather than copied: these tests exercise the same loop from a different angle,
# and two divergent copies of that setup would be a bug factory. It defines no test
# methods of its own, so importing it does not re-run anything.
from gameplan.tests.platform.test_mutation_cli import ORIGINAL, CampaignLoopTestCase

# A synthetic target map. Deliberately not the real one: these tests are about the
# mapping logic, and pinning them to the real map would make every legitimate edit to
# config.TIER1/TIER2 fail an unrelated test.
TARGETS = {
	"pkg/alpha.py": ["tests.test_alpha"],
	"pkg/beta.py": ["tests.test_beta", "tests.test_beta_extra"],
	"pkg/gamma.py": ["tests.test_gamma"],
}


def mutant_records(records: list[dict]) -> list[dict]:
	"""Just the mutant verdicts. A campaign also journals statements about MODULES.

	Those statements ("no current score", "score is current") are keyed per module rather
	than per mutation site, and counting them as measurements is the mistake the report
	used to make - see ModuleCurrencyIsDataTest.
	"""
	return [record for record in records if record.get("status") not in config.MODULE_STATUSES]


WORKFLOW_DIR = Path(config.APP_ROOT) / ".github" / "workflows"
NIGHTLY_WORKFLOW = WORKFLOW_DIR / "mutation-nightly.yml"
PR_WORKFLOW = WORKFLOW_DIR / "mutation-pr.yml"


class FakeClock:
	"""A monotonic clock that only moves when the test says so."""

	def __init__(self) -> None:
		self.now = 0.0

	def __call__(self) -> float:
		return self.now

	def advance(self, seconds: float) -> None:
		self.now += seconds


class BudgetTest(unittest.TestCase):
	"""The allowance itself: it must be an honest wall clock and never negative."""

	def test_no_budget_never_expires(self):
		clock = FakeClock()
		budget = scope.Budget(None, clock=clock)
		clock.advance(10_000)
		self.assertFalse(budget.expired)
		self.assertTrue(budget.unlimited)
		self.assertEqual(budget.remaining, float("inf"))

	def test_it_expires_when_the_allowance_is_used(self):
		clock = FakeClock()
		budget = scope.Budget(60, clock=clock)
		clock.advance(59.9)
		self.assertFalse(budget.expired)
		clock.advance(0.1)
		self.assertTrue(budget.expired)

	def test_remaining_counts_down_and_clamps_at_zero(self):
		clock = FakeClock()
		budget = scope.Budget(60, clock=clock)
		clock.advance(20)
		self.assertAlmostEqual(budget.remaining, 40)
		clock.advance(100)
		self.assertEqual(budget.remaining, 0.0)

	def test_a_zero_budget_is_expired_from_the_start(self):
		"""Mirrors --limit 0: an explicit request to evaluate nothing."""
		self.assertTrue(scope.Budget(0, clock=FakeClock()).expired)

	def test_a_negative_budget_is_rejected(self):
		with self.assertRaises(ValueError):
			scope.Budget(-1)

	def test_the_clock_starts_at_construction_not_at_first_check(self):
		"""Setup spends the budget too, or "45 minutes" is not a wall-clock number."""
		clock = FakeClock()
		budget = scope.Budget(30, clock=clock)
		clock.advance(31)
		self.assertTrue(budget.expired)


class BudgetStopsBetweenMutantsTest(CampaignLoopTestCase):
	"""The load-bearing one: where the budget is allowed to interrupt the loop."""

	def run_budgeted(
		self,
		targets: dict[str, list[str]],
		budget_seconds: float,
		cost_per_mutant: float,
		clock: FakeClock | None = None,
	) -> tuple[int, list[bool]]:
		"""Run the loop with a fake clock that only advances while a mutant is evaluated.

		Returns the exit code and, for each mutant that was evaluated, whether the budget
		was already expired at the moment evaluation started.
		"""
		clock = clock or FakeClock()
		expired_on_entry: list[bool] = []
		budget = scope.Budget(budget_seconds, clock=clock)

		def fake_evaluate(_guard, mutated_source, *_args, **_kwargs):
			expired_on_entry.append(budget.expired)
			self.evaluated_sources.append(mutated_source)
			clock.advance(cost_per_mutant)
			return config.STATUS_KILLED, "tests.some_module", cost_per_mutant

		self.evaluated_sources = []
		with mock.patch.object(campaign, "_baseline_ok", return_value=(True, "")):
			with mock.patch.object(campaign, "_evaluate_mutant", fake_evaluate):
				with contextlib.redirect_stdout(io.StringIO()) as out:
					code = campaign._run_campaign_locked(
						targets=targets,
						site="unused.test",
						timeout=1,
						limit=None,
						mutate_strings=False,
						assume_yes=True,
						journal_path=self.journal,
						budget=budget,
					)
		self.output = out.getvalue()
		return code, expired_on_entry

	def test_no_mutant_is_started_after_the_budget_is_gone(self):
		self.write_target("pkg/alpha.py", ORIGINAL)
		_code, expired_on_entry = self.run_budgeted(
			{"pkg/alpha.py": ["tests.test_alpha"]}, budget_seconds=10, cost_per_mutant=4
		)
		self.assertTrue(expired_on_entry, "expected at least one mutant to be evaluated")
		self.assertNotIn(True, expired_on_entry)

	def test_it_stops_partway_through_a_module_rather_than_finishing_it(self):
		path = self.write_target("pkg/alpha.py", ORIGINAL)
		total = len(mutators.collect_sites(path.read_text(), "pkg/alpha.py"))
		self.assertGreater(total, 2, "fixture must have enough mutants to stop partway")

		_code, expired_on_entry = self.run_budgeted(
			{"pkg/alpha.py": ["tests.test_alpha"]}, budget_seconds=2, cost_per_mutant=1
		)
		self.assertLess(len(expired_on_entry), total)

	def test_the_source_file_is_unmutated_after_a_budget_stop(self):
		"""A stop that abandoned a mutant on disk would be worse than no budget at all."""
		path = self.write_target("pkg/alpha.py", ORIGINAL)
		self.run_budgeted({"pkg/alpha.py": ["tests.test_alpha"]}, budget_seconds=2, cost_per_mutant=1)
		self.assertEqual(path.read_text(), ORIGINAL)

	def test_no_backup_is_left_behind_after_a_budget_stop(self):
		"""A stranded sidecar backup makes the next run refuse to start as an orphan."""
		self.write_target("pkg/alpha.py", ORIGINAL)
		self.run_budgeted({"pkg/alpha.py": ["tests.test_alpha"]}, budget_seconds=2, cost_per_mutant=1)
		self.assertEqual(list(self.backup_dir.iterdir()), [])

	def test_everything_it_did_evaluate_is_journalled(self):
		"""The journal is the resume point; work done outside it is work done twice."""
		self.write_target("pkg/alpha.py", ORIGINAL)
		_code, expired_on_entry = self.run_budgeted(
			{"pkg/alpha.py": ["tests.test_alpha"]}, budget_seconds=2, cost_per_mutant=1
		)
		self.assertEqual(len(mutant_records(self.journal_records())), len(expired_on_entry))

	def test_a_budget_stop_does_not_start_the_next_module(self):
		"""The check sits before the module too: a baseline pass costs minutes."""
		self.write_target("pkg/alpha.py", ORIGINAL)
		self.write_target("pkg/beta.py", ORIGINAL)
		self.run_budgeted(
			{"pkg/alpha.py": ["tests.test_alpha"], "pkg/beta.py": ["tests.test_beta"]},
			budget_seconds=2,
			cost_per_mutant=1,
		)
		measured = {record["module"] for record in self.journal_records()}
		self.assertEqual(measured, {"pkg/alpha.py"})

	def test_a_budget_stop_exits_with_the_budget_code(self):
		self.write_target("pkg/alpha.py", ORIGINAL)
		code, _ = self.run_budgeted(
			{"pkg/alpha.py": ["tests.test_alpha"]}, budget_seconds=2, cost_per_mutant=1
		)
		self.assertEqual(code, campaign.EXIT_BUDGET_EXHAUSTED)
		self.assertIn("STOPPED ON BUDGET", self.output)

	def test_a_budget_that_outlasts_the_work_exits_zero(self):
		"""Finishing the corpus inside the allowance is a plain success, not a budget stop."""
		self.write_target("pkg/alpha.py", ORIGINAL)
		code, _ = self.run_budgeted(
			{"pkg/alpha.py": ["tests.test_alpha"]}, budget_seconds=10_000, cost_per_mutant=1
		)
		self.assertEqual(code, campaign.EXIT_OK)


class BudgetExitCodeTest(unittest.TestCase):
	"""``_campaign_exit_code`` again, now with the budget in the mix."""

	def test_stopping_on_budget_is_neither_success_nor_failure(self):
		code = campaign._campaign_exit_code(
			targeted=3, skipped=0, pending=50, evaluated=12, aborted=False, budget_stopped=True
		)
		self.assertEqual(code, campaign.EXIT_BUDGET_EXHAUSTED)
		for other in (
			campaign.EXIT_OK,
			campaign.EXIT_ABORTED,
			campaign.EXIT_USAGE,
			campaign.EXIT_NOTHING_MEASURED,
		):
			self.assertNotEqual(code, other)

	def test_an_abort_outranks_the_budget(self):
		"""The circuit breaker fired: nothing this run produced is credible."""
		code = campaign._campaign_exit_code(
			targeted=3, skipped=0, pending=50, evaluated=12, aborted=True, budget_stopped=True
		)
		self.assertEqual(code, campaign.EXIT_ABORTED)

	def test_a_budget_that_measured_nothing_is_still_a_failure(self):
		"""45 minutes and not one verdict is a broken site, not a budget doing its job."""
		code = campaign._campaign_exit_code(
			targeted=3, skipped=0, pending=50, evaluated=0, aborted=False, budget_stopped=True
		)
		self.assertEqual(code, campaign.EXIT_NOTHING_MEASURED)

	def test_every_module_skipped_outranks_the_budget(self):
		code = campaign._campaign_exit_code(
			targeted=2, skipped=2, pending=0, evaluated=0, aborted=False, budget_stopped=True
		)
		self.assertEqual(code, campaign.EXIT_NOTHING_MEASURED)

	def test_a_zero_budget_is_an_explicit_request_to_measure_nothing(self):
		code = campaign._campaign_exit_code(
			targeted=1,
			skipped=0,
			pending=9,
			evaluated=0,
			aborted=False,
			budget_stopped=True,
			budget_seconds=0,
		)
		self.assertEqual(code, campaign.EXIT_BUDGET_EXHAUSTED)

	def test_an_unbudgeted_run_is_unaffected(self):
		code = campaign._campaign_exit_code(
			targeted=1, skipped=0, pending=9, evaluated=9, aborted=False, budget_stopped=False
		)
		self.assertEqual(code, campaign.EXIT_OK)


class RoundRobinOrderTest(unittest.TestCase):
	"""Ordering is pure: modules in, modules out."""

	MODULES = ["a.py", "b.py", "c.py"]

	def test_an_empty_journal_keeps_the_declared_order(self):
		self.assertEqual(scope.round_robin_order(self.MODULES, {}), self.MODULES)

	def test_the_least_recently_measured_module_goes_first(self):
		order = scope.round_robin_order(self.MODULES, {"a.py": 10, "b.py": 2, "c.py": 7})
		self.assertEqual(order, ["b.py", "c.py", "a.py"])

	def test_never_measured_modules_outrank_measured_ones(self):
		"""A newly added target must not wait a full rotation to be looked at."""
		order = scope.round_robin_order(self.MODULES, {"a.py": 0, "c.py": 1})
		self.assertEqual(order, ["b.py", "a.py", "c.py"])

	def test_ties_keep_the_declared_order(self):
		order = scope.round_robin_order(self.MODULES, {"a.py": 5, "b.py": 5, "c.py": 5})
		self.assertEqual(order, self.MODULES)

	def test_it_rotates_rather_than_restarting_at_the_same_module(self):
		"""Simulate three budgeted nights, each measuring only whatever came first."""
		positions: dict[str, int] = {}
		clock = 0
		first_each_night = []
		for _night in range(4):
			order = scope.round_robin_order(self.MODULES, positions)
			first_each_night.append(order[0])
			clock += 1
			positions[order[0]] = clock
		self.assertEqual(first_each_night, ["a.py", "b.py", "c.py", "a.py"])

	def test_last_measured_positions_uses_the_most_recent_record(self):
		records = [
			{"module": "a.py"},
			{"module": "b.py"},
			{"module": "a.py"},
		]
		self.assertEqual(scope.last_measured_positions(records), {"a.py": 2, "b.py": 1})

	def test_last_measured_positions_falls_back_to_the_file_field(self):
		"""Older journal records predate the "module" field."""
		self.assertEqual(scope.last_measured_positions([{"file": "a.py"}]), {"a.py": 0})

	def test_records_without_a_module_are_ignored(self):
		self.assertEqual(scope.last_measured_positions([{"status": "killed"}, {"module": ""}]), {})


class RoundRobinInTheLoopTest(CampaignLoopTestCase):
	"""Consecutive budgeted runs over one journal must move through the corpus."""

	def night(self, targets: dict[str, list[str]]) -> str | None:
		"""One budgeted run that can afford exactly one mutant. Returns the module it hit."""
		clock = FakeClock()
		budget = scope.Budget(1, clock=clock)

		def fake_evaluate(*_args, **_kwargs):
			clock.advance(100)
			return config.STATUS_KILLED, "tests.some_module", 100.0

		before = len(self.journal_records())
		with mock.patch.object(campaign, "_baseline_ok", return_value=(True, "")):
			with mock.patch.object(campaign, "_evaluate_mutant", fake_evaluate):
				with contextlib.redirect_stdout(io.StringIO()):
					campaign._run_campaign_locked(
						targets=targets,
						site="unused.test",
						timeout=1,
						limit=None,
						mutate_strings=False,
						assume_yes=True,
						journal_path=self.journal,
						budget=budget,
					)
		added = self.journal_records()[before:]
		return added[0]["module"] if added else None

	def test_three_nights_cover_three_modules(self):
		targets = {}
		for name in ("alpha", "beta", "gamma"):
			self.write_target(f"pkg/{name}.py", ORIGINAL)
			targets[f"pkg/{name}.py"] = [f"tests.test_{name}"]

		nights = [self.night(targets) for _ in range(3)]

		self.assertEqual(nights, ["pkg/alpha.py", "pkg/beta.py", "pkg/gamma.py"])

	def test_the_fourth_night_wraps_back_to_the_first_module(self):
		targets = {}
		for name in ("alpha", "beta"):
			self.write_target(f"pkg/{name}.py", ORIGINAL)
			targets[f"pkg/{name}.py"] = [f"tests.test_{name}"]

		nights = [self.night(targets) for _ in range(4)]

		self.assertEqual(nights, ["pkg/alpha.py", "pkg/beta.py", "pkg/alpha.py", "pkg/beta.py"])

	def test_a_finished_module_costs_no_baseline_run(self):
		"""Otherwise a mostly-finished corpus spends its whole budget re-proving itself."""
		self.write_target("pkg/alpha.py", ORIGINAL)
		targets = {"pkg/alpha.py": ["tests.test_alpha"]}
		with mock.patch.object(campaign, "_baseline_ok", return_value=(True, "")) as baseline:
			with mock.patch.object(
				campaign, "_evaluate_mutant", lambda *_a, **_k: (config.STATUS_KILLED, "t", 0.0)
			):
				with contextlib.redirect_stdout(io.StringIO()):
					for _ in range(2):
						campaign._run_campaign_locked(
							targets=targets,
							site="unused.test",
							timeout=1,
							limit=None,
							mutate_strings=False,
							assume_yes=True,
							journal_path=self.journal,
						)
		self.assertEqual(baseline.call_count, 1)


class ChangedTargetsTest(unittest.TestCase):
	"""Diff scope: which targets a pull request implicates."""

	def test_a_changed_target_source_selects_itself(self):
		selected = scope.changed_targets(["pkg/beta.py"], TARGETS)
		self.assertEqual(selected, {"pkg/beta.py": ["tests.test_beta", "tests.test_beta_extra"]})

	def test_a_changed_test_module_selects_the_source_it_covers(self):
		"""Deleting an assertion is exactly the change this job exists to catch."""
		selected = scope.changed_targets(["tests/test_beta_extra.py"], TARGETS)
		self.assertEqual(list(selected), ["pkg/beta.py"])

	def test_a_pull_request_that_touches_no_target_selects_nothing(self):
		selected = scope.changed_targets(["frontend/src/pages/Discussion.vue", "README.md"], TARGETS)
		self.assertEqual(selected, {})

	def test_a_non_target_python_file_selects_nothing(self):
		"""Being Python is not the same as being mapped to tests."""
		self.assertEqual(scope.changed_targets(["pkg/untested.py"], TARGETS), {})

	def test_an_empty_diff_selects_nothing(self):
		self.assertEqual(scope.changed_targets([], TARGETS), {})

	def test_several_changed_files_select_several_targets_in_declared_order(self):
		selected = scope.changed_targets(["pkg/gamma.py", "pkg/alpha.py"], TARGETS)
		self.assertEqual(list(selected), ["pkg/alpha.py", "pkg/gamma.py"])

	def test_a_source_and_its_test_do_not_select_it_twice(self):
		selected = scope.changed_targets(["pkg/alpha.py", "tests/test_alpha.py"], TARGETS)
		self.assertEqual(list(selected), ["pkg/alpha.py"])

	def test_paths_are_normalised(self):
		for raw in ("./pkg/alpha.py", "  pkg/alpha.py  ", "pkg\\alpha.py"):
			with self.subTest(raw=raw):
				self.assertEqual(list(scope.changed_targets([raw], TARGETS)), ["pkg/alpha.py"])

	def test_blank_lines_in_a_diff_list_are_ignored(self):
		self.assertEqual(scope.changed_targets(["", "   "], TARGETS), {})

	def test_the_result_is_a_subset_of_the_map_it_was_given(self):
		"""--tier narrows the map first, so scope must never widen it back."""
		tier2 = config.target_map("2")
		selected = scope.changed_targets(list(config.TIER1) + list(tier2), tier2)
		self.assertEqual(list(selected), list(tier2))

	def test_it_works_against_the_real_target_map(self):
		"""One check against reality, so a renamed target is noticed here."""
		real = config.target_map("all")
		source = next(iter(real))
		self.assertEqual(list(scope.changed_targets([source], real)), [source])


class ChangedTargetsWiringTest(unittest.TestCase):
	"""The diff list has to reach ``changed_targets`` from the command line."""

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.tmp = Path(self._tmp.name)

	def write_list(self, paths: list[str]) -> Path:
		path = self.tmp / "changed.txt"
		path.write_text("\n".join(paths) + "\n", encoding="utf-8")
		return path

	def test_the_diff_list_is_read_and_passed_through(self):
		listing = self.write_list(["gameplan/api.py", "frontend/src/main.ts"])
		with mock.patch.object(campaign, "run_campaign", return_value=0) as stub:
			with contextlib.redirect_stdout(io.StringIO()):
				cli.main(["run", "--changed-files-from", str(listing)])
		self.assertEqual(stub.call_args.kwargs["changed_files"], ["gameplan/api.py", "frontend/src/main.ts"])

	def test_no_diff_list_means_no_scoping(self):
		with mock.patch.object(campaign, "run_campaign", return_value=0) as stub:
			with contextlib.redirect_stdout(io.StringIO()):
				cli.main(["run"])
		self.assertIsNone(stub.call_args.kwargs["changed_files"])

	def test_a_missing_diff_list_is_a_usage_error(self):
		"""Not "nothing measured": we were told to scope to a diff we cannot see."""
		with contextlib.redirect_stdout(io.StringIO()):
			code = cli.main(["run", "--changed-files-from", str(self.tmp / "gone.txt")])
		self.assertEqual(code, campaign.EXIT_USAGE)

	def test_the_budget_is_passed_through(self):
		with mock.patch.object(campaign, "run_campaign", return_value=0) as stub:
			with contextlib.redirect_stdout(io.StringIO()):
				cli.main(["run", "--budget-seconds", "2700"])
		self.assertEqual(stub.call_args.kwargs["budget_seconds"], 2700.0)

	def test_the_budget_exit_code_reaches_the_shell(self):
		with mock.patch.object(campaign, "run_campaign", return_value=campaign.EXIT_BUDGET_EXHAUSTED):
			with contextlib.redirect_stdout(io.StringIO()):
				code = cli.main(["run"])
		self.assertEqual(code, campaign.EXIT_BUDGET_EXHAUSTED)

	def test_the_budget_exit_code_is_documented_in_the_help(self):
		help_text = io.StringIO()
		with contextlib.redirect_stdout(help_text):
			with self.assertRaises(SystemExit):
				cli.build_parser().parse_args(["run", "--help"])
		text = help_text.getvalue()
		self.assertIn("--budget-seconds", text)
		self.assertIn(f"  {campaign.EXIT_BUDGET_EXHAUSTED}  ", text)

	def test_a_diff_with_no_targets_succeeds_without_touching_the_working_tree(self):
		"""The common frontend-only pull request: fast, green, and explicit about why."""
		with mock.patch.object(campaign.safety, "CampaignLock") as lock:
			with contextlib.redirect_stdout(io.StringIO()) as out:
				code = campaign.run_campaign(
					tier="all", changed_files=["frontend/src/main.ts"], journal_path=self.tmp / "j.jsonl"
				)
		self.assertEqual(code, campaign.EXIT_OK)
		lock.assert_not_called()
		self.assertIn("nothing to measure", out.getvalue())

	def test_module_and_diff_scoping_together_are_a_usage_error(self):
		with contextlib.redirect_stdout(io.StringIO()):
			code = campaign.run_campaign(only_module="gameplan/api.py", changed_files=["gameplan/api.py"])
		self.assertEqual(code, campaign.EXIT_USAGE)


class ScopeScriptTest(unittest.TestCase):
	"""``scope.py`` must run as a bare script, with no bench and no frappe.

	The pull-request job asks "does this diff touch a mutation target?" before it decides
	whether to spend ten minutes provisioning a bench. ``gameplan/tests/__init__.py``
	imports frappe, so that question cannot be asked through the package. A relative
	import added to scope.py at module level would break this and the only symptom would
	be a red job on every pull request.
	"""

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.tmp = Path(self._tmp.name)
		self.script = Path(scope.__file__).resolve()

	def run_script(self, paths: list[str]) -> subprocess.CompletedProcess:
		listing = self.tmp / "changed.txt"
		listing.write_text("\n".join(paths) + "\n", encoding="utf-8")
		# -I isolates the interpreter (no PYTHONPATH, no user site), and the cwd is a
		# tempdir, so nothing in this repo is importable as a package.
		return subprocess.run(
			[sys.executable, "-I", str(self.script), "--changed-files-from", str(listing)],
			cwd=str(self.tmp),
			capture_output=True,
			text=True,
			timeout=60,
			env={"PATH": os.environ.get("PATH", "")},
		)

	def test_it_prints_the_targets_a_diff_implicates(self):
		source = next(iter(config.target_map("all")))
		result = self.run_script([source, "frontend/src/main.ts"])
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.split(), [source])

	def test_it_prints_nothing_and_succeeds_when_no_target_is_touched(self):
		"""Empty stdout is the "skip the heavy job" signal, so it must stay exit 0."""
		result = self.run_script(["frontend/src/main.ts", "README.md"])
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(result.stdout.strip(), "")


class NewSinceTest(unittest.TestCase):
	"""``report --new-since``: what THIS run added, not what the corpus looks like."""

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.tmp = Path(self._tmp.name)

	def write_journal(self, name: str, keys: list[str], status: str = "killed") -> Path:
		path = self.tmp / name
		with open(path, "w", encoding="utf-8") as handle:
			for key in keys:
				handle.write(json.dumps({"key": key, "module": "pkg/a.py", "status": status}) + "\n")
		return path

	def test_mutants_already_settled_with_the_same_verdict_are_dropped(self):
		baseline = self.write_journal("before.jsonl", ["old1", "old2"])
		records = [
			{"key": "old1", "status": "killed"},
			{"key": "new1", "status": "killed"},
		]
		self.assertEqual(report_mod.only_new_since(records, baseline), [{"key": "new1", "status": "killed"}])

	def test_a_verdict_that_changed_is_kept_even_though_the_key_is_old(self):
		"""Killed yesterday, surviving today: the regression the nightly exists to catch.

		Filtering on the key alone hides it among 500 cumulative survivors - and now that a
		test edit re-measures settled keys, that is the common case rather than a corner.
		"""
		baseline = self.write_journal("before.jsonl", ["old1"], status="killed")
		records = [{"key": "old1", "status": "survived"}]
		self.assertEqual(report_mod.only_new_since(records, baseline), records)

	def test_a_module_skip_is_never_filtered_out(self):
		"""Its key is fixed per module, so "already seen" says nothing about this run.

		Dropping it deletes the only evidence that a changed file was never measured.
		"""
		baseline = self.write_journal("before.jsonl", ["baseline:pkg/a.py"], status="baseline-skip")
		records = [{"key": "baseline:pkg/a.py", "status": "baseline-skip"}]
		self.assertEqual(report_mod.only_new_since(records, baseline), records)

	def test_a_missing_baseline_filters_nothing(self):
		"""A cold or evicted cache must degrade to "report everything", not to silence."""
		records = [{"key": "a"}, {"key": "b"}]
		self.assertEqual(report_mod.only_new_since(records, self.tmp / "absent.jsonl"), records)
		self.assertEqual(report_mod.only_new_since(records, None), records)

	def test_the_report_scores_only_the_new_mutants(self):
		baseline = self.write_journal("before.jsonl", ["old"])
		journal = self.tmp / "journal.jsonl"
		with open(journal, "w", encoding="utf-8") as handle:
			for key, status in (("old", "killed"), ("new", "survived")):
				handle.write(json.dumps({"key": key, "module": "pkg/a.py", "status": status}) + "\n")

		with contextlib.redirect_stderr(io.StringIO()):
			with contextlib.redirect_stdout(io.StringIO()) as out:
				code = report_mod.report(journal_path=journal, fmt="json", new_since=baseline)

		# Parsed whole: the "N of M are new" notice belongs on stderr, or this is a job
		# that pipes a report into json.load and crashes.
		summary = json.loads(out.getvalue())
		self.assertEqual(code, report_mod.EXIT_OK)
		self.assertEqual(
			summary["overall"], {"total": 1, "scored": 1, "unscored": 0, "killed": 0, "score": 0.0}
		)

	def test_nothing_new_is_reported_as_nothing_to_report(self):
		"""No new mutants means no score to report - never a fabricated 0%."""
		baseline = self.write_journal("before.jsonl", ["old"])
		journal = self.write_journal("journal.jsonl", ["old"])
		with contextlib.redirect_stderr(io.StringIO()):
			with contextlib.redirect_stdout(io.StringIO()):
				code = report_mod.report(journal_path=journal, new_since=baseline)
		self.assertEqual(code, report_mod.EXIT_NOTHING_TO_REPORT)
		self.assertNotEqual(code, report_mod.EXIT_OK)
		self.assertNotEqual(code, report_mod.EXIT_NOTHING_MEASURED)


def _workflow(path: Path) -> dict:
	return yaml.safe_load(path.read_text(encoding="utf-8"))


def _steps(workflow: dict) -> list[dict]:
	return [step for job in workflow["jobs"].values() for step in job["steps"]]


def _cache_steps(workflow: dict) -> list[dict]:
	return [step for step in _steps(workflow) if "actions/cache" in step.get("uses", "")]


def _mutation_cache_steps(workflow: dict) -> list[dict]:
	return [step for step in _cache_steps(workflow) if ".mutation" in step["with"]["path"]]


def _cached_entries(step: dict) -> list[str]:
	"""The individual paths a cache step names, as written in the workflow."""
	return [line.strip() for line in step["with"]["path"].strip().splitlines() if line.strip()]


class CachedStateTest(unittest.TestCase):
	"""What the Actions cache is allowed to carry between runners.

	This is the defect that made the nightly self-poisoning. ``.mutation/`` holds three
	kinds of thing: the journals (append-only records of completed work, meaningful
	anywhere), the crash sidecars in ``backup/`` (bound to one working tree and one
	process), and ``campaign.lock`` (bound to one pid on one machine). Caching the
	DIRECTORY carried all three. A nightly killed mid-mutant - job cancel, timeout, OOM -
	left sidecars behind, the ``if: always()`` save cached them, and the next night's fresh
	clone at a different commit found a backup matching neither the file nor the recorded
	mutant. The harness then correctly refused to touch it, ``--yes`` could not override
	that, the campaign exited 1 with a gate message blaming the circuit breaker, and the
	poisoned directory was re-cached every night. It also failed every pull request, and
	nothing self-healed it.

	So: only journal files may be cached, asserted against config.py rather than against
	string literals, so moving the sidecars somewhere else cannot quietly re-open it.
	"""

	def setUp(self) -> None:
		self.nightly = _workflow(NIGHTLY_WORKFLOW)
		self.pr = _workflow(PR_WORKFLOW)

	def cacheable_names(self) -> set[str]:
		return {config.JOURNAL_PATH.name, config.VERIFY_PATH.name}

	def test_both_workflows_cache_journal_files_and_nothing_else(self):
		for name, workflow in (("nightly", self.nightly), ("pr", self.pr)):
			steps = _mutation_cache_steps(workflow)
			self.assertTrue(steps, f"{name} caches no journal at all")
			for step in steps:
				for entry in _cached_entries(step):
					with self.subTest(workflow=name, step=step.get("name"), entry=entry):
						self.assertIn(Path(entry).name, self.cacheable_names())

	def test_the_directory_itself_is_never_cached(self):
		"""Caching the directory is how the sidecars and the lock got in."""
		for workflow in (self.nightly, self.pr):
			for step in _mutation_cache_steps(workflow):
				for entry in _cached_entries(step):
					self.assertNotEqual(Path(entry).name, config.MUTATION_DIR.name)

	def test_no_cached_path_can_contain_a_crash_sidecar_or_the_lock(self):
		"""The property, stated the way it actually matters: could this payload hold one?"""
		forbidden = {config.BACKUP_DIR.name, config.LOCK_PATH.name}
		for workflow in (self.nightly, self.pr):
			for step in _mutation_cache_steps(workflow):
				for entry in _cached_entries(step):
					parts = set(Path(entry).parts)
					self.assertEqual(parts & forbidden, set(), entry)
					# A file path cannot contain anything; a directory could.
					self.assertTrue(Path(entry).suffix, f"{entry} is not a file")

	def test_the_backup_directory_and_lock_really_do_live_under_the_mutation_directory(self):
		"""Fixes the test to reality: without this the assertions above prove nothing."""
		self.assertEqual(config.BACKUP_DIR.parent, config.MUTATION_DIR)
		self.assertEqual(config.LOCK_PATH.parent, config.MUTATION_DIR)
		self.assertEqual(config.JOURNAL_PATH.parent, config.MUTATION_DIR)

	def test_the_nightly_saves_exactly_what_it_restores(self):
		steps = _mutation_cache_steps(self.nightly)
		restore = [s for s in steps if "restore" in s["uses"]]
		save = [s for s in steps if "save" in s["uses"]]
		self.assertEqual(len(restore), 1)
		self.assertEqual(len(save), 1)
		self.assertEqual(_cached_entries(restore[0]), _cached_entries(save[0]))
		# The rolling key: save writes the key the restore could not possibly have hit,
		# which is what makes the prefix match return last night's cache instead of a hit
		# that skips the save.
		self.assertEqual(restore[0]["with"]["key"], save[0]["with"]["key"])
		self.assertIn("run_id", restore[0]["with"]["key"])

	def test_a_pull_request_never_writes_the_nightly_cache(self):
		saves = [s for s in _cache_steps(self.pr) if "save" in s["uses"]]
		self.assertEqual(saves, [])

	def test_the_pull_request_lookup_key_is_outside_the_nightly_prefix(self):
		"""Or adding a save step here later silently hands PR journals to the nightly."""
		prefix = self.nightly["env"]["JOURNAL_CACHE_PREFIX"]
		self.assertEqual(prefix, self.pr["env"]["JOURNAL_CACHE_PREFIX"])
		for step in _mutation_cache_steps(self.pr):
			self.assertNotIn(prefix, step["with"]["key"])
			self.assertNotIn("JOURNAL_CACHE_PREFIX", step["with"]["key"])
			# ...while still READING the nightly's lineage.
			self.assertIn("JOURNAL_CACHE_PREFIX", step["with"]["restore-keys"])

	def test_the_cache_lineage_was_abandoned_rather_than_inherited(self):
		"""v1 caches may hold sidecars from before this fix; they must never be restored."""
		self.assertNotIn("v1", self.nightly["env"]["JOURNAL_CACHE_PREFIX"])


class SignalRestoreDropsTheSidecarTest(unittest.TestCase):
	"""``restore_all`` is what a cancelled job runs, and it must leave nothing behind.

	The sidecar exists to undo a mutation nobody else can undo. Once ``restore`` has put
	the file back and proved it byte for byte, that job is done - and a leftover manifest
	is then indistinguishable from a real crash to the next run, which is what wedged the
	nightly. If the restore FAILS, the sidecar is still the only copy of the original and
	is kept.
	"""

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.tmp = Path(self._tmp.name)
		self.backup_dir = self.tmp / "backup"
		self.backup_dir.mkdir()
		patcher = mock.patch.object(safety, "BACKUP_DIR", self.backup_dir)
		patcher.start()
		self.addCleanup(patcher.stop)
		self.source = self.tmp / "target.py"
		self.source.write_text(ORIGINAL, encoding="utf-8")

	def mutated_guard(self) -> safety.FileGuard:
		guard = safety.FileGuard(self.source)
		guard.install_backup()
		guard.apply(ORIGINAL.replace(">", ">="))
		safety.register(guard)
		self.addCleanup(safety.unregister, guard)
		return guard

	def test_it_restores_the_file(self):
		self.mutated_guard()
		with contextlib.redirect_stderr(io.StringIO()):
			safety.restore_all()
		self.assertEqual(self.source.read_text(), ORIGINAL)

	def test_it_leaves_no_sidecar_for_the_next_run_to_trip_over(self):
		self.mutated_guard()
		with contextlib.redirect_stderr(io.StringIO()):
			safety.restore_all()
		self.assertEqual(list(self.backup_dir.iterdir()), [])
		self.assertEqual(safety.find_orphaned_backups(), [])

	def test_a_later_edit_to_the_file_no_longer_wedges_anything(self):
		"""The exact scenario: interrupted run, then the source moves on (a new commit).

		With the sidecar still on disk this is what ``check_orphans`` classifies "unknown"
		and refuses - permanently, and with ``--yes`` powerless to override it.
		"""
		self.mutated_guard()
		with contextlib.redirect_stderr(io.StringIO()):
			safety.restore_all()
		self.source.write_text(ORIGINAL + "\n# a later commit\n", encoding="utf-8")

		with contextlib.redirect_stdout(io.StringIO()) as out:
			self.assertTrue(campaign.check_orphans(assume_yes=True))
		self.assertNotIn("refusing", out.getvalue())

	def test_a_failed_restore_keeps_the_sidecar(self):
		"""The one case where the backup is still the only copy of the original."""
		guard = self.mutated_guard()
		with mock.patch.object(safety.FileGuard, "restore", side_effect=safety.RestoreError("disk is full")):
			with contextlib.redirect_stderr(io.StringIO()) as err:
				safety.restore_all()
		self.assertIn("CRITICAL", err.getvalue())
		self.assertTrue(guard.backup_path.exists())
		self.assertTrue(guard.manifest_path.exists())


class TestFingerprintTest(unittest.TestCase):
	"""``scope.test_fingerprint``: the provenance stamped on every verdict."""

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.root = Path(self._tmp.name)
		self.write("tests.test_alpha", "def test_a():\n\tassert True\n")
		self.write("tests.test_beta", "def test_b():\n\tassert True\n")

	def write(self, dotted: str, body: str) -> Path:
		path = self.root / (dotted.replace(".", "/") + ".py")
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(body, encoding="utf-8")
		return path

	def test_it_is_stable_for_unchanged_files(self):
		first = scope.test_fingerprint(["tests.test_alpha"], self.root)
		self.assertEqual(first, scope.test_fingerprint(["tests.test_alpha"], self.root))

	def test_editing_a_mapped_test_changes_it(self):
		before = scope.test_fingerprint(["tests.test_alpha"], self.root)
		self.write("tests.test_alpha", "def test_a():\n\tpass\n")
		self.assertNotEqual(before, scope.test_fingerprint(["tests.test_alpha"], self.root))

	def test_editing_an_unmapped_test_does_not(self):
		before = scope.test_fingerprint(["tests.test_alpha"], self.root)
		self.write("tests.test_beta", "def test_b():\n\tpass\n")
		self.assertEqual(before, scope.test_fingerprint(["tests.test_alpha"], self.root))

	def test_two_modules_with_different_tests_differ(self):
		self.assertNotEqual(
			scope.test_fingerprint(["tests.test_alpha"], self.root),
			scope.test_fingerprint(["tests.test_beta"], self.root),
		)

	def test_it_covers_every_mapped_module_not_just_the_first(self):
		before = scope.test_fingerprint(["tests.test_alpha", "tests.test_beta"], self.root)
		self.write("tests.test_beta", "def test_b():\n\tpass\n")
		self.assertNotEqual(
			before, scope.test_fingerprint(["tests.test_alpha", "tests.test_beta"], self.root)
		)

	def test_order_does_not_matter(self):
		self.assertEqual(
			scope.test_fingerprint(["tests.test_alpha", "tests.test_beta"], self.root),
			scope.test_fingerprint(["tests.test_beta", "tests.test_alpha"], self.root),
		)

	def test_a_missing_test_module_hashes_rather_than_raising(self):
		"""config.py can name a module that was renamed away; that invalidates, not crashes."""
		digest = scope.test_fingerprint(["tests.test_gone"], self.root)
		self.assertNotEqual(digest, scope.test_fingerprint(["tests.test_alpha"], self.root))


class SettledVerdictStalenessTest(unittest.TestCase):
	"""``completed_keys`` only calls a verdict done while its tests are unchanged."""

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.journal = Path(self._tmp.name) / "journal.jsonl"

	def write(self, records: list[dict]) -> None:
		with open(self.journal, "w", encoding="utf-8") as handle:
			for record in records:
				handle.write(json.dumps(record, sort_keys=True) + "\n")

	def test_a_matching_fingerprint_is_settled(self):
		self.write([{"key": "k1", "module": "pkg/a.py", "status": "killed", "tests_sha": "aaa"}])
		self.assertEqual(journal_mod.completed_keys(self.journal, fingerprints={"pkg/a.py": "aaa"}), {"k1"})

	def test_a_changed_fingerprint_is_stale(self):
		self.write([{"key": "k1", "module": "pkg/a.py", "status": "killed", "tests_sha": "aaa"}])
		self.assertEqual(journal_mod.completed_keys(self.journal, fingerprints={"pkg/a.py": "bbb"}), set())

	def test_a_record_without_provenance_is_stale(self):
		"""Written before verdicts carried their provenance: we cannot show what produced it."""
		self.write([{"key": "k1", "module": "pkg/a.py", "status": "killed"}])
		self.assertEqual(journal_mod.completed_keys(self.journal, fingerprints={"pkg/a.py": "aaa"}), set())

	def test_only_the_module_whose_tests_changed_is_invalidated(self):
		self.write(
			[
				{"key": "a1", "module": "pkg/a.py", "status": "killed", "tests_sha": "aaa"},
				{"key": "b1", "module": "pkg/b.py", "status": "killed", "tests_sha": "bbb"},
			]
		)
		done = journal_mod.completed_keys(
			self.journal, fingerprints={"pkg/a.py": "CHANGED", "pkg/b.py": "bbb"}
		)
		self.assertEqual(done, {"b1"})

	def test_a_module_outside_the_run_is_left_alone(self):
		"""No current fingerprint for it means no evidence it is stale."""
		self.write([{"key": "k1", "module": "pkg/other.py", "status": "killed"}])
		self.assertEqual(journal_mod.completed_keys(self.journal, fingerprints={"pkg/a.py": "aaa"}), {"k1"})

	def test_without_fingerprints_nothing_is_invalidated(self):
		"""The verify stage runs the full suite, so a per-module fingerprint means nothing."""
		self.write([{"key": "k1", "module": "pkg/a.py", "status": "killed"}])
		self.assertEqual(journal_mod.completed_keys(self.journal), {"k1"})

	def test_a_retryable_status_is_still_retried_regardless(self):
		self.write([{"key": "k1", "module": "pkg/a.py", "status": "timeout", "tests_sha": "aaa"}])
		self.assertEqual(
			journal_mod.completed_keys(
				self.journal,
				exclude_statuses=config.RETRYABLE_STATUSES,
				fingerprints={"pkg/a.py": "aaa"},
			),
			set(),
		)


class TestEditReMeasuresTheRightModuleTest(CampaignLoopTestCase):
	"""End to end: edit one test file, and exactly that module is measured again.

	Without this the nightly is theatre. Mutant keys come from the source AST, so deleting
	an assertion changes no key: every "killed" stays settled for ever, the module
	short-circuits before its baseline, and the job republishes yesterday's score having
	run nothing - looking greener and doing less work every night.
	"""

	def setUp(self) -> None:
		super().setUp()
		self.targets = {}
		for name in ("alpha", "beta"):
			self.write_target(f"pkg/{name}.py", ORIGINAL)
			self.write_test_module(f"tests.test_{name}", "def test_x():\n\tassert True\n")
			self.targets[f"pkg/{name}.py"] = [f"tests.test_{name}"]

	def write_test_module(self, dotted: str, body: str) -> Path:
		path = self.app_root / (dotted.replace(".", "/") + ".py")
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(body, encoding="utf-8")
		return path

	def modules_measured(self, before: int) -> list[str]:
		return [record["module"] for record in mutant_records(self.journal_records()[before:])]

	def test_a_settled_corpus_measures_nothing_when_nothing_changed(self):
		self.run_campaign(self.targets)
		self.run_campaign(self.targets)
		self.assertEqual(self.evaluated_sources, [])

	def test_deleting_an_assertion_re_measures_that_module(self):
		self.run_campaign(self.targets)
		mark = len(self.journal_records())

		self.write_test_module("tests.test_alpha", "def test_x():\n\tpass\n")
		self.run_campaign(self.targets)

		self.assertTrue(self.evaluated_sources, "the edited module was not re-measured")
		self.assertEqual(set(self.modules_measured(mark)), {"pkg/alpha.py"})

	def test_the_other_module_is_not_re_measured(self):
		"""The cost is bounded: one module's tests, one module's verdicts."""
		self.run_campaign(self.targets)
		mark = len(self.journal_records())

		self.write_test_module("tests.test_alpha", "def test_x():\n\tpass\n")
		self.run_campaign(self.targets)

		self.assertNotIn("pkg/beta.py", self.modules_measured(mark))

	def test_every_mutant_of_the_edited_module_is_re_measured(self):
		self.run_campaign(self.targets)
		mark = len(self.journal_records())
		expected = len(mutators.collect_sites(ORIGINAL, "pkg/alpha.py"))

		self.write_test_module("tests.test_alpha", "def test_x():\n\tpass\n")
		self.run_campaign(self.targets)

		self.assertEqual(len(self.modules_measured(mark)), expected)

	def test_re_measuring_pays_for_the_baseline_again(self):
		"""A verdict is only as good as the baseline behind it, so it must be re-proven."""
		self.run_campaign(self.targets)
		self.write_test_module("tests.test_alpha", "def test_x():\n\tpass\n")
		with mock.patch.object(campaign, "_baseline_ok", return_value=(True, "")) as baseline:
			with mock.patch.object(
				campaign, "_evaluate_mutant", lambda *_a, **_k: (config.STATUS_KILLED, "t", 0.0)
			):
				with contextlib.redirect_stdout(io.StringIO()):
					campaign._run_campaign_locked(
						targets=self.targets,
						site="unused.test",
						timeout=1,
						limit=None,
						mutate_strings=False,
						assume_yes=True,
						journal_path=self.journal,
					)
		self.assertEqual(baseline.call_count, 1)

	def test_the_verdict_carries_the_fingerprint_that_produced_it(self):
		self.run_campaign(self.targets)
		expected = scope.test_fingerprint(["tests.test_alpha"], self.app_root)
		alpha = [r for r in self.journal_records() if r["module"] == "pkg/alpha.py"]
		self.assertTrue(alpha)
		for record in alpha:
			self.assertEqual(record["tests_sha"], expected)


class SkippedModuleVisibilityTest(CampaignLoopTestCase):
	"""Every way a module can drop out has to be visible in the journal AND the report.

	The exit code cannot carry this: it only fails when EVERY module was skipped, so a
	renamed target sits there unmeasured for ever - green job, stale verdicts still
	counting toward the published score, one line of stdout nobody reads.
	"""

	def summary(self) -> dict:
		return report_mod.summarise(report_mod.load_results(self.journal))

	def test_a_missing_source_file_is_journalled(self):
		self.run_campaign({"pkg/gone.py": ["tests.test_gone"]})
		records = self.journal_records()
		self.assertEqual([r["status"] for r in records], [config.STATUS_MODULE_SKIP])
		self.assertIn("does not exist", records[0]["reason"])

	def test_a_missing_source_file_reaches_the_report(self):
		self.run_campaign({"pkg/gone.py": ["tests.test_gone"]})
		skipped = self.summary()["skipped_modules"]
		self.assertIn("pkg/gone.py", skipped)
		self.assertEqual(skipped["pkg/gone.py"]["kind"], "not measurable")

	def test_a_guard_failure_is_journalled_and_reported(self):
		self.write_target("pkg/alpha.py", ORIGINAL)
		with mock.patch.object(campaign, "_guard_for", side_effect=OSError("permission denied")):
			self.run_campaign({"pkg/alpha.py": ["tests.test_alpha"]})
		self.assertIn("pkg/alpha.py", self.summary()["skipped_modules"])
		self.assertIn("permission denied", self.journal_records()[0]["reason"])

	def test_a_red_baseline_is_reported_as_a_red_baseline(self):
		"""The three causes stay distinguishable; only "measured nothing" is shared."""
		self.write_target("pkg/alpha.py", ORIGINAL)
		self.run_campaign({"pkg/alpha.py": ["tests.test_alpha"]}, baseline=(False, "site is down"))
		skipped = self.summary()["skipped_modules"]
		self.assertEqual(skipped["pkg/alpha.py"]["kind"], "red baseline")
		self.assertIn("site is down", skipped["pkg/alpha.py"]["reason"])

	def test_a_partially_skipped_run_is_green_but_the_report_is_not_silent(self):
		"""Exactly the hole: exit 0, and the only trace used to be a line of stdout."""
		self.write_target("pkg/alpha.py", ORIGINAL)
		code = self.run_campaign({"pkg/alpha.py": ["tests.test_alpha"], "pkg/gone.py": ["tests.test_gone"]})
		self.assertEqual(code, campaign.EXIT_OK)
		self.assertEqual(list(self.summary()["skipped_modules"]), ["pkg/gone.py"])

	def test_the_skip_names_the_module_and_the_reason_on_stdout_too(self):
		self.run_campaign({"pkg/gone.py": ["tests.test_gone"]})
		self.assertIn("pkg/gone.py", self.output)
		self.assertIn("without updating config.py", self.output)

	def test_a_skip_never_becomes_a_module_with_a_score(self):
		"""It is not a mutant and must never render as one, not even as "n/a"."""
		self.run_campaign({"pkg/gone.py": ["tests.test_gone"]})
		self.assertEqual(self.summary()["modules"], {})

	def test_measuring_the_module_again_clears_the_skip(self):
		"""Or the gate stays red for ever after the cause is fixed."""
		self.run_campaign({"pkg/alpha.py": ["tests.test_alpha"]}, baseline=(False, "site is down"))
		self.write_target("pkg/alpha.py", ORIGINAL)
		self.run_campaign({"pkg/alpha.py": ["tests.test_alpha"]})
		self.assertEqual(self.summary()["skipped_modules"], {})

	def test_a_skipped_module_is_not_pushed_to_the_back_of_the_rotation(self):
		"""The skip record must not read as "recently measured"; it is the opposite."""
		records = [
			{"module": "a.py", "status": config.STATUS_KILLED},
			{"module": "b.py", "status": config.STATUS_KILLED},
			{"module": "a.py", "status": config.STATUS_BASELINE_SKIP},
		]
		positions = scope.last_measured_positions(records, ignore_statuses=config.SKIP_STATUSES)
		self.assertEqual(scope.round_robin_order(["a.py", "b.py"], positions), ["a.py", "b.py"])


class StaleCorpusTest(unittest.TestCase):
	"""Verdicts about code that no longer exists must not stay in the published score."""

	SOURCE = "def f(a, b):\n\treturn a > b\n"

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.root = Path(self._tmp.name)
		(self.root / "pkg").mkdir()
		(self.root / "pkg" / "a.py").write_text(self.SOURCE, encoding="utf-8")
		self.sites = mutators.collect_sites(self.SOURCE, "pkg/a.py", mutate_strings=True)

	def record(self, key: str, status: str = "killed") -> dict:
		return {"key": key, "module": "pkg/a.py", "file": "pkg/a.py", "status": status}

	def test_a_live_site_is_kept(self):
		kept, dropped = report_mod.drop_stale_sites([self.record(self.sites[0].key)], self.root)
		self.assertEqual(len(kept), 1)
		self.assertEqual(dropped, 0)

	def test_a_key_that_matches_no_current_site_is_dropped(self):
		kept, dropped = report_mod.drop_stale_sites([self.record("nolongerexists")], self.root)
		self.assertEqual(kept, [])
		self.assertEqual(dropped, 1)

	def test_a_file_that_cannot_be_read_keeps_all_of_its_records(self):
		""" "I could not check" must never be resolved into "these results are stale"."""
		record = dict(self.record("whatever"), file="pkg/missing.py", module="pkg/missing.py")
		kept, dropped = report_mod.drop_stale_sites([record], self.root)
		self.assertEqual(kept, [record])
		self.assertEqual(dropped, 0)

	def test_an_unparseable_file_keeps_all_of_its_records(self):
		(self.root / "pkg" / "broken.py").write_text("def (:\n", encoding="utf-8")
		record = dict(self.record("whatever"), file="pkg/broken.py", module="pkg/broken.py")
		kept, _dropped = report_mod.drop_stale_sites([record], self.root)
		self.assertEqual(kept, [record])

	def test_module_skips_are_always_kept(self):
		record = self.record("baseline:pkg/a.py", status=config.STATUS_MODULE_SKIP)
		kept, _dropped = report_mod.drop_stale_sites([record], self.root)
		self.assertEqual(kept, [record])

	def test_pruning_changes_the_published_score(self):
		"""The point of it: a stale kill inflates the number a human reads."""
		records = [
			self.record(self.sites[0].key, status="survived"),
			self.record("deleted-code-that-was-killed", status="killed"),
		]
		self.assertEqual(report_mod.summarise(records)["overall"]["score"], 0.5)
		kept, _ = report_mod.drop_stale_sites(records, self.root)
		self.assertEqual(report_mod.summarise(kept)["overall"]["score"], 0.0)


class BudgetSpentBeforeAnythingWasMeasuredTest(CampaignLoopTestCase):
	"""A whole allowance burned without one verdict is a broken site, not a budget stop."""

	def run_with_expired_budget(self, targets: dict[str, list[str]], budget_seconds: float) -> int:
		clock = FakeClock()
		budget = scope.Budget(budget_seconds, clock=clock)
		# Setup (orphan recovery, the git check, a slow provisioning step) ate the lot
		# before the loop ever looked at a module.
		clock.advance(budget_seconds + 1)
		with mock.patch.object(campaign, "_baseline_ok", return_value=(True, "")):
			with contextlib.redirect_stdout(io.StringIO()) as out:
				code = campaign._run_campaign_locked(
					targets=targets,
					site="unused.test",
					timeout=1,
					limit=None,
					mutate_strings=False,
					assume_yes=True,
					journal_path=self.journal,
					budget=budget,
				)
		self.output = out.getvalue()
		return code

	def test_it_does_not_report_a_healthy_budget_stop(self):
		"""``pending`` is 0 only because the loop never reached a module to count one."""
		self.write_target("pkg/alpha.py", ORIGINAL)
		code = self.run_with_expired_budget({"pkg/alpha.py": ["tests.test_alpha"]}, 2700)
		self.assertEqual(code, campaign.EXIT_NOTHING_MEASURED)
		self.assertNotEqual(code, campaign.EXIT_BUDGET_EXHAUSTED)
		self.assertEqual(self.journal_records(), [])

	def test_an_explicit_zero_budget_is_still_an_explicit_request_to_do_nothing(self):
		self.write_target("pkg/alpha.py", ORIGINAL)
		code = self.run_with_expired_budget({"pkg/alpha.py": ["tests.test_alpha"]}, 0)
		self.assertEqual(code, campaign.EXIT_BUDGET_EXHAUSTED)


class PullRequestJobClaimsTest(unittest.TestCase):
	"""The pull-request job must not turn "I measured nothing" into a fact about the code.

	``report`` returns non-zero for three different reasons and the job used to answer all
	three with "the pull request did not change any mutable behaviour in them". Two of
	those are false: exit 3 means every new mutant produced a NON-verdict (one hung mutant
	used to eat the entire budget, since --timeout equalled --budget-seconds), and a
	crashed report means nothing was measured at all.
	"""

	def setUp(self) -> None:
		self.pr = _workflow(PR_WORKFLOW)
		self.report_step = next(step for step in _steps(self.pr) if step.get("name") == "Publish the report")
		self.gate_step = next(
			step for step in _steps(self.pr) if step.get("name") == "Gate on the mutation signal"
		)

	def case_arm(self, script: str, label: str) -> str:
		"""The body of one `case` arm, from its label to the `;;` that closes it."""
		head = script.index(f"{label})")
		return script[head : script.index(";;", head)]

	def test_the_three_outcomes_have_three_separate_arms(self):
		script = self.report_step["run"]
		for label in ("0", "5", "3", "*"):
			self.assertIn(f"{label})", script)

	def test_no_arm_claims_anything_about_mutants_that_were_not_evaluated(self):
		"""The empty-result arm used to generalise from a sample to the whole diff.

		A pull request that edits a mapped test module invalidates every verdict of the
		module behind it; the run then re-measures as many as its 10-minute budget allows -
		20 of 273, say - and if they all agree with the journal the report is empty. The old
		text answered that with "the pull request did not change any mutable behaviour in
		them", a claim over 273 mutants earned on 20, printed directly above the note saying
		the run was cut off by its budget.
		"""
		script = self.report_step["run"]
		self.assertNotIn("did not change any mutable behaviour", script)
		self.assertIn("every mutant this run reached", self.case_arm(script, "5"))

	def test_the_summary_says_what_the_run_actually_did(self):
		"""Without it, "no new verdicts" and "the campaign never ran" render identically."""
		script = self.report_step["run"]
		self.assertIn("mutation work", script)
		self.assertIn('echo "${work}"', script)

	def test_the_no_verdict_case_says_so(self):
		self.assertIn("No verdict", self.case_arm(self.report_step["run"], "3"))

	def test_the_crashed_report_case_says_so(self):
		arm = self.case_arm(self.report_step["run"], "*")
		self.assertIn("report itself failed", arm)

	def test_the_exit_codes_the_workflow_branches_on_are_the_ones_report_returns(self):
		"""Pins the shell to the Python: renumbering either alone breaks this."""
		self.assertEqual(report_mod.EXIT_NOTHING_TO_REPORT, 5)
		self.assertEqual(report_mod.EXIT_NOTHING_MEASURED, 3)
		self.assertEqual(report_mod.EXIT_OK, 0)

	def test_the_pull_request_job_gates_on_skipped_modules(self):
		"""The nightly had this gate and the pull-request job did not."""
		self.assertIn("skipped_modules", self.gate_step["run"])

	def test_the_budget_is_comfortably_larger_than_one_mutant_timeout(self):
		"""Equal values mean one hung module consumes the whole allowance by construction."""
		script = next(
			step["run"] for step in _steps(self.pr) if step.get("name") == "Mutate the changed targets"
		)
		timeout = int(script.split("--timeout")[1].split()[0])
		budget = int(script.split("--budget-seconds")[1].split()[0])
		self.assertLess(timeout * 2, budget)


class NightlyGateHonestyTest(unittest.TestCase):
	"""The nightly's gate may not diagnose a cause it has not established."""

	def setUp(self) -> None:
		self.nightly = _workflow(NIGHTLY_WORKFLOW)
		self.gate = next(
			step["run"] for step in _steps(self.nightly) if step.get("name") == "Gate on the mutation signal"
		)

	def test_exit_one_does_not_blame_the_circuit_breaker_alone(self):
		"""Exit 1 is also an orphaned backup, a held lock, or a dirty target file."""
		arm = self.gate[self.gate.index("1)") : self.gate.index(";;", self.gate.index("1)"))]
		self.assertIn("aborted or refused to start", arm)
		for cause in ("circuit breaker", "orphaned backup", "lock", "uncommitted changes"):
			self.assertIn(cause, arm)

	def test_it_gates_on_every_kind_of_skip(self):
		self.assertIn("skipped_modules", self.gate)

	def test_the_summary_states_the_budget_it_actually_used(self):
		"""A manually dispatched short run must not read like a normal night."""
		publish = next(
			step["run"] for step in _steps(self.nightly) if step.get("name") == "Publish the report"
		)
		self.assertIn("Budget:", publish)

	def test_the_summary_shows_what_changed_rather_than_the_whole_corpus(self):
		publish = next(
			step["run"] for step in _steps(self.nightly) if step.get("name") == "Publish the report"
		)
		self.assertIn("--new-since", publish)
		self.assertIn("Decided tonight", publish)


class ModuleCurrencyIsDataTest(unittest.TestCase):
	"""A skip is reported IF AND ONLY IF it describes the module as it is now.

	Under any filtering. That "under any filtering" is the whole test class, because the
	defect it pins was not in what the report decided but in WHERE it decided it. Currency
	used to be inferred from journal position - "a mutant record further down means this
	skip is old" - and every caller is free to filter the list that position is measured
	over. ``--new-since`` keeps skips (deliberately: they are the evidence a changed file
	was never measured) and drops settled mutants, i.e. it removes exactly the evidence
	that ages a skip out. So one red baseline anywhere in the nightly journal made every
	pull request red, for a module the pull request never touched, with a reason from weeks
	ago - while the nightly's own cumulative report insisted nothing was skipped, so
	nothing pointed at the cause. Nothing could clear it either: the key is fixed per
	module, so the record is immortal.

	The fix is that currency is now a FACT in the journal - a module that has a current
	score says so under the skip's own key - settled once against the complete journal and
	only read thereafter. These tests pin the property, not the mechanism: cumulative and
	filtered views must agree, whatever the filter.
	"""

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.tmp = Path(self._tmp.name)
		self.journal = self.tmp / "journal.jsonl"

	def skip_record(self, module: str = "pkg/a.py", reason: str = "tests were red") -> dict:
		return {
			"key": f"baseline:{module}",
			"module": module,
			"file": module,
			"status": config.STATUS_BASELINE_SKIP,
			"reason": reason,
		}

	def current_record(self, module: str = "pkg/a.py") -> dict:
		return {
			"key": f"baseline:{module}",
			"module": module,
			"file": module,
			"status": config.STATUS_MODULE_CURRENT,
			"reason": "baseline green",
		}

	def mutant(self, key: str, module: str = "pkg/a.py", status: str = config.STATUS_KILLED) -> dict:
		return {"key": key, "module": module, "file": module, "status": status}

	def write(self, records: list[dict], name: str = "journal.jsonl") -> Path:
		path = self.tmp / name
		with open(path, "w", encoding="utf-8") as handle:
			for record in records:
				handle.write(json.dumps(record, sort_keys=True) + "\n")
		return path

	def skipped(self, records: list[dict]) -> dict:
		return report_mod.summarise(records)["skipped_modules"]

	def test_a_measurement_after_the_skip_retires_it(self):
		journal = self.write([self.skip_record(), self.mutant("k1"), self.mutant("k2")])
		self.assertEqual(self.skipped(report_mod.load_results(journal)), {})

	def test_the_filtered_view_agrees_with_the_cumulative_one(self):
		"""The defect, stated as the property it broke. Both views, one answer."""
		journal = self.write([self.skip_record(), self.mutant("k1"), self.mutant("k2")])
		before = self.write([self.skip_record(), self.mutant("k1"), self.mutant("k2")], "before.jsonl")

		cumulative = report_mod.load_results(journal)
		filtered = report_mod.only_new_since(cumulative, before)

		self.assertEqual(self.skipped(cumulative), {})
		self.assertEqual(self.skipped(filtered), {})

	def test_a_skip_that_is_still_current_survives_both_views(self):
		"""The other half: retiring a live skip would hide an unmeasured module."""
		journal = self.write([self.mutant("k1"), self.skip_record()])
		before = self.write([self.mutant("k1"), self.skip_record()], "before.jsonl")

		cumulative = report_mod.load_results(journal)
		filtered = report_mod.only_new_since(cumulative, before)

		self.assertEqual(list(self.skipped(cumulative)), ["pkg/a.py"])
		self.assertEqual(self.skipped(cumulative), self.skipped(filtered))

	def test_a_current_score_record_retires_the_skip_by_key(self):
		"""The forward mechanism: one key per module, last record wins, no ordering guess."""
		journal = self.write([self.skip_record(), self.current_record()])
		records = report_mod.load_results(journal)
		self.assertEqual(self.skipped(records), {})
		self.assertEqual([r["status"] for r in records], [config.STATUS_MODULE_CURRENT])

	def test_a_skip_after_a_current_score_record_still_wins(self):
		"""Same key, and the later record is the module's state. Order matters HERE only."""
		journal = self.write([self.current_record(), self.skip_record()])
		self.assertEqual(list(self.skipped(report_mod.load_results(journal))), ["pkg/a.py"])

	def test_pruning_every_mutant_record_cannot_resurrect_a_skip(self):
		"""N2: --prune-stale over a rewritten module used to delete the retiring evidence."""
		source_root = self.tmp / "app"
		(source_root / "pkg").mkdir(parents=True)
		(source_root / "pkg" / "a.py").write_text("def f(a, b):\n\treturn a > b\n", encoding="utf-8")
		journal = self.write(
			[self.skip_record(), self.mutant("gone-1"), self.mutant("gone-2"), self.current_record()]
		)

		records = report_mod.load_results(journal)
		pruned, dropped = report_mod.drop_stale_sites(records, source_root)

		self.assertEqual(dropped, 2, "the module was rewritten; its old verdicts are stale")
		self.assertEqual(self.skipped(pruned), {})

	def test_summarise_does_not_read_currency_out_of_the_list_it_is_given(self):
		"""Handed a skip and nothing else, it reports it; the ordering logic is gone."""
		self.assertEqual(list(self.skipped([self.skip_record()])), ["pkg/a.py"])
		self.assertEqual(self.skipped([self.current_record()]), {})

	def test_a_skip_never_becomes_a_scored_module(self):
		summary = report_mod.summarise([self.skip_record(), self.current_record("pkg/b.py")])
		self.assertEqual(summary["modules"], {})
		self.assertEqual(summary["overall"]["total"], 0)

	def test_the_verify_stage_cannot_retire_a_skip(self):
		"""Stage 2 re-runs old survivors; it says nothing about today's baseline."""
		journal = self.write([self.mutant("k1"), self.skip_record()])
		verify = self.write([self.mutant("k1", status=config.STATUS_KILLED_BY_OTHER_SUITE)], "v.jsonl")
		records = report_mod.load_results(journal, verify)
		self.assertEqual(list(self.skipped(records)), ["pkg/a.py"])


class ModuleCurrencyInTheLoopTest(CampaignLoopTestCase):
	"""The campaign has to WRITE the fact that a module's score is current.

	Every path that leaves a module measurable must say so under the skip's own key, or a
	skip journalled once is a skip for ever - and the gate reads skips.
	"""

	def module_records(self, module: str) -> list[dict]:
		return [
			record
			for record in self.journal_records()
			if record["module"] == module and record["status"] in config.MODULE_STATUSES
		]

	def summary(self) -> dict:
		return report_mod.summarise(report_mod.load_results(self.journal))

	def test_a_green_baseline_records_that_the_module_has_a_current_score(self):
		self.write_target("pkg/alpha.py", ORIGINAL)
		self.run_campaign({"pkg/alpha.py": ["tests.test_alpha"]})
		self.assertEqual(
			[r["status"] for r in self.module_records("pkg/alpha.py")], [config.STATUS_MODULE_CURRENT]
		)

	def test_a_module_with_nothing_pending_records_it_too(self):
		"""The one that closes the loop: a settled module never runs a baseline again.

		Without a record here, a module that was skipped once and then has every mutant
		settled short-circuits before the baseline for ever, so nothing can ever clear the
		skip and the gate is red until a human deletes the journal.
		"""
		self.write_target("pkg/alpha.py", ORIGINAL)
		self.run_campaign({"pkg/alpha.py": ["tests.test_alpha"]})
		self.run_campaign({"pkg/alpha.py": ["tests.test_alpha"]})
		self.assertEqual(self.evaluated_sources, [], "nothing should have been re-measured")
		self.assertEqual(len(self.module_records("pkg/alpha.py")), 2)
		self.assertEqual(self.module_records("pkg/alpha.py")[-1]["status"], config.STATUS_MODULE_CURRENT)

	def test_a_skip_clears_even_when_there_is_nothing_left_to_measure(self):
		"""The self-sustaining case, end to end: settled module, skip, fix, still cleared.

		A module whose every mutant is settled never runs a baseline again, so the skip
		journalled while its source was missing has no later mutant record to age it out.
		Only the "score is current" record can retire it, and this is the run that writes
		one.
		"""
		path = self.write_target("pkg/alpha.py", ORIGINAL)
		targets = {"pkg/alpha.py": ["tests.test_alpha"]}
		self.run_campaign(targets)  # settles every mutant

		path.unlink()  # a rename config.py did not follow
		self.run_campaign(targets)
		self.assertEqual(list(self.summary()["skipped_modules"]), ["pkg/alpha.py"])

		self.write_target("pkg/alpha.py", ORIGINAL)  # put back; nothing is pending
		self.run_campaign(targets)

		self.assertEqual(self.evaluated_sources, [], "nothing was pending, so nothing ran")
		self.assertEqual(self.summary()["skipped_modules"], {})

	def test_the_cleared_skip_stays_cleared_in_a_filtered_report(self):
		"""What a pull request seeded from this journal sees. Same answer, or it is red."""
		self.write_target("pkg/alpha.py", ORIGINAL)
		targets = {"pkg/alpha.py": ["tests.test_alpha"]}
		self.run_campaign(targets, baseline=(False, "site is down"))
		self.run_campaign(targets)

		records = report_mod.load_results(self.journal)
		filtered = report_mod.only_new_since(records, self.journal)

		self.assertEqual(report_mod.summarise(records)["skipped_modules"], {})
		self.assertEqual(report_mod.summarise(filtered)["skipped_modules"], {})

	def test_a_module_record_does_not_push_the_module_down_the_rotation(self):
		"""It is a statement, not a measurement: a budget stop must not cost a rotation."""
		records = [
			{"module": "a.py", "status": config.STATUS_KILLED},
			{"module": "b.py", "status": config.STATUS_KILLED},
			{"module": "a.py", "status": config.STATUS_MODULE_CURRENT},
		]
		positions = scope.last_measured_positions(records, ignore_statuses=config.MODULE_STATUSES)
		self.assertEqual(scope.round_robin_order(["a.py", "b.py"], positions), ["a.py", "b.py"])


class QuietNightIsNotADegradedNightTest(unittest.TestCase):
	"""Exit 3 means "we measured and got no verdict". Nothing else may borrow it."""

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.tmp = Path(self._tmp.name)

	def write(self, records: list[dict], name: str) -> Path:
		path = self.tmp / name
		with open(path, "w", encoding="utf-8") as handle:
			for record in records:
				handle.write(json.dumps(record, sort_keys=True) + "\n")
		return path

	def report(self, journal: Path, **kwargs) -> tuple[int, str]:
		with contextlib.redirect_stderr(io.StringIO()):
			with contextlib.redirect_stdout(io.StringIO()) as out:
				code = report_mod.report(journal_path=journal, fmt="json", **kwargs)
		return code, out.getvalue()

	def test_a_view_holding_only_a_skip_is_not_reported_as_degraded(self):
		"""It used to exit 3, which the nightly renders as "a degraded run, not a result"."""
		journal = self.write(
			[{"key": "baseline:pkg/a.py", "module": "pkg/a.py", "status": config.STATUS_BASELINE_SKIP}],
			"journal.jsonl",
		)
		code, _stdout = self.report(journal)
		self.assertEqual(code, report_mod.EXIT_NOTHING_TO_REPORT)
		self.assertNotEqual(code, report_mod.EXIT_NOTHING_MEASURED)

	def test_a_view_where_mutants_ran_and_none_scored_is_still_degraded(self):
		"""The distinction has to cut both ways or exit 3 stops meaning anything."""
		journal = self.write(
			[{"key": "k1", "module": "pkg/a.py", "status": config.STATUS_TIMEOUT}], "journal.jsonl"
		)
		code, _stdout = self.report(journal)
		self.assertEqual(code, report_mod.EXIT_NOTHING_MEASURED)

	def test_the_summary_is_rendered_even_when_there_is_nothing_to_report(self):
		"""Both gates parse this JSON; a step that prints nothing makes them guess."""
		journal = self.write([], "empty.jsonl")
		code, stdout = self.report(journal)
		self.assertEqual(code, report_mod.EXIT_NOTHING_TO_REPORT)
		self.assertEqual(json.loads(stdout)["skipped_modules"], {})

	def test_a_skip_only_view_still_names_the_module_in_the_json(self):
		"""Exit 5 must not mean "silent": the pull-request gate reads skips out of this."""
		journal = self.write(
			[
				{
					"key": "baseline:pkg/a.py",
					"module": "pkg/a.py",
					"status": config.STATUS_MODULE_SKIP,
					"reason": "renamed away",
				}
			],
			"journal.jsonl",
		)
		_code, stdout = self.report(journal)
		self.assertEqual(list(json.loads(stdout)["skipped_modules"]), ["pkg/a.py"])

	def test_an_empty_render_says_so_rather_than_printing_zeros(self):
		summary = report_mod.summarise([])
		self.assertIn("Nothing to report", report_mod.render_markdown(summary))
		self.assertIn("Nothing to report", report_mod.render_text(summary))
		self.assertNotIn("NOTHING MEASURED", report_mod.render_text(summary))


class WorkDoneTest(unittest.TestCase):
	"""What a run DID, which a report of what it DECIDED cannot express.

	A night that re-measures 431 mutants because one test file was touched, and confirms
	every verdict, decides nothing: ``--new-since`` filters all of it and the summary says
	"nothing new". So does a night whose campaign died in provisioning. Truthful about
	verdicts, useless about work - and the second one is the one somebody has to act on.
	"""

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.tmp = Path(self._tmp.name)

	def write(self, name: str, records: list[dict]) -> Path:
		path = self.tmp / name
		with open(path, "w", encoding="utf-8") as handle:
			for record in records:
				handle.write(json.dumps(record, sort_keys=True) + "\n")
		return path

	def mutant(self, key: str, module: str) -> dict:
		return {"key": key, "module": module, "status": config.STATUS_KILLED}

	def test_it_counts_the_mutants_a_run_appended(self):
		before = self.write("before.jsonl", [self.mutant("k0", "pkg/a.py")])
		journal = self.write(
			"journal.jsonl",
			[self.mutant("k0", "pkg/a.py"), self.mutant("k1", "pkg/a.py"), self.mutant("k2", "pkg/b.py")],
		)
		work = report_mod.work_done(journal, before)
		self.assertEqual(work["evaluated"], 2)
		self.assertEqual(work["modules"], ["pkg/a.py", "pkg/b.py"])

	def test_a_re_measured_verdict_that_did_not_change_still_counts_as_work(self):
		"""The exact case: 431 mutants re-measured, every verdict identical, report empty."""
		records = [self.mutant("k1", "pkg/a.py")]
		before = self.write("before.jsonl", records)
		journal = self.write("journal.jsonl", records + records)

		self.assertEqual(report_mod.only_new_since(report_mod.load_results(journal), before), [])
		self.assertEqual(report_mod.work_done(journal, before)["evaluated"], 1)

	def test_module_level_records_are_not_counted_as_mutants(self):
		before = self.write("before.jsonl", [])
		journal = self.write(
			"journal.jsonl",
			[{"key": "baseline:pkg/a.py", "module": "pkg/a.py", "status": config.STATUS_MODULE_CURRENT}],
		)
		work = report_mod.work_done(journal, before)
		self.assertEqual(work["evaluated"], 0)
		self.assertEqual(work["modules"], [])

	def test_a_skipped_module_is_named(self):
		before = self.write("before.jsonl", [])
		journal = self.write(
			"journal.jsonl",
			[{"key": "baseline:pkg/a.py", "module": "pkg/a.py", "status": config.STATUS_BASELINE_SKIP}],
		)
		self.assertEqual(report_mod.work_done(journal, before)["skipped"], ["pkg/a.py"])

	def test_a_replaced_journal_is_reported_as_unknown_rather_than_guessed(self):
		before = self.write("before.jsonl", [self.mutant("k1", "pkg/a.py")] * 3)
		journal = self.write("journal.jsonl", [self.mutant("k1", "pkg/a.py")])
		self.assertTrue(report_mod.work_done(journal, before)["unknown"])
		self.assertIn("unknown", report_mod.render_work(report_mod.work_done(journal, before)))

	def test_a_run_that_evaluated_nothing_says_so_in_words(self):
		before = self.write("before.jsonl", [])
		journal = self.write("journal.jsonl", [])
		self.assertIn(
			"no mutant was evaluated", report_mod.render_work(report_mod.work_done(journal, before))
		)

	def test_the_line_names_the_modules_it_covered(self):
		before = self.write("before.jsonl", [])
		journal = self.write("journal.jsonl", [self.mutant("k1", "pkg/a.py")])
		line = report_mod.render_work(report_mod.work_done(journal, before))
		self.assertIn("1 mutant(s) evaluated", line)
		self.assertIn("pkg/a.py", line)

	def test_the_cli_prints_it_and_never_gates_on_it(self):
		before = self.write("before.jsonl", [])
		journal = self.write("journal.jsonl", [self.mutant("k1", "pkg/a.py")])
		with contextlib.redirect_stdout(io.StringIO()) as out:
			code = cli.main(["work", "--journal", str(journal), "--since", str(before)])
		self.assertEqual(code, 0)
		self.assertIn("1 mutant(s) evaluated", out.getvalue())


class StaleProvenanceIsMarkedTest(unittest.TestCase):
	"""A score computed from verdicts whose tests have moved has to SAY so.

	Invalidation drives re-measurement but did not reach the report. A test edit invalidates
	a whole module at once and a big one takes several budgeted nights to work through, so
	for those nights the published headline is computed entirely from verdicts the harness
	has itself flagged as describing a suite that no longer exists - with no marker, while
	a red baseline gets an explicit "STALE:".
	"""

	def records(self, sha: str | None) -> list[dict]:
		record = {"key": "k1", "module": "pkg/a.py", "file": "pkg/a.py", "status": config.STATUS_KILLED}
		if sha is not None:
			record["tests_sha"] = sha
		return [record]

	def test_verdicts_from_the_current_tests_are_not_marked(self):
		summary = report_mod.summarise(self.records("aaa"), fingerprints={"pkg/a.py": "aaa"})
		self.assertEqual(summary["modules"]["pkg/a.py"]["provenance"], "current")
		self.assertEqual(summary["stale_test_modules"], [])

	def test_verdicts_from_edited_tests_are_marked_stale(self):
		summary = report_mod.summarise(self.records("aaa"), fingerprints={"pkg/a.py": "CHANGED"})
		self.assertEqual(summary["modules"]["pkg/a.py"]["provenance"], "stale")
		self.assertEqual(summary["stale_test_modules"], ["pkg/a.py"])

	def test_verdicts_with_no_provenance_at_all_are_marked_too(self):
		"""A pre-fingerprint journal cannot show what produced its numbers."""
		summary = report_mod.summarise(self.records(None), fingerprints={"pkg/a.py": "aaa"})
		self.assertEqual(summary["modules"]["pkg/a.py"]["provenance"], "unknown")

	def test_a_partially_re_measured_module_is_still_stale(self):
		records = self.records("aaa") + [
			{"key": "k2", "module": "pkg/a.py", "status": config.STATUS_KILLED, "tests_sha": "NEW"}
		]
		summary = report_mod.summarise(records, fingerprints={"pkg/a.py": "NEW"})
		self.assertEqual(summary["modules"]["pkg/a.py"]["provenance"], "stale")

	def test_without_fingerprints_no_claim_is_made_either_way(self):
		summary = report_mod.summarise(self.records("aaa"))
		self.assertNotIn("provenance", summary["modules"]["pkg/a.py"])
		self.assertEqual(summary["stale_test_modules"], [])

	def test_both_renderers_show_the_marker(self):
		summary = report_mod.summarise(self.records("aaa"), fingerprints={"pkg/a.py": "CHANGED"})
		self.assertIn("STALE", report_mod.render_text(summary))
		self.assertIn("stale: tests changed", report_mod.render_markdown(summary))

	def test_the_two_kinds_of_staleness_do_not_share_a_sentence(self):
		""" "edited since this was measured" and "nothing says what measured it" differ."""
		edited = report_mod.provenance_note("stale")
		unknown = report_mod.provenance_note("unknown")
		self.assertNotEqual(edited, unknown)
		self.assertIn("tests changed", edited)
		self.assertIn("no record", unknown)

	def test_the_score_itself_is_unchanged_by_the_marker(self):
		"""It annotates the number; suppressing it would be worse than publishing it."""
		summary = report_mod.summarise(self.records("aaa"), fingerprints={"pkg/a.py": "CHANGED"})
		self.assertEqual(summary["overall"]["score"], 1.0)

	def test_a_tree_it_cannot_fingerprint_degrades_to_no_marker(self):
		with mock.patch.object(scope, "test_fingerprint", side_effect=OSError("no tree")):
			self.assertEqual(report_mod.current_fingerprints(), {})

	def test_the_real_target_map_is_what_gets_fingerprinted(self):
		fingerprints = report_mod.current_fingerprints()
		self.assertEqual(set(fingerprints), set(config.target_map("all")))


class SharedTestInfrastructureTest(unittest.TestCase):
	"""The fingerprint has to cover the files the mapped tests get their assertions from.

	``assert_allowed``/``assert_not_allowed`` live in ``gameplan/tests/base.py`` and the
	personas in ``gameplan/tests/fixtures.py``. Gut one of those and every permission test
	still passes, asserting nothing - while no mapped test file's bytes moved, so a
	fingerprint over the mapped files alone does not move either, every verdict stays
	settled, the module short-circuits before its baseline and the nightly republishes
	yesterday's score having run nothing. That is the failure the fingerprint exists to
	prevent, reachable one import away from where it was fixed.
	"""

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.root = Path(self._tmp.name)
		self.write("gameplan/tests/__init__.py", "")
		self.write("gameplan/tests/base.py", "def assert_not_allowed(x):\n\tassert not x\n")
		self.write("gameplan/tests/fixtures.py", "def create_space():\n\treturn 1\n")
		self.write(
			"gameplan/tests/features/__init__.py",
			"",
		)
		self.write(
			"gameplan/tests/features/test_alpha.py",
			"from gameplan.tests.base import assert_not_allowed\n"
			"from gameplan.tests.fixtures import create_space\n",
		)
		self.mapped = ["gameplan.tests.features.test_alpha"]

	def write(self, relative: str, body: str) -> Path:
		path = self.root / relative
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(body, encoding="utf-8")
		return path

	def test_weakening_a_shared_assertion_helper_moves_the_fingerprint(self):
		before = scope.test_fingerprint(self.mapped, self.root)
		self.write("gameplan/tests/base.py", "def assert_not_allowed(x):\n\tpass\n")
		self.assertNotEqual(before, scope.test_fingerprint(self.mapped, self.root))

	def test_changing_a_shared_fixture_moves_it_too(self):
		before = scope.test_fingerprint(self.mapped, self.root)
		self.write("gameplan/tests/fixtures.py", "def create_space():\n\treturn 2\n")
		self.assertNotEqual(before, scope.test_fingerprint(self.mapped, self.root))

	def test_package_level_setup_is_covered(self):
		"""Importing a test module executes it, so it decides what the tests do."""
		before = scope.test_fingerprint(self.mapped, self.root)
		self.write("gameplan/tests/__init__.py", "# search isolation disabled\n")
		self.assertNotEqual(before, scope.test_fingerprint(self.mapped, self.root))

	def test_it_follows_imports_transitively(self):
		self.write(
			"gameplan/tests/base.py",
			"from gameplan.tests.search_isolation import guard\n\n"
			"def assert_not_allowed(x):\n\tassert not x\n",
		)
		self.write("gameplan/tests/search_isolation.py", "def guard():\n\treturn 1\n")
		before = scope.test_fingerprint(self.mapped, self.root)
		self.write("gameplan/tests/search_isolation.py", "def guard():\n\treturn 2\n")
		self.assertNotEqual(before, scope.test_fingerprint(self.mapped, self.root))

	def test_production_code_is_not_in_the_fingerprint(self):
		"""The boundary, and it is load-bearing: a corpus that goes stale on any source
		edit is never settled long enough to be measured at all."""
		self.write("gameplan/permissions.py", "def check():\n\treturn 1\n")
		self.write(
			"gameplan/tests/features/test_alpha.py",
			"from gameplan.permissions import check\nfrom gameplan.tests.base import assert_not_allowed\n",
		)
		before = scope.test_fingerprint(self.mapped, self.root)
		self.write("gameplan/permissions.py", "def check():\n\treturn 2\n")
		self.assertEqual(before, scope.test_fingerprint(self.mapped, self.root))

	def test_an_unrelated_test_module_is_not_in_the_fingerprint(self):
		self.write("gameplan/tests/features/test_other.py", "x = 1\n")
		before = scope.test_fingerprint(self.mapped, self.root)
		self.write("gameplan/tests/features/test_other.py", "x = 2\n")
		self.assertEqual(before, scope.test_fingerprint(self.mapped, self.root))

	def test_a_diff_touching_a_shared_helper_selects_the_targets_it_invalidates(self):
		"""Or the pull-request job maps the one edit that matters to zero targets."""
		targets = {"pkg/alpha.py": self.mapped}
		selected = scope.changed_targets(["gameplan/tests/base.py"], targets, self.root)
		self.assertEqual(list(selected), ["pkg/alpha.py"])

	def test_scope_and_fingerprint_agree_against_the_real_tree(self):
		"""One check against reality: base.py really is shared by every real target."""
		real = config.target_map("all")
		selected = scope.changed_targets(["gameplan/tests/base.py"], real, Path(config.APP_ROOT))
		self.assertEqual(list(selected), list(real), "base.py must invalidate every target")

	def test_the_real_closure_includes_the_assertion_helpers(self):
		closure = scope._support_closure(
			["gameplan.tests.permissions.test_visibility"], Path(config.APP_ROOT)
		)
		self.assertIn("gameplan.tests.base", closure)
		self.assertIn("gameplan.tests.fixtures", closure)
		self.assertIn("gameplan.tests", closure)


class PruneAgainstAMutatedTreeTest(unittest.TestCase):
	"""Pruning asks the source "does this site still exist?"; a mutant makes it lie.

	Mutant keys carry a fingerprint of their enclosing scope, so ONE applied mutant re-keys
	every site in that function. If a run is SIGKILLed with a mutant on disk, the
	``if: always()`` report step prunes against that tree and silently deletes real
	verdicts - measured at 12 of 72 keys for one mutant in reactions.py - describing them
	as "sites that no longer exist".
	"""

	SOURCE = "def f(a, b):\n\treturn a > b\n"

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.root = Path(self._tmp.name)
		(self.root / "pkg").mkdir()
		(self.root / "pkg" / "a.py").write_text(self.SOURCE, encoding="utf-8")

	def test_records_of_a_file_left_mutated_are_kept(self):
		record = {"key": "a-key-from-the-unmutated-file", "module": "pkg/a.py", "file": "pkg/a.py"}
		kept, dropped = report_mod.drop_stale_sites([record], self.root, unreadable_files={"pkg/a.py"})
		self.assertEqual(kept, [record])
		self.assertEqual(dropped, 0)

	def test_other_files_are_still_pruned(self):
		"""Refusing to prune anything at all would let a real refactor inflate the score."""
		(self.root / "pkg" / "b.py").write_text(self.SOURCE, encoding="utf-8")
		record = {"key": "stale", "module": "pkg/b.py", "file": "pkg/b.py"}
		kept, dropped = report_mod.drop_stale_sites([record], self.root, unreadable_files={"pkg/a.py"})
		self.assertEqual(kept, [])
		self.assertEqual(dropped, 1)

	def test_a_clean_tree_names_no_unreadable_file(self):
		with mock.patch.object(safety, "find_orphaned_backups", return_value=[]):
			self.assertEqual(report_mod.mutated_files(self.root), set())

	def test_a_crashed_run_names_the_file_it_left_mutated(self):
		manifest = {"path": str(self.root / "pkg" / "a.py")}
		with mock.patch.object(safety, "find_orphaned_backups", return_value=[manifest]):
			with mock.patch.object(safety, "orphan_state", return_value="mutated"):
				self.assertEqual(report_mod.mutated_files(self.root), {"pkg/a.py"})

	def test_an_already_restored_backup_does_not_block_pruning(self):
		manifest = {"path": str(self.root / "pkg" / "a.py")}
		with mock.patch.object(safety, "find_orphaned_backups", return_value=[manifest]):
			with mock.patch.object(safety, "orphan_state", return_value="clean"):
				self.assertEqual(report_mod.mutated_files(self.root), set())

	def test_a_broken_safety_layer_never_stops_a_report(self):
		with mock.patch.object(safety, "find_orphaned_backups", side_effect=OSError("no /proc")):
			self.assertEqual(report_mod.mutated_files(self.root), set())


class CacheIdentityTest(unittest.TestCase):
	"""The two workflows' cache path lists are one string, not two.

	``actions/cache`` derives a cache entry's version from the raw ``path`` input, so a
	restore only matches entries saved under the same list, byte for byte. The nightly
	saves; the pull-request job restores from the same lineage. Add a third journal file to
	one of them, or reorder the two lines, and every pull request misses the seed silently -
	it just measures from scratch on a 600-second budget, stays green, and prints the same
	"No seed journal" line a legitimate first run prints.
	"""

	def setUp(self) -> None:
		self.nightly = _workflow(NIGHTLY_WORKFLOW)
		self.pr = _workflow(PR_WORKFLOW)

	def restore_paths(self, workflow: dict) -> list[str]:
		steps = [s for s in _mutation_cache_steps(workflow) if "restore" in s["uses"]]
		self.assertEqual(len(steps), 1)
		return _cached_entries(steps[0])

	def test_the_pull_request_restores_exactly_what_the_nightly_saves(self):
		saves = [s for s in _mutation_cache_steps(self.nightly) if "save" in s["uses"]]
		self.assertEqual(len(saves), 1)
		self.assertEqual(self.restore_paths(self.pr), _cached_entries(saves[0]))

	def test_the_two_restore_lists_are_identical_including_order(self):
		self.assertEqual(self.restore_paths(self.pr), self.restore_paths(self.nightly))

	def test_both_files_say_why_the_list_may_not_drift(self):
		"""A comment is the only thing between this and a silent regression."""
		for path in (NIGHTLY_WORKFLOW, PR_WORKFLOW):
			text = path.read_text(encoding="utf-8")
			self.assertIn("identity", text.lower())


class PullRequestGateTest(unittest.TestCase):
	"""What the pull-request job is allowed to turn red, and for whose module."""

	def setUp(self) -> None:
		self.pr = _workflow(PR_WORKFLOW)
		self.gate = next(
			step["run"] for step in _steps(self.pr) if step.get("name") == "Gate on the mutation signal"
		)

	def test_the_skip_gate_is_restricted_to_this_pull_request_s_targets(self):
		"""The report covers the whole seeded journal; the gate must not blame the diff.

		A module the nightly currently cannot measure appears in a report seeded from the
		nightly's journal. Failing the pull request for it names a file the author never
		touched, with a reason from another day - which is how a gate gets ignored.
		"""
		self.assertIn("needs.scope.outputs.targets", self.gate)
		self.assertIn("if m in t", self.gate)

	def test_it_fails_when_every_mutant_it_ran_produced_a_non_verdict(self):
		"""The nightly is red for this; the pull-request job used to be green."""
		self.assertIn('json-status }}" = "3"', self.gate)
		self.assertIn("non-verdict", self.gate)

	def test_it_does_not_fail_merely_because_there_was_nothing_to_report(self):
		"""Exit 5 is the ordinary outcome of a settled diff, not a broken signal."""
		self.assertNotIn('= "5"', self.gate)

	def test_it_still_reads_the_summary_whatever_the_report_exit_code_was(self):
		"""The report renders on every path now, so an unparseable one is a real failure."""
		self.assertIn("no readable summary", self.gate)


class NightlySummaryHonestyTest(unittest.TestCase):
	"""A night that ground for 45 minutes must not render as an idle one."""

	def setUp(self) -> None:
		self.nightly = _workflow(NIGHTLY_WORKFLOW)
		self.publish = next(
			step["run"] for step in _steps(self.nightly) if step.get("name") == "Publish the report"
		)
		self.gate = next(
			step["run"] for step in _steps(self.nightly) if step.get("name") == "Gate on the mutation signal"
		)

	def test_the_summary_reports_the_work_the_night_did(self):
		self.assertIn("mutation work", self.publish)
		self.assertIn('echo "${work}"', self.publish)

	def test_the_rendered_report_is_printed_on_every_path(self):
		"""The 'degraded' arm used to discard the only place a skipped module is named."""
		self.assertEqual(self.publish.count('cat "${RUNNER_TEMP}/tonight.md"'), 1)
		arms = self.publish.split('case "${tonight_status}"')[1]
		self.assertNotIn('cat "${RUNNER_TEMP}/tonight.md"', arms.split("esac")[0])

	def test_the_quiet_night_arm_does_not_call_it_degraded(self):
		arm = self.publish[self.publish.index("5)") : self.publish.index(";;", self.publish.index("5)"))]
		self.assertNotIn("degraded", arm)
		self.assertIn("no verdict changed", arm)

	def test_the_exit_three_gate_names_the_causes_it_cannot_distinguish(self):
		"""The fix the pull-request job got and this one did not.

		Budget-expired-inside-a-baseline-pass became a reachable cause of exit 3 once the
		exit rules started firing on "budget stopped and nothing evaluated", and this arm
		asserted a different one as fact.
		"""
		arm = self.gate[self.gate.index("3)") : self.gate.index(";;", self.gate.index("3)"))]
		for cause in ("red baseline", "missing source", "budget expired"):
			self.assertIn(cause, arm)
		self.assertNotIn("the signal is broken", arm)


if __name__ == "__main__":
	unittest.main()
