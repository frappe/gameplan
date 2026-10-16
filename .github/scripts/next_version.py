#!/usr/bin/env python3
"""Set `__version__` in gameplan/__init__.py to the version the release workflow
should release next, and print that version.

	next_version.py <previous> [requested]

<previous> is the version of the newest release tag ("" before the first release), and
[requested] is a version given to a manual run of the workflow ("" when not given).

- A requested version is released as given. This is how 1.0.0 is released.
- A version in code above the previous release was set by hand in a pull request,
  so it is released as it is. The file is then left unchanged.
- A version in code below the previous release is refused.
- The first release is 0.1.0.
- Otherwise the patch version of the previous release goes up: 0.1.0, 0.1.1, 0.1.2, ...
"""

import re
import sys
from pathlib import Path

VERSION = re.compile(r"(\d+)\.(\d+)\.(\d+)")
VERSION_LINE = re.compile(r'^__version__ = "(.*)"$', re.MULTILINE)
INIT_FILE = Path(__file__).resolve().parents[2] / "gameplan" / "__init__.py"
FIRST_RELEASE = (0, 1, 0)


def parse(version: str) -> tuple[int, int, int]:
	match = VERSION.fullmatch(version)
	if not match:
		sys.exit(f"{version!r} is not a version like 1.2.3")
	major, minor, patch = (int(part) for part in match.groups())
	return major, minor, patch


def as_text(version: tuple[int, int, int]) -> str:
	return ".".join(str(part) for part in version)


def next_version(current: str, previous: str, requested: str) -> str:
	in_code = parse(current)
	released = parse(previous) if previous else None
	if released and in_code < released:
		sys.exit(f"__version__ is {current}, which is below the latest release {previous}")
	if requested:
		newest = max(in_code, released or in_code)
		if parse(requested) <= newest:
			sys.exit(f"Requested {requested}, which is not above {as_text(newest)}")
		return requested
	if released is None:
		return as_text(max(in_code, FIRST_RELEASE))
	if in_code > released:
		return as_text(in_code)
	major, minor, patch = released
	return as_text((major, minor, patch + 1))


if __name__ == "__main__":
	previous, requested = (sys.argv[1:] + ["", ""])[:2]
	source = INIT_FILE.read_text()
	line = VERSION_LINE.search(source)
	if not line:
		sys.exit(f"No __version__ line in {INIT_FILE}")
	version = next_version(line.group(1), previous, requested)
	INIT_FILE.write_text(source[: line.start(1)] + version + source[line.end(1) :])
	print(version)
