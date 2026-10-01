# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Public read access: letting people who are not signed in read chosen spaces.

A community or a space has one of three visibility tiers:

- Anonymous: anyone with the link can read it, signed in or not.
- General: anyone signed in to Gameplan can read it.
- Member Access: only the people on its member list can read it.

Refer to a tier through the constants below, never a bare string. "Anonymous" as a tier
means "readable by people who are not signed in". It does not mean that the content or its
author is anonymous, and `GP Poll.anonymous` (a poll with hidden voters) is unrelated.
"""

import frappe
from frappe.utils import cint

VISIBILITY_ANONYMOUS = "Anonymous"
VISIBILITY_GENERAL = "General"
VISIBILITY_MEMBER_ACCESS = "Member Access"
VISIBILITY_TIERS = (VISIBILITY_ANONYMOUS, VISIBILITY_GENERAL, VISIBILITY_MEMBER_ACCESS)

# The tiers every signed-in Gameplan user may read without being on a member list. A SQL
# filter must list these rather than exclude Member Access: an empty or unknown value has to
# read as Member Access, and `!= "Member Access"` would let it through.
SIGNED_IN_TIERS = (VISIBILITY_GENERAL, VISIBILITY_ANONYMOUS)

PUBLIC_ACCESS_CONFIG_KEY = "gameplan_public_access_enabled"
VISIBILITY_DOCTYPES = ("GP Team", "GP Project")


def visibility_tier(value) -> str:
	"""`value` as a tier. Anything empty or unknown reads as Member Access, the strictest.

	Fail closed: a row whose tier was never set, or was set to something this code does not
	know, is shown to fewer people rather than more.
	"""
	return value if value in VISIBILITY_TIERS else VISIBILITY_MEMBER_ACCESS


def is_member_access(value) -> bool:
	"""Whether only the people on the member list may read something with this tier."""
	return visibility_tier(value) == VISIBILITY_MEMBER_ACCESS


def public_access_enabled() -> bool:
	"""Whether this site lets people who are not signed in read the Anonymous tier.

	Off unless site config turns it on. Every anonymous read path checks it, so setting
	`gameplan_public_access_enabled` to 0 in site_config.json closes public access on that
	site without a deploy.

	Always off while demo mode is on. On a demo site, opening /g with `?demo` in the URL
	signs the visitor in as a real demo user (see `login_as_demo_user_if_enabled` in
	www/g.py), so a public reader would silently become a member partway through a visit.
	"""
	from gameplan.demo.demo import demo_data_enabled

	if demo_data_enabled():
		return False
	return bool(cint(frappe.conf.get(PUBLIC_ACCESS_CONFIG_KEY)))


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


def find_visibility_backfill_mismatches() -> list[str]:
	"""Every community and space whose `visibility` does not match its old `is_private`.

	The backfill patch maps `is_private = 1` to Member Access and `is_private = 0` to
	General. After it runs, every row must have a tier, must round-trip to the value it
	came from, and must not be Anonymous: publishing is always a person's decision, never
	a migration's. Only meaningful until a tier is changed after the migration, because
	`is_private` is no longer written.
	"""
	mismatches = []
	for doctype in VISIBILITY_DOCTYPES:
		rows = frappe.qb.get_query(doctype, fields=["name", "visibility", "is_private"]).run(as_dict=True)
		for row in rows:
			if row.visibility not in VISIBILITY_TIERS:
				mismatches.append(f"{doctype} {row.name}: visibility is {row.visibility!r}")
			elif row.visibility == VISIBILITY_ANONYMOUS:
				mismatches.append(f"{doctype} {row.name}: backfilled to Anonymous")
			elif (row.visibility == VISIBILITY_MEMBER_ACCESS) != bool(cint(row.is_private)):
				mismatches.append(
					f"{doctype} {row.name}: visibility is {row.visibility}"
					f" but is_private was {row.is_private}"
				)
	return mismatches


def verify_visibility_backfill():
	"""Print every backfill mismatch and fail if there is one.

	Run it on a copy of production data before a release that reads `visibility`:

		bench --site <site> execute gameplan.public_access.verify_visibility_backfill
	"""
	mismatches = find_visibility_backfill_mismatches()
	for mismatch in mismatches:
		print(mismatch)
	if mismatches:
		frappe.throw(f"{len(mismatches)} visibility backfill mismatch(es)")
	print("Visibility backfill verified: every community and space matches its old is_private value.")


def refuse_generic_routes_for_anonymous():
	"""`before_request`: keep anonymous visitors off frappe's generic routes for Gameplan data.

	The Guest role can read a few Gameplan doctypes, and frappe's REST routes answer anyone
	the role layer lets in: `/api/resource/<doctype>` and `/api/v2/document/<doctype>` list
	any columns, `owner` and `modified_by` included, and `?expand_links=1` follows links
	into User. None of that passes through `gameplan.public_payload`. So a request with
	nobody signed in that routes to a doctype the Guest role can read may only reach the
	endpoints in ANONYMOUS_REST_ENDPOINTS, whose output goes through
	`as_dict`. Lists go through Gameplan's own endpoints instead.
	"""
	import gameplan

	request = getattr(frappe.local, "request", None)
	if not gameplan.is_anonymous() or not request or not request.path.startswith("/api/"):
		return

	from frappe.api import API_URL_MAP
	from werkzeug.exceptions import HTTPException

	try:
		endpoint, arguments = API_URL_MAP.bind_to_environ(request.environ).match()
	except HTTPException:
		return  # not a route; frappe answers it with a 404 or 405
	doctype = arguments.get("doctype")
	if doctype in anonymous_readable_doctypes() and endpoint not in anonymous_rest_endpoints():
		frappe.throw("Not permitted", frappe.PermissionError)


def anonymous_rest_endpoints():
	"""The frappe REST endpoints an anonymous visitor may use for a Guest-readable doctype.

	Reading one document (serialised through the controller's `as_dict`) and calling a
	document method (whitelisted with `allow_guest`, or refused by frappe).
	"""
	import frappe.api.v2

	return (frappe.api.v2.read_doc, frappe.api.v2.execute_doc_method, frappe.api.v2.handle_rpc_call)


def anonymous_readable_doctypes():
	"""The doctypes the Guest role can read. Each one's payload is cleaned for anonymous visitors."""
	from gameplan.public_payload import public_doctypes

	return public_doctypes()


@frappe.whitelist(allow_guest=True)
def realtime_has_permission(doctype: str, name: str = "", ptype: str = "read"):
	"""`frappe.realtime.has_permission`, minus doctype-wide rooms for anonymous visitors.

	Both socket servers ask this before letting a socket into a room. Without a `name` the
	room is the whole doctype, and frappe sends it a `list_update` on every save of every
	document of that doctype: its name, and the email of whoever saved it. The role layer
	alone answers yes for the Guest role, so an anonymous socket would hear about every
	comment posted anywhere, private spaces included. A single document's room is still
	allowed: it hears only that document's `doc_update`, and only if the visitor can read it.
	"""
	from frappe.realtime import has_permission

	import gameplan

	if gameplan.is_anonymous() and not name and doctype in anonymous_readable_doctypes():
		frappe.throw("Not permitted", frappe.PermissionError)
	return has_permission(doctype, name, ptype)
