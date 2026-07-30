# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Unit tests for the mutation harness's outcome classification.

These pin the one rule the harness's usefulness rests on: a "kill" is a claim that the
TEST SUITE detected the mutation. A timeout, a wedged site, a broken venv, a runner that
died halfway through - none of those are the suite making a judgement, so none of them
may be scored as a kill, and all of them must be retried rather than cached.

Every bug these tests were written for scored an infrastructure failure as coverage,
which inflates the mutation score toward 100% and then caches the lie in the journal
forever. Deliberately no site, no bench, no subprocess: ``RunResult`` is a plain
dataclass over captured output, so classification is pure and must stay that way.
"""

from __future__ import annotations

import unittest
from unittest import mock

from gameplan.tests.mutation import campaign, config
from gameplan.tests.mutation.runner import RunResult

MUTATED_FILE = "gameplan/email_digest.py"
OTHER_FILE = "gameplan/api.py"


def result(output: str = "", returncode: int = 0, timed_out: bool = False) -> RunResult:
	return RunResult(returncode=returncode, output=output, duration_s=1.0, timed_out=timed_out)


# --- captured output shapes -------------------------------------------------------
# Trimmed from real `bench run-tests` output; the parts the classifier reads are exact.

PASSING = """\
Running 6 old-frappe-test-class-category tests for gameplan

gameplan.tests.features.test_email_digest.TestEmailDigest
    test_digest_groups_by_space
----------------------------------------------------------------------
Ran 6 tests in 3.212s

OK
"""

FAILING = """\
Running 6 old-frappe-test-class-category tests for gameplan

======================================================================
 FAIL  test_digest_groups_by_space
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/f/frappe-bench/apps/gameplan/gameplan/tests/features/test_email_digest.py", line 88
    self.assertEqual(len(items), 2)
AssertionError: 0 != 2

----------------------------------------------------------------------
Ran 6 tests in 3.400s

FAILED (failures=1)
"""

PASSING_WITH_SKIPS = PASSING.replace("OK\n", "OK (skipped=2)\n")

# The mutant made its own module unparseable, so the test module could not be imported.
MUTANT_BROKE_ITS_MODULE = """\
Traceback (most recent call last):
  File "/home/f/frappe-bench/apps/gameplan/gameplan/tests/features/test_email_digest.py", line 12
    from gameplan.email_digest import EmailDigest
  File "/home/f/frappe-bench/apps/gameplan/gameplan/email_digest.py", line 411
    return None None
           ^^^^^^^^^
SyntaxError: invalid syntax
"""

# Same family of words, nothing whatsoever to do with the mutant: a broken environment.
BROKEN_VENV = """\
Traceback (most recent call last):
  File "/home/f/frappe-bench/env/bin/bench", line 5, in <module>
    from bench.cli import cli
ModuleNotFoundError: No module named 'frappe'
"""

# bench never got as far as loading anything.
SITE_LOCKED = """\
Site gp-sqlite.test is currently in maintenance/locked state.
"""

# One suite finished, then the process was killed before the next one reported.
DIED_MID_RUN = """\
Running 12 unit tests for gameplan
----------------------------------------------------------------------
Ran 12 tests in 4.100s

OK

Running 533 integration tests for gameplan
sqlite3.OperationalError: database is locked
Killed
"""

# A real assertion failure that happens to print the word "ImportError" in a captured
# log line. The old substring scan filed this as killed-import-error.
FAILING_MENTIONING_IMPORTERROR = FAILING.replace(
	"AssertionError: 0 != 2",
	"AssertionError: 'ImportError' != 'ok'",
)


class TestClassify(unittest.TestCase):
	"""campaign.classify maps one run outcome to one mutant status."""

	def test_clean_pass_is_a_survivor(self):
		self.assertEqual(
			campaign.classify(result(PASSING, returncode=0), MUTATED_FILE),
			config.STATUS_SURVIVED,
		)

	def test_pass_with_skips_is_a_survivor(self):
		self.assertEqual(
			campaign.classify(result(PASSING_WITH_SKIPS, returncode=0), MUTATED_FILE),
			config.STATUS_SURVIVED,
		)

	def test_genuine_test_failure_is_a_kill(self):
		self.assertEqual(
			campaign.classify(result(FAILING, returncode=1), MUTATED_FILE),
			config.STATUS_KILLED,
		)

	def test_failure_output_mentioning_importerror_is_still_an_ordinary_kill(self):
		"""Tests ran and the suite said FAILED; the word in a log line is irrelevant."""
		status = campaign.classify(result(FAILING_MENTIONING_IMPORTERROR, returncode=1), MUTATED_FILE)
		self.assertEqual(status, config.STATUS_KILLED)

	def test_timeout_is_never_a_kill(self):
		status = campaign.classify(result("", returncode=None, timed_out=True), MUTATED_FILE)
		self.assertEqual(status, config.STATUS_TIMEOUT)
		self.assertNotIn(status, config.KILLED_STATUSES)
		self.assertIn(status, config.NO_VERDICT_STATUSES)
		self.assertIn(status, config.RETRYABLE_STATUSES)

	def test_timeout_wins_over_every_other_signal(self):
		"""Partial output captured before the kill must not promote a timeout to a kill."""
		for output in (PASSING, FAILING, MUTANT_BROKE_ITS_MODULE, DIED_MID_RUN, BROKEN_VENV):
			with self.subTest(output=output.splitlines()[0]):
				status = campaign.classify(result(output, returncode=None, timed_out=True), MUTATED_FILE)
				self.assertEqual(status, config.STATUS_TIMEOUT)

	def test_zero_tests_and_no_explanation_is_infra(self):
		status = campaign.classify(result(SITE_LOCKED, returncode=1), MUTATED_FILE)
		self.assertEqual(status, config.STATUS_INFRA_ERROR)
		self.assertNotIn(status, config.KILLED_STATUSES)

	def test_infra_crash_mentioning_importerror_is_not_a_kill(self):
		"""A broken venv names no mutated file, so it proves nothing about the mutant."""
		status = campaign.classify(result(BROKEN_VENV, returncode=1), MUTATED_FILE)
		self.assertEqual(status, config.STATUS_INFRA_ERROR)
		self.assertNotIn(status, config.KILLED_STATUSES)
		self.assertIn(status, config.RETRYABLE_STATUSES)

	def test_import_error_naming_the_mutated_file_is_a_kill(self):
		status = campaign.classify(result(MUTANT_BROKE_ITS_MODULE, returncode=1), MUTATED_FILE)
		self.assertEqual(status, config.STATUS_KILLED_IMPORT_ERROR)
		self.assertIn(status, config.KILLED_STATUSES)

	def test_import_error_naming_a_different_file_is_not_a_kill(self):
		status = campaign.classify(result(MUTANT_BROKE_ITS_MODULE, returncode=1), OTHER_FILE)
		self.assertEqual(status, config.STATUS_INFRA_ERROR)

	def test_import_error_without_a_known_mutated_file_is_not_a_kill(self):
		"""No attribution possible means no verdict, not a free kill."""
		status = campaign.classify(result(MUTANT_BROKE_ITS_MODULE, returncode=1), None)
		self.assertEqual(status, config.STATUS_INFRA_ERROR)

	def test_infra_crash_after_a_partial_run_is_not_a_kill(self):
		"""12 tests passed, then the process died. Nothing judged the mutant."""
		status = campaign.classify(result(DIED_MID_RUN, returncode=-9), MUTATED_FILE)
		self.assertEqual(status, config.STATUS_INCOMPLETE)
		self.assertNotIn(status, config.KILLED_STATUSES)
		self.assertIn(status, config.RETRYABLE_STATUSES)

	def test_exit_zero_without_a_verdict_is_not_a_survivor(self):
		"""A survivor is a claim of missing coverage; a suite that never ran is not."""
		status = campaign.classify(result("bench: nothing to do\n", returncode=0), MUTATED_FILE)
		self.assertEqual(status, config.STATUS_INFRA_ERROR)

	def test_no_tests_ran_verdict_with_failure_exit_is_infra(self):
		status = campaign.classify(result("Ran 0 tests in 0.000s\n\nNO TESTS RAN\n", 1), MUTATED_FILE)
		self.assertEqual(status, config.STATUS_INFRA_ERROR)

	def test_every_reachable_status_is_survived_killed_or_no_verdict(self):
		cases = [
			result(PASSING, 0),
			result(PASSING_WITH_SKIPS, 0),
			result(FAILING, 1),
			result(MUTANT_BROKE_ITS_MODULE, 1),
			result(BROKEN_VENV, 1),
			result(SITE_LOCKED, 1),
			result(DIED_MID_RUN, -9),
			result("", None, timed_out=True),
			result("", 0),
			result("", 1),
		]
		buckets = config.KILLED_STATUSES | config.NO_VERDICT_STATUSES | {config.STATUS_SURVIVED}
		for case in cases:
			with self.subTest(rc=case.returncode, timed_out=case.timed_out):
				self.assertIn(campaign.classify(case, MUTATED_FILE), buckets)


class TestRunResultFacts(unittest.TestCase):
	"""RunResult reports facts about the output; it must not editorialise."""

	def test_tests_ran_sums_every_block(self):
		self.assertEqual(result(DIED_MID_RUN).tests_ran, 12)
		self.assertEqual(result(PASSING).tests_ran, 6)

	def test_tests_ran_is_none_when_never_reported(self):
		self.assertIsNone(result(BROKEN_VENV).tests_ran)

	def test_reached_verdict_needs_the_runners_own_summary_line(self):
		self.assertTrue(result(PASSING).reached_verdict)
		self.assertTrue(result(FAILING).reached_verdict)
		self.assertFalse(result(BROKEN_VENV).reached_verdict)
		self.assertFalse(result(SITE_LOCKED).reached_verdict)

	def test_suite_reported_failure_only_on_the_failed_summary_line(self):
		self.assertTrue(result(FAILING).suite_reported_failure)
		self.assertFalse(result(PASSING).suite_reported_failure)
		# A completed suite followed by a dead process is not a reported failure.
		self.assertFalse(result(DIED_MID_RUN).suite_reported_failure)
		# Nor is the word appearing inside a traceback body.
		self.assertFalse(result("  raise Exception('FAILED to connect')\n").suite_reported_failure)

	def test_blames_file_matches_traceback_frames_not_arbitrary_text(self):
		res = result(MUTANT_BROKE_ITS_MODULE)
		self.assertTrue(res.blames_file(MUTATED_FILE))
		self.assertFalse(res.blames_file(OTHER_FILE))
		self.assertFalse(res.blames_file(None))

	def test_mutant_broke_import_requires_zero_tests(self):
		"""If tests executed, the module imported fine whatever the output says."""
		output = FAILING + MUTANT_BROKE_ITS_MODULE
		self.assertFalse(result(output, 1).mutant_broke_import(MUTATED_FILE))

	def test_mutant_broke_import_requires_a_marker(self):
		output = 'File "/home/f/frappe-bench/apps/gameplan/gameplan/email_digest.py", line 1\n'
		self.assertFalse(result(output, 1).mutant_broke_import(MUTATED_FILE))


class TestStatusVocabularyInvariants(unittest.TestCase):
	"""The config sets are the harness's safety net. Guard their relationships."""

	def all_statuses(self) -> set[str]:
		return {value for name, value in vars(config).items() if name.startswith("STATUS_")}

	def test_no_verdict_is_never_a_kill(self):
		self.assertEqual(config.NO_VERDICT_STATUSES & config.KILLED_STATUSES, frozenset())

	def test_no_verdict_never_reaches_the_score(self):
		self.assertTrue(config.NO_VERDICT_STATUSES <= config.NON_SCORING_STATUSES)

	def test_no_verdict_is_always_retried(self):
		self.assertTrue(config.NO_VERDICT_STATUSES <= config.RETRYABLE_STATUSES)

	def test_a_kill_is_never_retried_or_unscored(self):
		self.assertEqual(config.KILLED_STATUSES & config.RETRYABLE_STATUSES, frozenset())
		self.assertEqual(config.KILLED_STATUSES & config.NON_SCORING_STATUSES, frozenset())

	def test_every_status_has_been_classified(self):
		"""A new STATUS_* must be sorted into a bucket, not left to default to 'scored'."""
		accounted = (
			config.KILLED_STATUSES
			| config.NO_VERDICT_STATUSES
			| {config.STATUS_SURVIVED, config.STATUS_BASELINE_SKIP}
		)
		self.assertEqual(self.all_statuses() - accounted, set())

	def test_legacy_killed_timeout_is_demoted_not_counted(self):
		"""Journals written before timeouts were demoted must be re-evaluated, not scored."""
		self.assertNotIn(config.STATUS_KILLED_TIMEOUT, config.KILLED_STATUSES)
		self.assertIn(config.STATUS_KILLED_TIMEOUT, config.NO_VERDICT_STATUSES)
		self.assertIn(config.STATUS_KILLED_TIMEOUT, config.RETRYABLE_STATUSES)


class TestControlCheck(unittest.TestCase):
	"""The verify stage only believes a full-suite kill if the suite is provably green."""

	def _control(self, res: RunResult):
		with mock.patch.object(campaign, "run_tests", return_value=res):
			return campaign._control_ok("site", 60)

	def test_green_control_is_healthy(self):
		healthy, reason, _ = self._control(result(PASSING, 0))
		self.assertTrue(healthy)
		self.assertEqual(reason, "")

	def test_red_control_is_unhealthy(self):
		healthy, reason, _ = self._control(result(FAILING, 1))
		self.assertFalse(healthy)
		self.assertIn("RED", reason)

	def test_timed_out_control_is_unhealthy(self):
		healthy, reason, _ = self._control(result("", None, timed_out=True))
		self.assertFalse(healthy)
		self.assertIn("timed out", reason)

	def test_control_that_ran_nothing_is_unhealthy(self):
		healthy, reason, _ = self._control(result("bench: ok\n", 0))
		self.assertFalse(healthy)
		self.assertIn("never reported", reason)
