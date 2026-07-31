# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Unit tests for the mutation harness's CI boundary.

Everything here guards one rule: the harness must never signal success for a run in
which it measured nothing. That rule is enforced in three places, all covered below.

* ``cli`` argument wiring - ``verify`` used to ignore ``--journal`` when choosing where
  to write stage-2 verdicts, so an alternate campaign's results were invisible to its
  own report and quietly overwrote the default campaign's.
* ``campaign`` exit codes - a run that skipped every module on a red baseline exited 0,
  so a nightly with a dead site reported success having evaluated zero mutants.
* ``campaign`` per-module setup order - the ``FileGuard`` was built and the baseline run
  *before* ``install_backup``, which is the only thing that undoes a crashed run's
  leftover mutant. Sites were therefore collected from mutated source, and a module with
  nothing pending returned without ever calling it, leaving the mutant on disk.

Pure unit tests: a synthetic source tree in a tempdir, no bench and no site.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gameplan.tests.mutation import campaign, cli, mutators, safety, scope
from gameplan.tests.mutation import report as report_mod
from gameplan.tests.mutation.config import (
	JOURNAL_PATH,
	MODULE_STATUSES,
	STATUS_KILLED,
	STATUS_TIMEOUT,
	VERIFY_PATH,
)

# Small but real: collect_sites must find several mutable sites in it, and the mutant
# below has to be a plausible thing for a crashed run to have left behind.
ORIGINAL = "def compare(a, b):\n\tif a > b:\n\t\treturn True\n\treturn False\n"
LEFTOVER_MUTANT = "def compare(a, b):\n\tif a >= b:\n\t\treturn True\n\treturn False\n"


class MutationCliWiringTest(unittest.TestCase):
	"""``main`` must hand each subcommand the paths its flags actually named."""

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.tmp = Path(self._tmp.name)

	def call(self, argv: list[str], target: str, module=campaign, returns: int = 0) -> dict:
		"""Run ``main(argv)``, capturing the keyword arguments it passed to ``target``."""
		with mock.patch.object(module, target, return_value=returns) as stub:
			with contextlib.redirect_stdout(io.StringIO()):
				code = cli.main(argv)
		stub.assert_called_once()
		self.assertEqual(code, returns)
		return stub.call_args.kwargs

	# --- verify writes where report reads ----------------------------------------

	def test_verify_writes_the_stage_two_file_belonging_to_its_journal(self):
		journal = self.tmp / "archived.jsonl"
		kwargs = self.call(["verify", "--journal", str(journal)], "verify")
		self.assertEqual(kwargs["verify_path"], report_mod.verify_path_for(journal))
		self.assertEqual(kwargs["verify_path"], self.tmp / "archived.verify.jsonl")

	def test_verify_does_not_contaminate_the_default_campaign(self):
		"""The bug: every journal's verdicts landed in the default .mutation/verify.jsonl."""
		journal = self.tmp / "archived.jsonl"
		kwargs = self.call(["verify", "--journal", str(journal)], "verify")
		self.assertNotEqual(kwargs["verify_path"], VERIFY_PATH)

	def test_verify_keeps_the_historical_path_for_the_default_journal(self):
		kwargs = self.call(["verify"], "verify")
		self.assertEqual(kwargs["journal_path"], JOURNAL_PATH)
		self.assertEqual(kwargs["verify_path"], VERIFY_PATH)

	def test_verify_and_report_agree_by_construction(self):
		"""Whatever --journal is given, stage 2 writes exactly where stage 3 looks."""
		for name in ("journal.jsonl", "archived.jsonl", "nightly-2026-07-30.jsonl"):
			with self.subTest(journal=name):
				journal = self.tmp / name
				written = self.call(["verify", "--journal", str(journal)], "verify")["verify_path"]
				read = self.call(["report", "--journal", str(journal)], "report", module=report_mod)[
					"verify_path"
				]
				self.assertEqual(written, read)

	def test_explicit_verify_journal_overrides_the_derived_path(self):
		journal = self.tmp / "archived.jsonl"
		override = self.tmp / "elsewhere.jsonl"
		for command, module in (("verify", campaign), ("report", report_mod)):
			with self.subTest(command=command):
				kwargs = self.call(
					[command, "--journal", str(journal), "--verify-journal", str(override)],
					command,
					module=module,
				)
				self.assertEqual(kwargs["verify_path"], override)

	# --- report gating flags -------------------------------------------------------

	def test_report_passes_fail_under_through(self):
		kwargs = self.call(["report", "--fail-under", "80"], "report", module=report_mod)
		self.assertEqual(kwargs["fail_under"], 80.0)

	def test_fail_under_defaults_to_off(self):
		kwargs = self.call(["report"], "report", module=report_mod)
		self.assertIsNone(kwargs["fail_under"])

	def test_report_exit_code_is_returned_unchanged(self):
		"""main is a pass-through: a gate that fails must reach the shell as a failure."""
		for expected in (
			report_mod.EXIT_OK,
			report_mod.EXIT_BELOW_THRESHOLD,
			report_mod.EXIT_NOTHING_MEASURED,
		):
			with self.subTest(expected=expected):
				self.call(["report"], "report", module=report_mod, returns=expected)

	def test_run_exit_code_is_returned_unchanged(self):
		for expected in (campaign.EXIT_OK, campaign.EXIT_ABORTED, campaign.EXIT_NOTHING_MEASURED):
			with self.subTest(expected=expected):
				self.call(["run"], "run_campaign", returns=expected)

	def test_exit_codes_are_documented_in_the_help_text(self):
		parser = cli.build_parser()
		help_text = io.StringIO()
		with contextlib.redirect_stdout(help_text):
			with self.assertRaises(SystemExit):
				parser.parse_args(["report", "--help"])
		text = help_text.getvalue()
		self.assertIn("exit codes", text)
		self.assertIn(str(report_mod.EXIT_NOTHING_MEASURED), text)
		self.assertIn("--fail-under", text)


class CampaignExitCodeTest(unittest.TestCase):
	"""``_campaign_exit_code`` is the whole contract, so it is pinned in isolation."""

	def test_a_normal_run_succeeds(self):
		code = campaign._campaign_exit_code(targeted=2, skipped=0, pending=10, evaluated=10, aborted=False)
		self.assertEqual(code, campaign.EXIT_OK)

	def test_nothing_left_to_do_is_a_success(self):
		"""Every mutant already journalled: a resumed campaign has genuinely nothing to do."""
		code = campaign._campaign_exit_code(targeted=3, skipped=0, pending=0, evaluated=0, aborted=False)
		self.assertEqual(code, campaign.EXIT_OK)

	def test_every_module_skipped_is_a_failure(self):
		"""A dead site skips every module on a red baseline and measures nothing."""
		code = campaign._campaign_exit_code(targeted=3, skipped=3, pending=0, evaluated=0, aborted=False)
		self.assertEqual(code, campaign.EXIT_NOTHING_MEASURED)

	def test_pending_work_that_produced_nothing_is_a_failure(self):
		code = campaign._campaign_exit_code(targeted=1, skipped=0, pending=12, evaluated=0, aborted=False)
		self.assertEqual(code, campaign.EXIT_NOTHING_MEASURED)

	def test_nothing_measured_and_nothing_to_do_do_not_share_an_exit_code(self):
		broken = campaign._campaign_exit_code(targeted=2, skipped=2, pending=0, evaluated=0, aborted=False)
		resumed = campaign._campaign_exit_code(targeted=2, skipped=0, pending=0, evaluated=0, aborted=False)
		self.assertNotEqual(broken, resumed)

	def test_a_partial_skip_that_still_measured_something_succeeds(self):
		code = campaign._campaign_exit_code(targeted=3, skipped=2, pending=4, evaluated=4, aborted=False)
		self.assertEqual(code, campaign.EXIT_OK)

	def test_an_abort_outranks_everything(self):
		code = campaign._campaign_exit_code(targeted=1, skipped=0, pending=5, evaluated=5, aborted=True)
		self.assertEqual(code, campaign.EXIT_ABORTED)

	def test_limit_zero_is_an_explicit_request_to_measure_nothing(self):
		code = campaign._campaign_exit_code(
			targeted=1, skipped=0, pending=9, evaluated=0, aborted=False, limit=0
		)
		self.assertEqual(code, campaign.EXIT_OK)


class CampaignLoopTestCase(unittest.TestCase):
	"""Drives ``_run_campaign_locked`` over a synthetic app tree.

	Everything that would touch a site, a git repo or the real backup directory is
	replaced; what is left under test is the per-module ordering and the exit code.
	"""

	def setUp(self) -> None:
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.tmp = Path(self._tmp.name)
		self.app_root = self.tmp / "app"
		self.app_root.mkdir()
		self.backup_dir = self.tmp / "backup"
		self.backup_dir.mkdir()
		self.journal = self.tmp / "journal.jsonl"

		for target, attribute, value in (
			(campaign, "APP_ROOT", self.app_root),
			(campaign, "BACKUP_DIR", self.backup_dir),
			(safety, "BACKUP_DIR", self.backup_dir),
			# Real ones would prompt, shell out to git, or rewire this process's signals.
			(campaign, "check_orphans", lambda **_kwargs: True),
			(safety, "git_is_clean", lambda _paths: (True, [])),
			(safety, "install_handlers", lambda: None),
		):
			patcher = mock.patch.object(target, attribute, value)
			patcher.start()
			self.addCleanup(patcher.stop)

		self.collected_sources: list[str] = []
		real_collect = mutators.collect_sites

		def recording_collect(source: str, rel_path: str, **kwargs: object):
			self.collected_sources.append(source)
			return real_collect(source, rel_path, **kwargs)

		patcher = mock.patch.object(mutators, "collect_sites", recording_collect)
		patcher.start()
		self.addCleanup(patcher.stop)

	def write_target(self, rel_path: str, source: str) -> Path:
		path = self.app_root / rel_path
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(source, encoding="utf-8")
		return path

	def plant_crashed_run(self, path: Path, original: str, mutant: str) -> None:
		"""Leave the tree exactly as a SIGKILLed run would: mutant on disk, backup beside it."""
		path.write_text(mutant, encoding="utf-8")
		slug = safety.sha256_text(str(path.resolve()))
		(self.backup_dir / f"{slug}.orig").write_text(original, encoding="utf-8")
		(self.backup_dir / f"{slug}.json").write_text(
			json.dumps(
				{
					"path": str(path.resolve()),
					"sha256": safety.sha256_text(original),
					"mutated_sha256": safety.sha256_text(mutant),
					"pid": os.getpid(),
				}
			),
			encoding="utf-8",
		)

	def fingerprint(self, test_modules: list[str]) -> str:
		"""What the campaign stamps on a verdict, for journals a test writes by hand.

		A verdict is only settled while the tests behind it are unchanged, so a hand-written
		record without this is stale by construction and would be re-measured.
		"""
		return scope.test_fingerprint(test_modules, self.app_root)

	def journal_records(self) -> list[dict]:
		if not self.journal.exists():
			return []
		return [json.loads(line) for line in self.journal.read_text().splitlines() if line.strip()]

	def run_campaign(
		self,
		targets: dict[str, list[str]],
		baseline: tuple[bool, str] = (True, ""),
		status: str = STATUS_KILLED,
		limit: int | None = None,
	) -> int:
		self.evaluated_sources: list[str] = []

		def fake_evaluate(_guard, mutated_source, *_args, **_kwargs):
			self.evaluated_sources.append(mutated_source)
			return status, "tests.some_module", 0.01

		with mock.patch.object(campaign, "_baseline_ok", return_value=baseline):
			with mock.patch.object(campaign, "_evaluate_mutant", fake_evaluate):
				with contextlib.redirect_stdout(io.StringIO()) as out:
					code = campaign._run_campaign_locked(
						targets=targets,
						site="unused.test",
						timeout=1,
						limit=limit,
						mutate_strings=False,
						assume_yes=True,
						journal_path=self.journal,
					)
		self.output = out.getvalue()
		return code


class CampaignOrderingTest(CampaignLoopTestCase):
	"""The backup must be installed before anything reads or measures the file."""

	def test_sites_are_collected_from_the_recovered_original(self):
		"""The bug: collect_sites ran before install_backup, so it saw the crashed run's mutant."""
		path = self.write_target("pkg/compare.py", ORIGINAL)
		self.plant_crashed_run(path, ORIGINAL, LEFTOVER_MUTANT)

		code = self.run_campaign({"pkg/compare.py": ["tests.test_compare"]})

		self.assertEqual(self.collected_sources, [ORIGINAL])
		self.assertEqual(code, campaign.EXIT_OK)

	def test_the_leftover_mutant_is_gone_from_disk_afterwards(self):
		path = self.write_target("pkg/compare.py", ORIGINAL)
		self.plant_crashed_run(path, ORIGINAL, LEFTOVER_MUTANT)

		self.run_campaign({"pkg/compare.py": ["tests.test_compare"]})

		self.assertEqual(path.read_text(), ORIGINAL)

	def test_journalled_keys_belong_to_the_original_source(self):
		"""Keys are content hashes: sites from mutated source resume against nothing."""
		path = self.write_target("pkg/compare.py", ORIGINAL)
		self.plant_crashed_run(path, ORIGINAL, LEFTOVER_MUTANT)

		self.run_campaign({"pkg/compare.py": ["tests.test_compare"]})

		expected = {s.key for s in mutators.collect_sites(ORIGINAL, "pkg/compare.py")}
		# Mutant records only. A campaign also journals statements about the MODULE under
		# a fixed "baseline:<path>" key, which is not a site and has no content hash.
		journalled = {r["key"] for r in self.journal_records() if r["status"] not in MODULE_STATUSES}
		self.assertTrue(journalled)
		self.assertTrue(journalled <= expected)

	def test_a_module_with_nothing_pending_still_gets_its_mutant_removed(self):
		"""The second half of the ordering bug: 'if not pending: continue' skipped the backup."""
		path = self.write_target("pkg/compare.py", ORIGINAL)
		sites = mutators.collect_sites(ORIGINAL, "pkg/compare.py")
		with open(self.journal, "w", encoding="utf-8") as handle:
			for site in sites:
				record = site.to_dict()
				record.update(
					{
						"module": "pkg/compare.py",
						"status": STATUS_KILLED,
						"tests_sha": self.fingerprint(["tests.test_compare"]),
					}
				)
				handle.write(json.dumps(record, sort_keys=True) + "\n")
		self.plant_crashed_run(path, ORIGINAL, LEFTOVER_MUTANT)

		code = self.run_campaign({"pkg/compare.py": ["tests.test_compare"]})

		self.assertEqual(path.read_text(), ORIGINAL)
		self.assertEqual(self.evaluated_sources, [])
		self.assertEqual(code, campaign.EXIT_OK)

	def test_the_backup_is_released_when_the_module_is_skipped(self):
		"""A red baseline must not leave the sidecar backup behind as a fake orphan."""
		path = self.write_target("pkg/compare.py", ORIGINAL)
		self.plant_crashed_run(path, ORIGINAL, LEFTOVER_MUTANT)

		self.run_campaign({"pkg/compare.py": ["tests.test_compare"]}, baseline=(False, "site is down"))

		self.assertEqual(path.read_text(), ORIGINAL)
		self.assertEqual(list(self.backup_dir.iterdir()), [])


class CampaignRunExitCodeTest(CampaignLoopTestCase):
	"""End-to-end exit codes, so the contract holds through the real loop."""

	def test_a_measured_run_exits_zero(self):
		self.write_target("pkg/compare.py", ORIGINAL)
		code = self.run_campaign({"pkg/compare.py": ["tests.test_compare"]})
		self.assertEqual(code, campaign.EXIT_OK)
		self.assertTrue(self.evaluated_sources)

	def test_a_red_baseline_on_every_module_is_not_a_success(self):
		"""The bug: a nightly whose site was down exited 0 having evaluated zero mutants."""
		self.write_target("pkg/compare.py", ORIGINAL)
		self.write_target("pkg/other.py", ORIGINAL)
		code = self.run_campaign(
			{"pkg/compare.py": ["tests.test_compare"], "pkg/other.py": ["tests.test_other"]},
			baseline=(False, "site is down"),
		)
		self.assertEqual(code, campaign.EXIT_NOTHING_MEASURED)
		self.assertIn("NOTHING MEASURED", self.output)
		self.assertEqual(len(self.journal_records()), 2)

	def test_missing_target_files_are_skipped_and_reported(self):
		code = self.run_campaign({"pkg/gone.py": ["tests.test_gone"]})
		self.assertEqual(code, campaign.EXIT_NOTHING_MEASURED)

	def test_a_fully_journalled_run_exits_zero(self):
		"""Nothing to do is not the same as nothing measured, and must not look like it."""
		self.write_target("pkg/compare.py", ORIGINAL)
		self.run_campaign({"pkg/compare.py": ["tests.test_compare"]})
		self.assertTrue(self.evaluated_sources)

		code = self.run_campaign({"pkg/compare.py": ["tests.test_compare"]})
		self.assertEqual(code, campaign.EXIT_OK)
		self.assertEqual(self.evaluated_sources, [])

	def test_a_partially_skipped_run_still_exits_zero_but_says_so(self):
		self.write_target("pkg/compare.py", ORIGINAL)
		baselines = iter([(True, ""), (False, "site is down")])
		with mock.patch.object(campaign, "_baseline_ok", side_effect=lambda *_a: next(baselines)):
			with mock.patch.object(
				campaign, "_evaluate_mutant", lambda *_a, **_k: (STATUS_KILLED, "tests.x", 0.01)
			):
				with contextlib.redirect_stdout(io.StringIO()) as out:
					code = campaign._run_campaign_locked(
						targets={
							"pkg/compare.py": ["tests.test_compare"],
							"pkg/gone.py": ["tests.test_gone"],
						},
						site="unused.test",
						timeout=1,
						limit=None,
						mutate_strings=False,
						assume_yes=True,
						journal_path=self.journal,
					)
		self.assertEqual(code, campaign.EXIT_OK)
		self.assertIn("WARNING", out.getvalue())

	def test_the_circuit_breaker_still_reports_an_abort(self):
		self.write_target("pkg/compare.py", ORIGINAL)
		code = self.run_campaign({"pkg/compare.py": ["tests.test_compare"]}, status=STATUS_TIMEOUT)
		self.assertEqual(code, campaign.EXIT_ABORTED)


if __name__ == "__main__":
	unittest.main()
