# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Visibility tiers and public-read eligibility."""

import frappe
from frappe import _
from frappe.utils import cint

VISIBILITY_ANONYMOUS = "Anonymous"

VISIBILITY_GENERAL = "General"

VISIBILITY_MEMBER_ACCESS = "Member Access"

VISIBILITY_TIERS = (VISIBILITY_ANONYMOUS, VISIBILITY_GENERAL, VISIBILITY_MEMBER_ACCESS)

SIGNED_IN_TIERS = (VISIBILITY_GENERAL, VISIBILITY_ANONYMOUS)


def is_anonymous_eligible_community(community):
	"""Public eligibility without the site's temporary public-access switch."""
	if not hasattr(community, "get"):
		community = frappe.db.get_value("GP Team", community, ["visibility", "archived_at"], as_dict=True)
	return bool(community and community.visibility == VISIBILITY_ANONYMOUS and not community.archived_at)


def is_anonymous_eligible_space(space):
	if not hasattr(space, "get"):
		space = frappe.db.get_value("GP Project", space, ["visibility", "archived_at", "team"], as_dict=True)
	return bool(
		space
		and space.visibility == VISIBILITY_ANONYMOUS
		and not space.archived_at
		and space.team
		and is_anonymous_eligible_community(space.team)
	)


def require_admin_to_publish(was_public, will_be_public):
	"""Guard existing history becoming eligible for public reading through any action."""
	from gameplan.permissions import is_global_admin

	if not was_public and will_be_public and not is_global_admin(frappe.session.user):
		frappe.throw(_("Only Gameplan Admins can publish existing content"), frappe.PermissionError)


def visibility_tier(value) -> str:
	"""Fail closed: empty or unknown tiers require Member Access."""
	return value if value in VISIBILITY_TIERS else VISIBILITY_MEMBER_ACCESS


def is_member_access(value) -> bool:
	"""Whether only the people on the member list may read something with this tier."""
	return visibility_tier(value) == VISIBILITY_MEMBER_ACCESS


def public_team_criterion(Team):
	"""SQL for "someone who is not signed in may read this community", switch aside."""
	return (Team.visibility == VISIBILITY_ANONYMOUS) & Team.archived_at.isnull()


def anonymous_readable_criterion(Project):
	"""SQL for "someone who is not signed in may read this space", public access switch aside.

	True when the space and its community are both on the Anonymous tier and neither is
	archived. A space outside every community never qualifies: publishing a community is
	the second of the two decisions a public space needs. The switch is not part of it,
	because the switch is read on every request instead of being stored.
	"""
	Team = frappe.qb.DocType("GP Team")
	public_teams = frappe.qb.from_(Team).select(Team.name).where(public_team_criterion(Team))
	return (
		(Project.visibility == VISIBILITY_ANONYMOUS)
		& Project.archived_at.isnull()
		& Project.team.isin(public_teams)
	)


def refresh_anonymous_readable(spaces):
	"""Recompute `GP Project.is_anonymous_readable` for `spaces`.

	Clears the flag first and then sets it where it holds, so a failure between the two
	statements leaves the spaces unreadable to the public rather than readable.
	"""
	spaces = [str(space) for space in spaces]
	if not spaces:
		return
	Project = frappe.qb.DocType("GP Project")
	frappe.qb.update(Project).set(Project.is_anonymous_readable, 0).where(Project.name.isin(spaces)).run()
	(
		frappe.qb.update(Project)
		.set(Project.is_anonymous_readable, 1)
		.where(Project.name.isin(spaces))
		.where(anonymous_readable_criterion(Project))
	).run()


def find_anonymous_readable_drift() -> list[str]:
	"""Every space whose stored `is_anonymous_readable` disagrees with the rule.

	Empty when every lifecycle path that can change the answer has kept the flag current.
	"""
	Project = frappe.qb.DocType("GP Project")
	should_be = set(
		frappe.qb.from_(Project)
		.select(Project.name)
		.where(anonymous_readable_criterion(Project))
		.run(pluck=True)
	)
	rows = frappe.qb.from_(Project).select(Project.name, Project.is_anonymous_readable).run()
	return sorted(str(name) for name, stored in rows if bool(cint(stored)) != (name in should_be))
