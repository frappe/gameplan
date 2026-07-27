#!/usr/bin/env python3
"""Summarize repeated Cypress JUnit runs with iteration/spec attribution."""

import glob
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def parse_file(path: str) -> tuple[str, bool]:
	root = ET.parse(path).getroot()
	suites = root.findall(".//testsuite")
	spec = next((suite.get("file") for suite in suites if suite.get("file")), None)
	spec = os.path.basename(spec) if spec else os.path.basename(path)
	failed = any(
		case.find("failure") is not None or case.find("error") is not None
		for case in root.findall(".//testcase")
	)
	return spec, failed


def main() -> int:
	results_dir = sys.argv[1] if len(sys.argv) > 1 else "."
	repeat_count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
	statuses: dict[str, list[tuple[int, bool]]] = defaultdict(list)
	failures: list[tuple[int, str]] = []
	process_failures = False

	print("## Nightly Cypress repeat results\n")
	print("| Iteration | Process | Specs reported | Failed specs |")
	print("| --: | --- | --: | --- |")

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
		for path in files:
			try:
				spec, failed = parse_file(path)
			except ET.ParseError:
				spec, failed = os.path.basename(path), True
			statuses[spec].append((iteration, failed))
			if failed:
				failed_specs.append(spec)
				failures.append((iteration, spec))

		if exit_code == 0:
			process = "✅ passed"
		elif exit_code > 0:
			process = f"❌ exit {exit_code}"
		else:
			process = "⚠️ missing"
		attribution = ", ".join(sorted(failed_specs)) or "—"
		if exit_code != 0 and not failed_specs:
			attribution = "No JUnit failure recorded; inspect the iteration log"
		print(f"| {iteration} | {process} | {len(files)} | {attribution} |")

	if failures:
		print("\n### Failure attribution\n")
		print("| Iteration | Spec |")
		print("| --: | --- |")
		for iteration, spec in failures:
			print(f"| {iteration} | {spec} |")

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
	else:
		print(f"\n✅ All {repeat_count} iterations passed.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
