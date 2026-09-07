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
# produces the same non-verdict, so bail instead of scoring noise.
MAX_CONSECUTIVE_NO_VERDICT = 3

# Source module -> test modules that are expected to cover it. Tier 1 is the
# security/correctness-critical core; tier 2 is everything else worth measuring.
#
# WHAT BELONGS IN A TARGET'S LIST
# -------------------------------
# Stage 1 asks one question - "do the tests that OWN this module pin its behaviour?" -
# so the list is deliberately narrower than "every test file that happens to execute a
# line of it". Stage 2 (verify) is where the whole suite gets a say. Add a module here
# only when it is the primary - usually the only - place some behaviour of the target is
# asserted. Adding one because it merely touches the target buys nothing and costs on
# every mutant.
#
# The cost is real and asymmetric. campaign.run_one_mutant runs the list IN ORDER and
# stops at the first kill, so a module costs its own runtime once per mutant that
# survived everything before it - never once per mutant. The same 7s module is ~18
# minutes on permissions.py (~150 survivors) and under a minute on gp_poll.py (~9).
# Hence the ordering rule: the module that owns most of the target goes first, so the
# later entries are only ever paid for the mutants nothing before them caught.
#
# The other cost is invalidation: a target's list feeds scope.test_fingerprint, so
# editing the list re-measures every verdict that target already had. That is intended
# - a verdict produced by a different set of tests is stale, not settled.
TIER1: dict[str, list[str]] = {
	"gameplan/permissions.py": [
		"gameplan.tests.permissions.test_permission_matrix",
		"gameplan.tests.permissions.test_content_access",
		"gameplan.tests.permissions.test_guest_access",
		"gameplan.tests.permissions.test_visibility",
		# Written FOR this file: it calls content_has_permission, can_interact_with_content
		# and can_delete_content directly with assertIs, to pin the defaults that mutation
		# testing flagged as survivors. Read its module docstring before deleting a branch
		# it covers - and before adding a test for one it says it cannot reach.
		"gameplan.tests.permissions.test_permission_defaults",
		# The community half of guest access. test_guest_access above scopes a guest to
		# their granted SPACES; nothing there reads a GP Team, so can_view_community's
		# guest branch and team_access_criterion's guest criterion answer to this module
		# alone - see its "SPA navigation" section, which exists to pin exactly those two.
		"gameplan.tests.features.test_guest_participation",
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
		# test_profiles covers bento cards, emojis and quick reactions; the account-
		# management methods on the same doctype (change_user_role, disable_user) are
		# specced only here, as the privilege-escalation guards they are.
		"gameplan.tests.features.test_members",
	],
	"gameplan/gameplan/doctype/gp_invitation/gp_invitation.py": [
		# accept() and grant_access() are the only code that hands a user a Gameplan
		# role, and grant_access does it with no click to confirm. test_invitations owns
		# every branch of both.
		"gameplan.tests.features.test_invitations",
	],
	"gameplan/api.py": [
		"gameplan.tests.platform.test_api_endpoints",
		# api.py is a grab-bag, and two of its endpoints are owned by feature specs
		# rather than by the endpoint suite: _invite_by_email and accept_invitation are
		# called directly by test_invitations...
		"gameplan.tests.features.test_invitations",
		# ...and invite_by_email's admin gate and role allow-list, plus get_user_info's
		# "strip other members' emails for a guest" branch, only by test_members.
		"gameplan.tests.features.test_members",
	],
	"gameplan/gameplan/doctype/gp_draft/gp_draft.py": [
		"gameplan.tests.features.test_drafts",
	],
	"gameplan/gameplan/doctype/gp_poll/gp_poll.py": [
		"gameplan.tests.features.test_polls",
		# ongoing_polls_clause has no caller inside the poll doctype - it is the feed's
		# query-builder mirror of poll_has_stopped, and the test that holds the two in
		# step at the closing instant is TestFeedOngoingPolls, which lives with the feed.
		"gameplan.tests.features.test_discussions",
	],
	"gameplan/gameplan/doctype/gp_discussion/api.py": [
		"gameplan.tests.features.test_discussions",
		# The bookmarks feed is the one feed_type test_discussions does not exercise:
		# clause_discussions_bookmarked_by_user is reached only from the Bookmarks page,
		# which is specced with the rest of bookmarking.
		"gameplan.tests.features.test_bookmarks",
	],
	"gameplan/mixins/reactions.py": [
		"gameplan.tests.features.test_reactions",
		# test_reactions owns WHICH change notifies (add/withdraw/swap/own reaction);
		# WHO gets the row and WHICH row it lands in - the can_view_content guard and the
		# per-doctype dispatch that keeps a poll, comment and discussion reaction on
		# separate notifications - are pinned by TestReactionNotifications instead.
		"gameplan.tests.features.test_notifications",
	],
}

# Mutant outcome vocabulary. Kept explicit because the report and the verify stage
# both key off these exact strings.
#
# THE INVARIANT THAT HOLDS THIS HARNESS TOGETHER
# ----------------------------------------------
# Every status is either a VERDICT - the test suite itself judged this mutant - or a
# NON-VERDICT - something other than the suite decided the outcome (a timeout, a wedged
# site, a broken venv, a runner that died mid-suite, a harness bug). A "kill" is a claim
# that the tests detected the mutation; a non-verdict is an ABSENCE of evidence, never
# evidence of coverage. Resolving that ambiguity toward "killed" inflates the score and,
# because the resume logic caches completed work, caches the lie forever. So:
#
#     NO_VERDICT_STATUSES & KILLED_STATUSES == frozenset()   never counted as a kill
#     NO_VERDICT_STATUSES <= NON_SCORING_STATUSES            never reaches the score
#     NO_VERDICT_STATUSES <= RETRYABLE_STATUSES              never cached as done
#
# If you add a status, decide which side of that line it falls on. Anything that is not
# a judgement made by the test suite goes in NO_VERDICT_STATUSES. The three relations
# above are asserted by gameplan/tests/platform/test_mutation_classification.py, so
# breaking one fails the suite instead of silently inflating the mutation score.
STATUS_KILLED = "killed"
STATUS_KILLED_IMPORT_ERROR = "killed-import-error"
STATUS_KILLED_BY_OTHER_SUITE = "killed-by-other-suite"
STATUS_SURVIVED = "survived"
STATUS_BASELINE_SKIP = "baseline-skip"
# The module was never even offered to the suite: its source file is gone (usually a
# rename that config.py did not follow) or its FileGuard could not be built. Journalled
# for the same reason as a red baseline - a module that silently drops out of the corpus
# while its stale verdicts keep counting toward the published score is the exact failure
# this harness is supposed to make impossible.
STATUS_MODULE_SKIP = "module-skip"
# The opposite claim, and the record that CLEARS a skip: "this module has a current
# score". Written whenever a run establishes that - a green baseline, or a module whose
# every mutant is already settled against the current tests.
#
# It exists because a skip's key is fixed per module ("baseline:<path>"), so without a
# later record under the same key nothing ever supersedes it and the skip is immortal.
# Inferring instead that "a mutant record further down the journal means the skip is old"
# is the bug this replaces: journal position is only meaningful over the WHOLE journal,
# and every caller of the report is free to filter it (--new-since, --prune-stale). A
# filtered view then keeps the skip, loses the evidence that aged it out, and resurrects a
# dead skip - turning every pull request red for a module it never touched. Currency is
# therefore stated as data, under the key it supersedes, and no filter can separate them.
STATUS_MODULE_CURRENT = "module-current"
# The harness itself blew up on this mutant (bad AST rewrite, unwritable file).
STATUS_ERROR = "error"
# The suite never started: bench failed to launch, the site was locked, the disk filled up.
STATUS_INFRA_ERROR = "infra-error"
# The run exceeded its budget and was killed. A hung run is not a detection: nothing in
# the suite ever asserted anything about the mutant. See runner/classify for why we do
# not try to separate "mutant caused an infinite loop" from "the box was busy".
STATUS_TIMEOUT = "timeout"
# The suite started and then died without printing a judgement (OOM, lost site lock,
# a crashed worker). Whatever it had run so far proves nothing about this mutant.
STATUS_INCOMPLETE = "incomplete"
# Verify only: the full suite failed with the mutant applied, but the control re-run
# without it failed too, so the suite - not the mutant - is the variable.
STATUS_UNCONFIRMED = "unconfirmed"
# Legacy: campaigns run before timeouts were demoted to non-verdicts journalled this.
# Kept only so those cached fake kills are re-evaluated rather than counted.
STATUS_KILLED_TIMEOUT = "killed-timeout"

# Records that describe a MODULE rather than a mutant. They are never scored and never
# retried (there is no mutant to retry); they exist so that "this module produced no
# measurement tonight" is a fact in the journal instead of a line of stdout nobody reads.
SKIP_STATUSES = frozenset(
	{
		STATUS_BASELINE_SKIP,
		STATUS_MODULE_SKIP,
	}
)

# Every record that describes a MODULE rather than a mutant, i.e. every record keyed
# "baseline:<path>". They all share one key per module, so the journal's last-wins merge
# leaves exactly one of them per module and that one IS the module's current state: either
# "no current score" (a skip) or "score is current" (STATUS_MODULE_CURRENT). Report
# filters must keep or drop them as a class - never score them, never count them as a
# measurement in the rotation, and never let a filter keep the skip while dropping what
# supersedes it.
MODULE_STATUSES = SKIP_STATUSES | {STATUS_MODULE_CURRENT}

KILLED_STATUSES = frozenset(
	{
		STATUS_KILLED,
		STATUS_KILLED_IMPORT_ERROR,
		STATUS_KILLED_BY_OTHER_SUITE,
	}
)

# Outcomes where the suite never delivered a judgement about the mutant.
NO_VERDICT_STATUSES = frozenset(
	{
		STATUS_ERROR,
		STATUS_INFRA_ERROR,
		STATUS_TIMEOUT,
		STATUS_INCOMPLETE,
		STATUS_UNCONFIRMED,
		STATUS_KILLED_TIMEOUT,
	}
)

# Excluded from both the numerator and the denominator of the mutation score, and
# reported on their own. Counting them as kills reports 100% for a suite that never ran;
# counting them in the denominator alone punishes the tests for an infrastructure fault.
NON_SCORING_STATUSES = NO_VERDICT_STATUSES

# ...and because their cause is transient, they are re-evaluated on the next run
# instead of being treated as completed work by the resume logic.
RETRYABLE_STATUSES = NO_VERDICT_STATUSES


def target_map(tier: str) -> dict[str, list[str]]:
	"""Return the source->tests map for ``tier`` ("1", "2" or "all")."""
	if tier == "1":
		return dict(TIER1)
	if tier == "2":
		return dict(TIER2)
	if tier == "all":
		return {**TIER1, **TIER2}
	raise ValueError(f"unknown tier: {tier!r} (expected 1, 2 or all)")
