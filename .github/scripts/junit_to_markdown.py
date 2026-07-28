#!/usr/bin/env python3
"""Render JUnit XML as one section of the pull request's test report.

	junit_to_markdown.py <results-path> --label Backend [--kind module]

<results-path> is a file or a directory searched recursively for *.xml. Cypress
(mocha-junit-reporter, one file per spec) and `bench run-tests --junit-xml-output`
(one file, one suite per module) both emit the same testsuite/testcase shape, so
one renderer serves both.

The output is deliberately front-loaded: a single status line, then the failures
in full, then everything that passed folded away. A reviewer should learn whether
the run is red without expanding anything, and read a failure without leaving the
page. Passing rows are the bulk of the table and none of the news, so they go
under a <details>.
"""

import argparse
import glob
import os
import re
import xml.etree.ElementTree as ET

# A stack trace is worth linking to, not inlining — enough of the message to
# recognise the failure, and the run log for the rest.
MAX_MESSAGE_CHARS = 300


def fmt_time(seconds: float) -> str:
	s = round(seconds)
	if s < 60:
		return f"{s}s"
	m, s = divmod(s, 60)
	return f"{m}m {s}s"


def clean(text: str) -> str:
	"""Collapse a failure message to a single readable line."""
	text = re.sub(r"\s+", " ", (text or "").strip())
	if len(text) > MAX_MESSAGE_CHARS:
		text = text[:MAX_MESSAGE_CHARS].rstrip() + "…"
	# Backticks inside a message would end the code span it is rendered in.
	return text.replace("`", "'")


def iter_roots(path: str):
	"""Yield every XML document in a file.

	`bench run-tests` runs its suite in batches and xmlrunner writes one complete
	document per batch into the same stream, so the file holds several concatenated
	`<?xml ...?>` documents and is not well-formed as a whole — a plain parse of the
	real 545-test output dies with "junk after document element". Cypress writes one
	document per spec file, so the single-document path stays exact and the split is
	only a fallback.
	"""
	with open(path, "rb") as handle:
		raw = handle.read()

	try:
		yield ET.fromstring(raw)
		return
	except ET.ParseError:
		pass

	# Split only at a declaration that starts its own line, so a declaration quoted
	# inside a failure message does not cut the document in half. Chunks that still
	# do not parse are skipped rather than failing the whole report.
	for chunk in re.split(rb"\n(?=<\?xml)", raw):
		chunk = chunk.strip()
		if not chunk:
			continue
		try:
			yield ET.fromstring(chunk)
		except ET.ParseError:
			continue


def parse_file(path: str):
	"""Return (group_rows, failures) for one XML file."""
	rows, failures = [], []
	for root in iter_roots(path):
		file_rows, file_failures = parse_root(root, path)
		rows.extend(file_rows)
		failures.extend(file_failures)
	return rows, failures


def parse_root(root, path: str):
	"""Return (group_rows, failures) for one parsed document."""
	rows, failures = [], []

	# Cypress names the spec on a "Root Suite" that holds no test cases, while the
	# suites that do hold them carry no file at all — so a per-suite lookup alone
	# falls through to the artifact filename and the table reads as a list of
	# hashes. Fall back to whichever suite in this document does name a file.
	document_file = next((s.get("file") for s in root.iter("testsuite") if s.get("file")), None)

	for suite in root.iter("testsuite"):
		cases = suite.findall("testcase")
		if not cases:
			continue

		source = suite.get("file") or document_file or path
		group = os.path.basename(source)

		total = len(cases)
		skipped = sum(1 for c in cases if c.find("skipped") is not None)
		failed = 0

		for case in cases:
			problem = case.find("failure")
			if problem is None:
				problem = case.find("error")
			if problem is None:
				continue
			failed += 1
			name = case.get("name") or "(unnamed test)"
			message = problem.get("message") or (problem.text or "")
			failures.append((group, name, clean(message)))

		seconds = suite.get("time")
		seconds = float(seconds) if seconds else sum(float(c.get("time") or 0) for c in cases)
		rows.append([group, total, total - failed - skipped, failed, skipped, seconds])

	return rows, failures


def merge(rows: list[list]) -> list[list]:
	"""Fold suites that share a file into one row (bench emits one per module)."""
	merged: dict[str, list] = {}
	for group, total, passed, failed, skipped, seconds in rows:
		row = merged.setdefault(group, [group, 0, 0, 0, 0, 0.0])
		row[1] += total
		row[2] += passed
		row[3] += failed
		row[4] += skipped
		row[5] += seconds
	return sorted(merged.values())


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("results")
	parser.add_argument("--label", required=True, help="e.g. Backend, Cypress")
	parser.add_argument("--kind", default="spec", help="what a row is: spec, module…")
	parser.add_argument("--run-url", default="", help="linked from the failure list")
	args = parser.parse_args()

	if os.path.isdir(args.results):
		files = sorted(glob.glob(os.path.join(args.results, "**", "*.xml"), recursive=True))
	else:
		files = [args.results] if os.path.exists(args.results) else []

	rows, failures = [], []
	for path in files:
		try:
			file_rows, file_failures = parse_file(path)
		except ET.ParseError:
			continue
		rows.extend(file_rows)
		failures.extend(file_failures)

	rows = merge(rows)

	if not rows:
		print(f"**{args.label}** ⚠️ no test results were produced.")
		return 0

	total = sum(r[1] for r in rows)
	passed = sum(r[2] for r in rows)
	failed = sum(r[3] for r in rows)
	skipped = sum(r[4] for r in rows)
	seconds = sum(r[5] for r in rows)

	if failed:
		headline = f"**{args.label}** ❌ {failed} of {total} failed"
	else:
		headline = f"**{args.label}** ✅ {passed} passed"
	skip_note = f" · {skipped} skipped" if skipped else ""
	print(f"{headline} · {fmt_time(seconds)}{skip_note}")

	if failures:
		print()
		for group, name, message in failures:
			print(f"- `{group}` › **{name}**")
			if message:
				print(f"  <br><sub>{message}</sub>")
		if args.run_url:
			print(f"\n[Full log]({args.run_url})")

	print()
	summary = f"{len(rows)} {args.kind}{'s' if len(rows) != 1 else ''}"
	print(f"<details><summary>{summary}</summary>\n")
	print(f"| {args.kind.title()} | Tests | ✅ | ❌ | ⏭ | ⏱ |")
	print("| --- | --: | --: | --: | --: | --: |")
	for group, group_total, group_passed, group_failed, group_skipped, group_seconds in rows:
		mark = " ❌" if group_failed else ""
		print(
			f"| `{group}`{mark} | {group_total} | {group_passed} | {group_failed} "
			f"| {group_skipped} | {fmt_time(group_seconds)} |"
		)
	print(
		f"| **Total** | **{total}** | **{passed}** | **{failed}** "
		f"| **{skipped}** | **{fmt_time(seconds)}** |"
	)
	print("\n</details>")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
