#!/usr/bin/env python3
"""Render coverage.py XML as a compact GitHub job summary."""

import sys
import xml.etree.ElementTree as ET


def percent(value: str | None) -> str:
	return f"{float(value or 0) * 100:.1f}%"


def main() -> int:
	path = sys.argv[1] if len(sys.argv) > 1 else "coverage.xml"

	print("## Backend coverage\n")
	try:
		root = ET.parse(path).getroot()
	except (FileNotFoundError, ET.ParseError) as exc:
		print(f"⚠️ Coverage results were unavailable: {exc}.")
		return 0

	print("| Metric | Covered | Total | Coverage |")
	print("| --- | --: | --: | --: |")
	print(
		f"| Lines | {root.get('lines-covered', '0')} | {root.get('lines-valid', '0')} "
		f"| {percent(root.get('line-rate'))} |"
	)
	# frappe runs coverage without branch measurement, which reports zero of zero
	# branches. Printing that as 0.0% reads as "no branch coverage" rather than
	# "not measured", so omit the row entirely when there is nothing to report.
	if int(root.get("branches-valid") or 0):
		print(
			f"| Branches | {root.get('branches-covered', '0')} | {root.get('branches-valid', '0')} "
			f"| {percent(root.get('branch-rate'))} |"
		)
	print("\nCoverage is informational only; no minimum threshold is enforced.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
