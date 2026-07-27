#!/usr/bin/env python3
"""Summarize repeated Cypress JUnit runs with iteration/spec attribution."""

import glob
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple


class SpecResult(NamedTuple):
	spec: str
	failed: bool
	ran: int
	skipped: int

	@property
	def nothing_ran(self) -> bool:
		"""No test in this spec produced a result — the whole file was skipped.

		A spec that only ever skips is lost coverage, not a pass: `this.skip()` in a
		`before` hook (the realtime spec's preflight, an env var) empties the file
		without recording a single failure.
		"""
		return not self.failed and self.ran == 0


def _as_int(value: str | None) -> int:
	try:
		return int(value)
	except (TypeError, ValueError):
		return 0


def _declared_skips(root: ET.Element, suites: list[ET.Element]) -> int:
	"""The skip count the reporter recorded as an attribute rather than an element.

	mocha-junit-reporter writes no `<testcase>` at all for a pending/skipped test — it
	only bumps `skipped` on `<testsuites>` — while other JUnit writers emit
	`<testcase><skipped/></testcase>`. Reading both shapes keeps the count honest
	whichever reporter produced the file.
	"""
	declared = root.get("skipped")
	if declared is not None:
		return _as_int(declared)
	return sum(_as_int(suite.get("skipped")) for suite in suites)


def parse_file(path: str) -> SpecResult:
	root = ET.parse(path).getroot()
	suites = root.findall(".//testsuite")
	spec = next((suite.get("file") for suite in suites if suite.get("file")), None)
	spec = os.path.basename(spec) if spec else os.path.basename(path)

	cases = root.findall(".//testcase")
	failed = any(case.find("failure") is not None or case.find("error") is not None for case in cases)
	skipped_cases = sum(1 for case in cases if case.find("skipped") is not None)
	skipped = max(skipped_cases, _declared_skips(root, suites))
	return SpecResult(spec, failed, len(cases) - skipped_cases, skipped)


def main() -> int:
	results_dir = sys.argv[1] if len(sys.argv) > 1 else "."
	repeat_count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
	statuses: dict[str, list[tuple[int, bool]]] = defaultdict(list)
	failures: list[tuple[int, str]] = []
	skips: list[tuple[int, SpecResult]] = []
	silent_specs: set[str] = set()
	process_failures = False

	print("## Nightly Cypress repeat results\n")
	print("| Iteration | Process | Specs reported | Failed specs | Specs that ran nothing |")
	print("| --: | --- | --: | --- | --- |")

	for iteration in range(1, repeat_count + 1):
		iteration_dir = os.path.join(results_dir, f"iteration-{iteration}")
		files = sorted(glob.glob(os.path.join(iteration_dir, "*.xml")))
		status_path = os.path.join(iteration_dir, "exit-code")
		try:
			exit_code = int(Path(status_path).read_text(encoding="utf-8").strip())
		except (FileNotFoundError, ValueError):
			exit_code = -1
		process_failures = process_failures or exit_code != 0

		failed_specs = []
		silent_this_iteration = []
		for path in files:
			try:
				result = parse_file(path)
			except ET.ParseError:
				result = SpecResult(os.path.basename(path), True, 0, 0)
			statuses[result.spec].append((iteration, result.failed))
			if result.failed:
				failed_specs.append(result.spec)
				failures.append((iteration, result.spec))
			if result.skipped:
				skips.append((iteration, result))
			if result.nothing_ran:
				silent_this_iteration.append(result.spec)
				silent_specs.add(result.spec)

		if exit_code == 0:
			process = "✅ passed"
		elif exit_code > 0:
			process = f"❌ exit {exit_code}"
		else:
			process = "⚠️ missing"
		attribution = ", ".join(sorted(failed_specs)) or "—"
		if exit_code != 0 and not failed_specs:
			attribution = "No JUnit failure recorded; inspect the iteration log"
		silent_column = ", ".join(sorted(silent_this_iteration)) or "—"
		print(f"| {iteration} | {process} | {len(files)} | {attribution} | {silent_column} |")

	if failures:
		print("\n### Failure attribution\n")
		print("| Iteration | Spec |")
		print("| --: | --- |")
		for iteration, spec in failures:
			print(f"| {iteration} | {spec} |")

	if skips:
		print("\n### Skipped tests\n")
		print("| Iteration | Spec | Skipped | Ran |")
		print("| --: | --- | --: | --: |")
		for iteration, result in skips:
			print(f"| {iteration} | {result.spec} | {result.skipped} | {result.ran} |")

	nondeterministic = [
		spec
		for spec, runs in statuses.items()
		if any(failed for _, failed in runs) and any(not failed for _, failed in runs)
	]
	if nondeterministic:
		print("\n**Non-deterministic specs:** " + ", ".join(sorted(nondeterministic)))
	elif failures:
		print("\nFailures were recorded, but none of the failed specs also passed in another iteration.")
	elif process_failures:
		print("\n⚠️ One or more iterations did not complete successfully; inspect their logs.")
	elif not silent_specs:
		print(f"\n✅ All {repeat_count} iterations passed.")

	if silent_specs:
		print(
			"\n❌ **Ran no tests:** "
			+ ", ".join(sorted(silent_specs))
			+ " — every test in these specs was skipped, so they prove nothing. "
			"Nothing else in this workflow gates on that, so this step fails the job."
		)
		# The `Fail if an iteration failed` step only sees Cypress's exit code, and a
		# fully-skipped spec exits 0. Failing here is what keeps the nightly closed
		# against silently disabled coverage.
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
