"""Argument parsing for ``python -m gameplan.tests.mutation``.

Exit codes are part of this program's contract with CI, so they are documented in
``--help`` rather than only in the source. The rule they encode: a command that measured
nothing never exits 0.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import DEFAULT_SITE, DEFAULT_TIMEOUT, JOURNAL_PATH

RUN_EXIT_CODES = """exit codes:
  0  mutants were evaluated, or every mutant was already journalled
  1  the campaign aborted (too many runs produced no verdict), or it refused to start
  2  bad arguments (e.g. a module with no test mapping)
  3  nothing measured: every targeted module was skipped, or no pending mutant could
     be evaluated. Distinct from 0 so a nightly cannot read a broken site as success.
"""

REPORT_EXIT_CODES = """exit codes:
  0  a score was measured, and it meets --fail-under if given
  1  a score was measured and is below --fail-under
  3  nothing measured: no results, or every mutant produced a non-verdict. This is not
     a score of 0% and deliberately does not share an exit code with one.
"""


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		prog="python -m gameplan.tests.mutation",
		description="Mutation testing harness for the Gameplan Frappe app.",
	)
	sub = parser.add_subparsers(dest="command", required=True)

	run = sub.add_parser(
		"run",
		help="run a mutation campaign",
		description="Run a mutation campaign.",
		epilog=RUN_EXIT_CODES,
		formatter_class=argparse.RawDescriptionHelpFormatter,
	)
	run.add_argument("--tier", choices=["1", "2", "all"], default="1")
	run.add_argument("--module", dest="module", default=None, help="single source path, e.g. gameplan/api.py")
	run.add_argument("--site", default=DEFAULT_SITE)
	run.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="per test-module timeout, seconds")
	run.add_argument("--limit", type=int, default=None, help="stop after N mutants (smoke testing)")
	run.add_argument("--mutate-strings", action="store_true", help="also mutate string literals (noisy here)")
	run.add_argument("--yes", action="store_true", help="auto-restore orphaned backups without prompting")
	run.add_argument("--journal", type=Path, default=JOURNAL_PATH)

	rep = sub.add_parser(
		"report",
		help="summarise journalled results",
		description="Summarise journalled results and gate on them.",
		epilog=REPORT_EXIT_CODES,
		formatter_class=argparse.RawDescriptionHelpFormatter,
	)
	rep.add_argument("--journal", type=Path, default=JOURNAL_PATH)
	rep.add_argument("--format", dest="fmt", choices=["text", "md", "json"], default="text")
	rep.add_argument(
		"--verify-journal",
		dest="verify_path",
		type=Path,
		default=None,
		help="stage-2 results to merge in (default: the sibling of --journal)",
	)
	rep.add_argument(
		"--fail-under",
		type=float,
		default=None,
		metavar="PERCENT",
		help="exit 1 if the overall mutation score is below this percentage",
	)

	ver = sub.add_parser("verify", help="re-run survivors against the full suite")
	ver.add_argument("--journal", type=Path, default=JOURNAL_PATH)
	ver.add_argument(
		"--verify-journal",
		dest="verify_path",
		type=Path,
		default=None,
		help="where to write stage-2 verdicts (default: the sibling of --journal)",
	)
	ver.add_argument("--site", default=DEFAULT_SITE)
	ver.add_argument("--timeout", type=int, default=0, help="0 uses 10x the per-module default")
	ver.add_argument("--limit", type=int, default=None)
	ver.add_argument("--yes", action="store_true")

	sub.add_parser("restore", help="restore source files from orphaned backups after a hard crash")

	return parser


def main(argv: list[str] | None = None) -> int:
	# Imported lazily so `restore` and `report` stay usable even if something in the
	# campaign import chain is broken.
	from . import campaign
	from . import report as report_mod

	args = build_parser().parse_args(argv)

	if args.command == "run":
		return campaign.run_campaign(
			tier=args.tier,
			only_module=args.module,
			site=args.site,
			timeout=args.timeout,
			limit=args.limit,
			mutate_strings=args.mutate_strings,
			assume_yes=args.yes,
			journal_path=args.journal,
		)
	if args.command == "report":
		return report_mod.report(
			journal_path=args.journal,
			fmt=args.fmt,
			verify_path=args.verify_path or report_mod.verify_path_for(args.journal),
			fail_under=args.fail_under,
		)
	if args.command == "verify":
		return campaign.verify(
			journal_path=args.journal,
			# Derived from the same helper the report reads, so stage 2 always writes where
			# stage 3 looks. Left unset, verify wrote the default .mutation/verify.jsonl for
			# every journal: an alternate campaign's verdicts were invisible to its own
			# report and silently overwrote the default campaign's.
			verify_path=args.verify_path or report_mod.verify_path_for(args.journal),
			site=args.site,
			timeout=args.timeout,
			limit=args.limit,
			assume_yes=args.yes,
		)
	if args.command == "restore":
		return campaign.restore_command()
	return 2
