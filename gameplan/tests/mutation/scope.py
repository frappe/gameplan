"""What one mutation run attempts, and when it stops.

The decisions live here as functions of their arguments - no site, no network, no wall
clock except the one you inject, and no filesystem beyond reading files you name. That is
deliberate: they are the logic CI depends on, and CI is the one place we cannot debug
interactively.

* :class:`Budget` - the nightly runs for a fixed wall-clock slice, not to completion.
* :func:`round_robin_order` - which module that slice is spent on, so a week of budgeted
  nights covers the corpus instead of grinding the first module forever.
* :func:`changed_targets` - which targets a pull request's diff implicates.
* :func:`test_fingerprint` - when a settled verdict stops describing the current suite.

IMPORT CONSTRAINT: this module must import nothing but the standard library at module
level, and nothing from its own package. ``gameplan/tests/__init__.py`` imports frappe,
so `import gameplan.tests.mutation.scope` needs a provisioned bench. The CI job that
answers "does this PR touch any mutation target at all?" has to run *before* a bench
exists - otherwise every frontend-only PR pays ten minutes of provisioning to be told
"nothing to do". It therefore runs this file as a script:

    python gameplan/tests/mutation/scope.py --changed-files-from changed.txt

which puts the file's own directory on sys.path and never executes a parent package's
``__init__``. A single relative import at module level would break that.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import sys
import time
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from pathlib import Path

# The package that holds this app's shared test infrastructure. Everything a mapped test
# module transitively imports from under here is part of what its assertions MEAN, so it
# belongs in the fingerprint; see _support_closure.
TEST_PACKAGE = "gameplan.tests"


class Budget:
	"""A wall-clock allowance, checked *between* units of work.

	The nightly cannot run the full corpus in one go, so it runs for a slice and resumes
	tomorrow. The slice has to be enforced in here rather than by killing the job: the
	harness edits source files in place, and a process killed between ``apply`` and
	``restore`` leaves a mutant on disk in a real working tree. So nothing in this class
	can interrupt anything - it only ever answers "should the caller start another one?",
	and the caller asks that question at points where no file is mutated.

	``clock`` is injected so the whole thing is testable without sleeping.
	"""

	def __init__(self, seconds: float | None, clock: Callable[[], float] = time.monotonic) -> None:
		if seconds is not None and seconds < 0:
			raise ValueError(f"budget must not be negative: {seconds!r}")
		self.seconds = seconds
		self._clock = clock
		self._started = clock()

	@property
	def unlimited(self) -> bool:
		return self.seconds is None

	@property
	def elapsed(self) -> float:
		return self._clock() - self._started

	@property
	def remaining(self) -> float:
		"""Seconds left, clamped at 0. ``inf`` when there is no budget."""
		if self.seconds is None:
			return float("inf")
		return max(0.0, self.seconds - self.elapsed)

	@property
	def expired(self) -> bool:
		"""True once the allowance is used up.

		A zero budget is expired from the outset. That mirrors ``--limit 0``: an explicit
		request to evaluate nothing, which the exit-code rules treat as success rather
		than as a run that failed to measure anything.
		"""
		if self.seconds is None:
			return False
		return self.elapsed >= self.seconds

	def describe(self) -> str:
		if self.seconds is None:
			return "no budget"
		return f"{self.elapsed:.0f}s of {self.seconds:.0f}s used, {self.remaining:.0f}s left"


def last_measured_positions(
	records: Iterable[Mapping[str, object]], ignore_statuses: Collection[str] = ()
) -> dict[str, int]:
	"""Map each module to the position of its most recent journal record.

	The journal is append-only and survives between nightly runs (it is restored from the
	Actions cache), so position in the file *is* recency: the further down a module's last
	record sits, the more recently it was worked on.

	``ignore_statuses`` exists for the module-skip records. A skip is the opposite of a
	measurement, and counting it as one is actively harmful: the skip lands at the very end
	of the journal, so the broken module sorts LAST in the rotation - the one module the
	gate is demanding be re-measured becomes the one a budget will not reach, and the
	nightly stays red for a full rotation after the cause is fixed. Skips therefore leave a
	module's recency exactly where it was, so it is retried at its normal turn or sooner.
	"""
	positions: dict[str, int] = {}
	for position, record in enumerate(records):
		if record.get("status") in ignore_statuses:
			continue
		module = record.get("module") or record.get("file")
		if isinstance(module, str) and module:
			positions[module] = position
	return positions


def _module_path(dotted: str, root: Path) -> Path | None:
	"""Resolve a dotted module to a file under ``root``: a module, or a package's init."""
	base = root / dotted.replace(".", "/")
	module = base.with_suffix(".py")
	if module.is_file():
		return module
	package = base / "__init__.py"
	if package.is_file():
		return package
	return None


def _imported_support_modules(path: Path, dotted: str) -> list[str]:
	"""Dotted names under ``TEST_PACKAGE`` that ``path`` imports.

	Read from the AST rather than by importing anything: this runs on a bare checkout with
	no bench, and importing ``gameplan.tests`` needs frappe (see the module docstring).
	"""
	try:
		tree = ast.parse(path.read_bytes())
	except (OSError, SyntaxError, ValueError):
		# A test file we cannot parse still contributes its bytes to the fingerprint; only
		# the edges out of it are lost, and guessing them would be worse.
		return []
	candidates: list[str] = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			candidates += [alias.name for alias in node.names]
		elif isinstance(node, ast.ImportFrom):
			if node.level:
				# "from . import x" inside a module: the base is the module's package.
				parts = dotted.split(".")[: -node.level]
				if not parts:
					continue
				module = ".".join(parts + ([node.module] if node.module else []))
			else:
				module = node.module or ""
			if not module:
				continue
			candidates.append(module)
			# "from gameplan.tests import base" names the submodule in the alias, not the
			# module, so both spellings have to be tried.
			candidates += [f"{module}.{alias.name}" for alias in node.names]
	return [m for m in candidates if m == TEST_PACKAGE or m.startswith(f"{TEST_PACKAGE}.")]


def _support_closure(test_modules: Iterable[str], root: Path) -> list[str]:
	"""The mapped test modules plus the shared test code they transitively import.

	WHY THE CLOSURE AND NOT JUST THE MAPPED FILES
	---------------------------------------------
	The mapped modules are not where the assertions live. ``assert_allowed`` and
	``assert_not_allowed`` are in ``gameplan/tests/base.py``; the personas and
	``create_space``/``create_community`` are in ``gameplan/tests/fixtures.py``. Gut one of
	those and every permission test still passes while asserting nothing - and not one
	mapped file's bytes changed, so a fingerprint over the mapped files alone does not
	move, every verdict stays settled for ever, and the nightly republishes yesterday's
	score having run nothing. That is precisely the failure the fingerprint exists to
	prevent, one file away from where it was fixed.

	WHERE THE BOUNDARY IS, AND WHY THERE
	------------------------------------
	Only ``gameplan.tests.*``. Test code decides what is ASSERTED, and nothing else
	fingerprints it. Production code is the thing being measured: a change to it re-keys
	the mutation sites it contains, and the corpus rotation re-measures the rest. Pulling
	all first-party imports in instead would put most of the app behind every verdict, and
	a nightly whose entire corpus goes stale on any source edit never settles and therefore
	never measures anything at all.

	Package ``__init__`` files on the way to each module are included: importing a test
	module executes them, and ``gameplan/tests/__init__.py`` in particular installs
	setup that every test in this app runs under.

	THE COST, ACCEPTED DELIBERATELY: an edit to ``base.py`` invalidates EVERY target's
	verdicts - the whole ~1100-mutant corpus, several budgeted nights of re-measurement.
	That is the right trade, because the alternative is that the one edit which can make
	every suite in the repo vacuous is the one edit nothing re-measures. A cheaper grain
	(hash only the functions a test calls) would claim a precision the measurement does not
	have: a mutation verdict depends on the whole module's tests running, fixtures and
	imports included.
	"""
	seen: set[str] = set()
	queue: list[str] = []
	for dotted in test_modules:
		if dotted not in seen:
			seen.add(dotted)
			queue.append(dotted)
	while queue:
		dotted = queue.pop()
		path = _module_path(dotted, root)
		if path is None:
			continue
		parts = dotted.split(".")
		# Ancestor packages, as far up as the test package itself.
		ancestors = [".".join(parts[:i]) for i in range(1, len(parts))]
		neighbours = [a for a in ancestors if a == TEST_PACKAGE or a.startswith(f"{TEST_PACKAGE}.")]
		neighbours += _imported_support_modules(path, dotted)
		for candidate in neighbours:
			if candidate not in seen and _module_path(candidate, root) is not None:
				seen.add(candidate)
				queue.append(candidate)
	return sorted(seen)


def test_fingerprint(test_modules: Iterable[str], root: Path) -> str:
	"""Fingerprint the test files that decide a module's mutation verdicts.

	WHY A VERDICT NEEDS THIS
	------------------------
	A mutant key is derived purely from the source AST, so nothing about the test suite
	enters it. Without a fingerprint the resume logic treats "killed" as settled for ever:
	delete an assertion, and the mutant it used to kill is never re-measured. The nightly
	then cannot detect the one regression it exists to catch, and - because the journal is
	carried between nights - it looks greener and does less work every night, for ever.

	Storing this beside each verdict makes the verdict's provenance explicit: it says
	"this kill was produced by THESE test files, at these exact bytes". When the bytes
	change the verdict is stale, not wrong, and gets re-measured.

	WHAT IT COVERS
	--------------
	The mapped test files AND the shared test code they transitively import - see
	:func:`_support_closure`, which also documents where that boundary is drawn and what
	the width of it costs.

	THE COST, DECIDED DELIBERATELY
	------------------------------
	The fingerprint covers a whole module's test closure, so editing one line of
	``test_email_digest.py`` invalidates all of ``email_digest.py``'s verdicts - the
	largest target at 431 mutants, about 49 minutes at the measured 6.8s mean, i.e. more
	than one whole nightly budget - and editing ``base.py`` invalidates the entire corpus.
	That is the intended trade: the alternative on offer is never re-measuring at all, and
	a nightly that cannot notice a deleted assertion is theatre. A finer grain (per test
	function, or per mutant x killing-test) was rejected - a mutation verdict depends on the
	whole module's tests running, including which fixtures and which imports they set up,
	so anything narrower would claim a precision the measurement does not have.

	A missing test file hashes as a distinct constant rather than raising: config.py can
	name a module that has been renamed away, and that has to invalidate verdicts (and
	show up as a red baseline) rather than crash the campaign.
	"""
	digest = hashlib.sha256()
	for dotted in _support_closure(sorted(set(test_modules)), root):
		path = _module_path(dotted, root)
		try:
			body = path.read_bytes() if path is not None else b"\x00<missing>"
		except OSError:
			body = b"\x00<missing>"
		digest.update(dotted.encode("utf-8"))
		digest.update(b"\x00")
		digest.update(hashlib.sha256(body).hexdigest().encode("ascii"))
		digest.update(b"\x00")
	return digest.hexdigest()


def round_robin_order(modules: Sequence[str], last_measured: Mapping[str, int]) -> list[str]:
	"""Order modules least-recently-measured first.

	Without this, a budgeted nightly is worthless: every night starts at the top of the
	target map, so the first module absorbs the entire budget and the last module is never
	measured at all. Ordering by "when did we last touch this" makes consecutive nights
	pick up where the previous one stopped, and the corpus rotates.

	Modules with no journal record at all sort first (a brand-new target should not wait a
	full rotation), and ties keep the declared order so the result is deterministic.
	"""
	declared = {module: index for index, module in enumerate(modules)}
	return sorted(modules, key=lambda m: (last_measured.get(m, -1), declared[m]))


def normalise_path(raw: str) -> str:
	"""Repo-relative POSIX form of a path from a diff, or "" if it is not one."""
	path = raw.strip().replace("\\", "/")
	while path.startswith("./"):
		path = path[2:]
	return path.lstrip("/")


def _test_module_path(dotted: str) -> str:
	"""``gameplan.tests.features.test_polls`` -> ``gameplan/tests/features/test_polls.py``."""
	return dotted.replace(".", "/") + ".py"


def changed_targets(
	changed_paths: Iterable[str], targets: Mapping[str, Sequence[str]], root: Path | None = None
) -> dict[str, list[str]]:
	"""Restrict ``targets`` to the ones a diff implicates, keeping the declared order.

	Three kinds of changed file select a target:

	* the target source itself - the obvious case;
	* one of its mapped *test* modules - editing a test changes what that module's mutation
	score means, and a PR that deletes an assertion is exactly the change this job exists
	to catch. Skipping those would leave the one edit that can silently drop a module's
	score unmeasured.
	* any shared test file those modules import (``base.py``, ``fixtures.py``, ...). Same
	argument, and a stronger one: weakening ``assert_not_allowed`` makes every permission
	test in the repo vacuous while touching no mapped file at all. This mirrors exactly
	what :func:`test_fingerprint` invalidates, so the pull-request job measures what the
	nightly would re-measure. ``root`` is where those imports are resolved from; the
	default is this app's root, which is also the checkout in CI.

	Anything else - frontend, docs, an unmapped Python file - selects nothing, and an
	empty result is a legitimate answer meaning "this PR has nothing to measure", not an
	error. Inputs are expected repo-relative, as ``git diff --name-only`` emits them.
	"""
	root = root if root is not None else Path(__file__).resolve().parents[3]
	wanted: set[str] = set()
	by_test_file: dict[str, list[str]] = {}
	for source, test_modules in targets.items():
		# The declared modules first and unconditionally: a mapped test file selects its
		# target whether or not it exists on disk to be resolved.
		for dotted in list(test_modules) + _support_closure(test_modules, root):
			by_test_file.setdefault(_test_module_path(dotted), []).append(source)
			resolved = _module_path(dotted, root)
			if resolved is not None:
				try:
					relative = resolved.resolve().relative_to(root.resolve()).as_posix()
				except ValueError:  # pragma: no cover - a module outside the app root
					continue
				by_test_file.setdefault(relative, []).append(source)

	for raw in changed_paths:
		path = normalise_path(raw)
		if not path:
			continue
		if path in targets:
			wanted.add(path)
		wanted.update(by_test_file.get(path, ()))

	return {source: list(tests) for source, tests in targets.items() if source in wanted}


def _target_map_from_disk(tier: str = "all") -> dict[str, list[str]]:
	"""Load the target map without importing the ``gameplan`` package.

	See the import constraint in the module docstring: ``gameplan.tests`` pulls in frappe,
	which does not exist on a bare checkout. ``config.py`` next door is pure stdlib, so it
	can be loaded straight off disk by path.
	"""
	import importlib.util

	config_path = Path(__file__).resolve().with_name("config.py")
	spec = importlib.util.spec_from_file_location("_gameplan_mutation_config", config_path)
	if spec is None or spec.loader is None:  # pragma: no cover - unreachable for a real file
		raise RuntimeError(f"could not load {config_path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module.target_map(tier)


def read_changed_paths(source: str) -> list[str]:
	"""Read a newline-delimited path list from a file, or from stdin for "-"."""
	text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
	return [line for line in (line.strip() for line in text.splitlines()) if line]


def main(argv: list[str] | None = None) -> int:
	"""Print the mutation targets a diff implicates, one repo-relative path per line.

	Exits 0 whether or not anything matched - "this PR touches no mutation target" is an
	answer, not a failure. The caller distinguishes the two by whether stdout is empty,
	which is why nothing else is ever printed to it.
	"""
	parser = argparse.ArgumentParser(
		prog="scope.py",
		description="Map a list of changed files to mutation targets.",
	)
	parser.add_argument("--changed-files-from", required=True, metavar="PATH", help='file list, or "-"')
	parser.add_argument("--tier", choices=["1", "2", "all"], default="all")
	args = parser.parse_args(argv)

	selected = changed_targets(read_changed_paths(args.changed_files_from), _target_map_from_disk(args.tier))
	for source in selected:
		print(source)
	return 0


if __name__ == "__main__":
	sys.exit(main())
