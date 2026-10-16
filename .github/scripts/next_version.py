#!/usr/bin/env python3
"""Print the version the release workflow should release next.

	next_version.py <current> <previous> [requested]

<current> is `__version__` in gameplan/__init__.py, <previous> is the version of the
newest release tag ("" before the first release), and [requested] is a version given
to a manual run of the workflow ("" when not given).

- A requested version is released as given. This is how 1.0.0 is released.
- A current version above the previous release was set by hand in a pull request,
  so it is released as it is.
- Otherwise the previous release is bumped: the minor version before 1.0.0
  (0.1.0, 0.2.0, ...), the patch version from 1.0.0 on (1.0.1, 1.0.2, ...).
"""

import re
import sys

VERSION = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def parse(version: str) -> tuple[int, int, int]:
	match = VERSION.fullmatch(version)
	if not match:
		sys.exit(f"{version!r} is not a version like 1.2.3")
	major, minor, patch = (int(part) for part in match.groups())
	return major, minor, patch


def bump(version: tuple[int, int, int]) -> tuple[int, int, int]:
	major, minor, patch = version
	if major == 0:
		return 0, minor + 1, 0
	return major, minor, patch + 1


def next_version(current: str, previous: str, requested: str = "") -> str:
	in_code = parse(current)
	released = parse(previous) if previous else None
	if requested:
		newest = max(in_code, released or in_code)
		if parse(requested) <= newest:
			sys.exit(f"Requested {requested}, which is not above {as_text(newest)}")
		return requested
	if released is None:
		return as_text(bump(in_code))
	if in_code > released:
		return as_text(in_code)
	return as_text(bump(released))


def as_text(version: tuple[int, int, int]) -> str:
	return ".".join(str(part) for part in version)


if __name__ == "__main__":
	print(next_version(*sys.argv[1:4]))
