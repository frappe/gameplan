"""Subprocess wrapper around ``bench run-tests``.

Two things here are load-bearing:

* ``cwd`` is the bench root. ``bench`` resolves the sites directory relative to the
  working directory, so invoking it from the app directory simply fails.
* Timeouts kill the whole process group. ``bench`` spawns python children; killing
  only the parent leaves them holding the test site's lock, which then breaks every
  subsequent mutant run and silently invalidates the campaign.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass

from . import safety
from .config import BENCH_ROOT

RAN_TESTS_RE = re.compile(r"^Ran (\d+) tests?", re.MULTILINE)

# Markers that mean the module never got as far as executing tests. These make a
# non-zero exit a much weaker signal than a genuine assertion failure.
IMPORT_ERROR_MARKERS = (
	"ImportError",
	"ModuleNotFoundError",
	"SyntaxError",
	"IndentationError",
	"Failed to import test module",
	"ImportError: Failed to import",
)


@dataclass
class RunResult:
	returncode: int | None
	output: str
	duration_s: float
	timed_out: bool

	@property
	def tests_ran(self) -> int | None:
		"""Number of tests unittest reported running, or None if it never said."""
		matches = RAN_TESTS_RE.findall(self.output)
		if not matches:
			return None
		return sum(int(m) for m in matches)

	@property
	def looks_like_import_error(self) -> bool:
		"""The mutant broke the module before any test could run.

		Requires an actual import/syntax marker in the output. Treating "no ``Ran N
		tests`` line" as sufficient made every bench or site failure look like a mutant
		kill, which inflates the score to 100% while nothing is being tested at all.
		"""
		if self.timed_out or self.passed:
			return False
		return any(marker in self.output for marker in IMPORT_ERROR_MARKERS)

	@property
	def looks_like_infra_error(self) -> bool:
		"""Non-zero exit, no tests ran, and no sign the mutant caused it.

		A locked site, a bench that failed to start, a missing site, a full disk. Says
		nothing about the mutant, so it must be reported rather than scored.
		"""
		if self.timed_out or self.passed or self.looks_like_import_error:
			return False
		return self.tests_ran in (0, None)

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
