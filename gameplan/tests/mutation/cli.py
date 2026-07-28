"""Argument parsing for ``python -m gameplan.tests.mutation``."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import DEFAULT_SITE, DEFAULT_TIMEOUT, JOURNAL_PATH


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		prog="python -m gameplan.tests.mutation",
		description="Mutation testing harness for the Gameplan Frappe app.",
	)
	sub = parser.add_subparsers(dest="command", required=True)

	run = sub.add_parser("run", help="run a mutation campaign")
	run.add_argument("--tier", choices=["1", "2", "all"], default="1")
	run.add_argument("--module", dest="module", default=None, help="single source path, e.g. gameplan/api.py")
	run.add_argument("--site", default=DEFAULT_SITE)
	run.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="per test-module timeout, seconds")
	run.add_argument("--limit", type=int, default=None, help="stop after N mutants (smoke testing)")
	run.add_argument("--mutate-strings", action="store_true", help="also mutate string literals (noisy here)")
	run.add_argument("--yes", action="store_true", help="auto-restore orphaned backups without prompting")
	run.add_argument("--journal", type=Path, default=JOURNAL_PATH)

	rep = sub.add_parser("report", help="summarise journalled results")
	rep.add_argument("--journal", type=Path, default=JOURNAL_PATH)
	rep.add_argument("--format", dest="fmt", choices=["text", "md", "json"], default="text")

	ver = sub.add_parser("verify", help="re-run survivors against the full suite")
	ver.add_argument("--journal", type=Path, default=JOURNAL_PATH)
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
		return report_mod.report(journal_path=args.journal, fmt=args.fmt)
	if args.command == "verify":
		return campaign.verify(
			journal_path=args.journal,
			site=args.site,
			timeout=args.timeout,
			limit=args.limit,
			assume_yes=args.yes,
		)
	if args.command == "restore":
		return campaign.restore_command()
	return 2
