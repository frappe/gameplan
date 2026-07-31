"""Subprocess wrapper around ``bench run-tests``.

Two things here are load-bearing:

* ``cwd`` is the bench root. ``bench`` resolves the sites directory relative to the
  working directory, so invoking it from the app directory simply fails.
* Timeouts kill the whole process group. ``bench`` spawns python children; killing
  only the parent leaves them holding the test site's lock, which then breaks every
  subsequent mutant run and silently invalidates the campaign.

``RunResult`` deliberately exposes *facts about the output* rather than a verdict.
Deciding what an outcome means about a mutant is ``campaign.classify``'s job, and
keeping the two apart is what makes the classification unit-testable without a site.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass

from . import safety
from .config import BENCH_ROOT

RAN_TESTS_RE = re.compile(r"^Ran (\d+) tests?", re.MULTILINE)

# ``unittest.TextTestRunner`` closes every suite it finishes with exactly one of these
# at the start of a line, after the "Ran N tests" line. Their presence is the only
# positive proof that the runner reached the end of a suite and announced a result,
# rather than being killed somewhere in the middle. Frappe subclasses TextTestRunner
# and does not override that tail, and it runs one suite per app+category, so a healthy
# invocation can print several of these.
VERDICT_RE = re.compile(r"^(?:OK|FAILED|NO TESTS RAN)\b", re.MULTILINE)
# The only line that means "the test suite judged something to have failed". A non-zero
# exit code on its own does not: bench, the site loader and the process supervisor can
# all produce one without a single assertion having been evaluated.
FAILURE_VERDICT_RE = re.compile(r"^FAILED\b", re.MULTILINE)

# Markers that mean a module never got as far as executing tests. On their own they are
# far too weak to score anything - see ``RunResult.mutant_broke_import``.
IMPORT_ERROR_MARKERS = (
	"ImportError",
	"ModuleNotFoundError",
	"SyntaxError",
	"IndentationError",
	"Failed to import test module",
)


@dataclass
class RunResult:
	returncode: int | None
	output: str
	duration_s: float
	timed_out: bool

	@property
	def tests_ran(self) -> int | None:
		"""Total tests unittest reported running, or None if it never said.

		Summed across suites because bench prints one "Ran N tests" block per
		app+category. This answers "did anything execute at all", NOT "did the run
		finish" - use ``reached_verdict`` for that.
		"""
		matches = RAN_TESTS_RE.findall(self.output)
		if not matches:
			return None
		return sum(int(m) for m in matches)

	@property
	def reached_verdict(self) -> bool:
		"""The test runner itself announced a result (OK / FAILED / NO TESTS RAN)."""
		return bool(VERDICT_RE.search(self.output))

	@property
	def suite_reported_failure(self) -> bool:
		"""The test suite declared a failure, as opposed to the process merely dying."""
		return bool(FAILURE_VERDICT_RE.search(self.output))

	@property
	def has_import_error_marker(self) -> bool:
		return any(marker in self.output for marker in IMPORT_ERROR_MARKERS)

	def blames_file(self, rel_path: str | None) -> bool:
		"""The output contains a traceback frame in ``rel_path``.

		Matched on the path form only. Any Python traceback through that file prints
		``File "<abs path>"``, and the absolute path ends with the repo-relative one,
		so this is both reliable and much harder to trip accidentally than the dotted
		module name (which shows up in ordinary log lines and error messages).
		"""
		if not rel_path:
			return False
		return rel_path in self.output

	def mutant_broke_import(self, rel_path: str | None) -> bool:
		"""The mutant made its own module unimportable - a genuine detection.

		All three conditions are required, because each one alone is a known way to
		score an infrastructure failure as a kill:

		* non-zero exit, not a timeout;
		* zero tests executed - if tests ran, the module imported fine and any import
		marker in the output belongs to something else;
		* the traceback actually names the file we mutated - a broken venv, a missing
		app or a bench wrapper traceback all emit "ImportError" while saying nothing
		whatsoever about the mutant.
		"""
		if self.timed_out or self.passed:
			return False
		if self.tests_ran not in (0, None):
			return False
		if not self.has_import_error_marker:
			return False
		return self.blames_file(rel_path)

	@property
	def passed(self) -> bool:
		return self.returncode == 0


def build_command(site: str, test_module: str | None) -> list[str]:
	cmd = ["bench", "--site", site, "run-tests", "--app", "gameplan"]
	if test_module:
		cmd += ["--module", test_module]
	cmd.append("--failfast")
	return cmd


def run_tests(site: str, test_module: str | None, timeout: int) -> RunResult:
	"""Run one bench test invocation, hard-killing the process group on timeout."""
	cmd = build_command(site, test_module)
	started = time.monotonic()
	proc = subprocess.Popen(
		cmd,
		cwd=str(BENCH_ROOT),
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True,
		errors="replace",
		# Its own session/process group so os.killpg can reap bench AND its children.
		start_new_session=True,
	)
	# start_new_session makes the child a session/group leader, so its pgid is its pid.
	# Capture it now: by the time a timeout fires the `bench` wrapper has usually exited
	# and os.getpgid(proc.pid) would raise, leaving its children unkillable.
	pgid = proc.pid
	safety.set_active_child(proc, pgid)
	timed_out = False
	try:
		try:
			output, _ = proc.communicate(timeout=timeout)
		except subprocess.TimeoutExpired:
			timed_out = True
			safety.kill_process_group(proc, pgid)
			try:
				output, _ = proc.communicate(timeout=30)
			except subprocess.TimeoutExpired:
				# The group refused to die; surface it rather than pretend it is gone.
				safety.kill_process_group(proc, pgid)
				output = ""
	finally:
		safety.set_active_child(None)

	return RunResult(
		returncode=proc.returncode,
		output=output or "",
		duration_s=round(time.monotonic() - started, 2),
		timed_out=timed_out,
	)
