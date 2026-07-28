"""Paths, target map and status vocabulary for the mutation harness.

Everything here is plain data so the target map stays trivially editable.
"""

from __future__ import annotations

import os
from pathlib import Path

# Derived rather than hardcoded so the harness keeps working if the bench is moved or
# cloned elsewhere. config.py lives at <app>/gameplan/tests/mutation/config.py.
APP_ROOT: Path = Path(__file__).resolve().parents[3]
BENCH_ROOT: Path = Path(os.environ.get("GAMEPLAN_BENCH_ROOT") or APP_ROOT.parents[1])

MUTATION_DIR: Path = APP_ROOT / ".mutation"
BACKUP_DIR: Path = MUTATION_DIR / "backup"
JOURNAL_PATH: Path = MUTATION_DIR / "journal.jsonl"
VERIFY_PATH: Path = MUTATION_DIR / "verify.jsonl"
LOCK_PATH: Path = MUTATION_DIR / "campaign.lock"

DEFAULT_SITE = "gp-sqlite.test"
DEFAULT_TIMEOUT = 120

# Every mutant needs the test site to itself. Once the site is wedged (a leftover
# process holding the lock, a bench that will not start), every remaining mutant
# produces the same infrastructure failure, so bail instead of scoring noise.
MAX_CONSECUTIVE_INFRA_ERRORS = 3

# Source module -> test modules that are expected to cover it. Tier 1 is the
# security/correctness-critical core; tier 2 is everything else worth measuring.
TIER1: dict[str, list[str]] = {
	"gameplan/permissions.py": [
		"gameplan.tests.permissions.test_permission_matrix",
		"gameplan.tests.permissions.test_content_access",
		"gameplan.tests.permissions.test_guest_access",
		"gameplan.tests.permissions.test_visibility",
	],
	"gameplan/email_digest.py": [
		"gameplan.tests.features.test_email_digest",
	],
	"gameplan/gameplan/doctype/gp_unread_record/gp_unread_record.py": [
		"gameplan.tests.features.test_unread",
	],
	"gameplan/gameplan/doctype/gp_team/gp_team.py": [
		"gameplan.tests.features.test_communities",
	],
	"gameplan/gameplan/doctype/gp_project/gp_project.py": [
		"gameplan.tests.features.test_spaces",
	],
}

TIER2: dict[str, list[str]] = {
	"gameplan/gameplan/doctype/gp_user_profile/gp_user_profile.py": [
		"gameplan.tests.features.test_profiles",
	],
	"gameplan/api.py": [
		"gameplan.tests.platform.test_api_endpoints",
	],
	"gameplan/gameplan/doctype/gp_draft/gp_draft.py": [
		"gameplan.tests.features.test_drafts",
	],
	"gameplan/gameplan/doctype/gp_poll/gp_poll.py": [
		"gameplan.tests.features.test_polls",
	],
	"gameplan/gameplan/doctype/gp_discussion/api.py": [
		"gameplan.tests.features.test_discussions",
	],
	"gameplan/mixins/reactions.py": [
		"gameplan.tests.features.test_reactions",
	],
}

# Mutant outcome vocabulary. Kept explicit because the report and the verify stage
# both key off these exact strings.
STATUS_KILLED = "killed"
STATUS_KILLED_IMPORT_ERROR = "killed-import-error"
STATUS_KILLED_TIMEOUT = "killed-timeout"
STATUS_KILLED_BY_OTHER_SUITE = "killed-by-other-suite"
STATUS_SURVIVED = "survived"
STATUS_BASELINE_SKIP = "baseline-skip"
STATUS_ERROR = "error"
# The suite never ran: bench failed to start, the site was locked, the disk filled up.
# Says nothing about the mutant, so it must never reach the score.
STATUS_INFRA_ERROR = "infra-error"

KILLED_STATUSES = frozenset(
	{
		STATUS_KILLED,
		STATUS_KILLED_IMPORT_ERROR,
		STATUS_KILLED_TIMEOUT,
		STATUS_KILLED_BY_OTHER_SUITE,
	}
)

# Outcomes that carry no verdict about the mutant. They are excluded from both the
# numerator and the denominator of the mutation score, and reported on their own.
NON_SCORING_STATUSES = frozenset({STATUS_ERROR, STATUS_INFRA_ERROR})

# ...and because their cause is transient, they are re-evaluated on the next run
# instead of being treated as completed work by the resume logic.
RETRYABLE_STATUSES = NON_SCORING_STATUSES


def target_map(tier: str) -> dict[str, list[str]]:
	"""Return the source->tests map for ``tier`` ("1", "2" or "all")."""
	if tier == "1":
		return dict(TIER1)
	if tier == "2":
		return dict(TIER2)
	if tier == "all":
		return {**TIER1, **TIER2}
	raise ValueError(f"unknown tier: {tier!r} (expected 1, 2 or all)")
