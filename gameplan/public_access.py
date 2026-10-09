# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Public read eligibility, request guards and visibility tiers.

Anonymous means logged-out reading, not hidden authors or the unrelated GP Poll.anonymous.
General follows signed-in Member rules. Member Access requires explicit membership.
"""

import time
from urllib.parse import quote

import frappe
from frappe.utils import cint

from gameplan.public_payload import public_doctypes

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
	"""Fail closed: empty or unknown tiers require Member Access."""
	return value if value in VISIBILITY_TIERS else VISIBILITY_MEMBER_ACCESS


def is_member_access(value) -> bool:
	"""Whether only the people on the member list may read something with this tier."""
	return visibility_tier(value) == VISIBILITY_MEMBER_ACCESS


def public_access_enabled() -> bool:
	"""Check the opt-in site switch on every anonymous read.

	Demo mode stays closed: its automatic demo login would silently turn visitors into members.
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
	single-document and method endpoints below, whose output goes through `as_dict`.
	Lists go through Gameplan's own endpoints instead.
	"""
	import frappe.api.v2

	route = anonymous_api_route()
	if not route:
		return
	endpoint, arguments = route
	doctype = arguments.get("doctype")
	allowed = (frappe.api.v2.read_doc, frappe.api.v2.execute_doc_method, frappe.api.v2.handle_rpc_call)
	if doctype in public_doctypes() and endpoint not in allowed:
		frappe.throw("Not permitted", frappe.PermissionError)


# Requests per minute one IP address may make to each of these without signing in. These are
# the reads public access opens to the whole internet, and none is cheap: the feed joins four
# tables, a list or a document runs the permission rules per row, and a file is streamed
# from disk. A thread page makes about four of these calls; the limits leave room for a
# person reading quickly, not for a scraper. Signed-in users are never limited here.
ANONYMOUS_RATE_LIMITS = {
	"gameplan.api.search_sqlite": 30,
	"gameplan.api.get_search_filter_options": 30,
	"gameplan.gameplan.doctype.gp_discussion.api.get_discussions": 60,
	"gameplan.extends.client.get_list": 120,
	"gameplan.public_lists.communities": 60,
	"gameplan.public_lists.spaces": 60,
	"gameplan.public_lists.comments": 120,
	"gameplan.public_lists.polls": 120,
	"gameplan.api.get_public_user_info": 60,
	"gameplan.api.public_file": 600,
	"document": 120,
}
RATE_LIMIT_WINDOW_SECONDS = 60


def limit_anonymous_request_rate():
	"""`before_request`: cap how often one IP address may call the public read paths.

	Counted per address, per endpoint, in fixed one-minute windows in Redis. Anything not in
	ANONYMOUS_RATE_LIMITS is left to frappe (login, signup and the rest have their own).
	"""
	route = anonymous_api_route()
	if not route:
		return
	key = rate_limit_key(*route)
	limit = ANONYMOUS_RATE_LIMITS.get(key)
	if not limit:
		return

	window = int(time.time() // RATE_LIMIT_WINDOW_SECONDS)
	# make_key prefixes the site, so sites on one bench never share a bucket.
	cache_key = frappe.cache.make_key(f"gameplan:public-rate:{key}:{frappe.local.request_ip}:{window}")
	count = frappe.cache.incrby(cache_key, 1)
	if count == 1:
		frappe.cache.expire(cache_key, RATE_LIMIT_WINDOW_SECONDS * 2)
	if count > limit:
		frappe.throw("Too many requests. Please wait a minute, or sign in.", frappe.RateLimitExceededError)


def rate_limit_key(endpoint, arguments):
	"""Which ANONYMOUS_RATE_LIMITS entry a routed request counts against."""
	import frappe.api.v2

	if endpoint is frappe.api.v2.read_doc:
		return "document"
	method = arguments.get("method") or ""
	return method.split("/")[0]


def anonymous_api_route():
	"""`(endpoint, arguments)` for an API request with nobody signed in, else None."""
	import gameplan

	request = getattr(frappe.local, "request", None)
	if not gameplan.is_anonymous() or not request or not request.path.startswith("/api/"):
		return None

	from frappe.api import API_URL_MAP
	from werkzeug.exceptions import HTTPException

	try:
		return API_URL_MAP.bind_to_environ(request.environ).match()
	except HTTPException:
		return None  # not a route; frappe answers it with a 404 or 405


@frappe.whitelist(allow_guest=True)
def realtime_has_permission(doctype: str, name: str = "", ptype: str = "read"):
	"""Keep anonymous visitors out of Gameplan realtime rooms.

	The same permission check admits both document updates and document presence. Presence
	(`doc_open`) broadcasts viewer emails; doctype rooms broadcast editor emails. Public
	read access therefore does not grant realtime access. Signed-in sockets are unchanged.
	"""
	from frappe.realtime import has_permission

	import gameplan

	if gameplan.is_anonymous() and doctype in public_doctypes():
		frappe.throw("Not permitted", frappe.PermissionError)
	return has_permission(doctype, name, ptype)


def gameplan_robots_rules() -> str:
	"""Crawler rules for the app at /g: public spaces may be crawled, nothing else may.

	A space is listed exactly when someone not signed in may read it: public access is on and
	the space is anonymous-readable (`is_anonymous_readable`, kept current with the rule the
	permission checks use). Allow lines come first, for crawlers that take the first match;
	the others take the longest, which is also the Allow. The API is not blocked: it answers
	nobody more than they may read, and a crawler that renders the page needs it.
	"""
	lines = ["# Gameplan: only spaces anyone may read without signing in.", "User-agent: *"]
	if public_access_enabled():
		Project = frappe.qb.DocType("GP Project")
		spaces = (
			frappe.qb.from_(Project)
			.select(Project.team, Project.name)
			.where(Project.is_anonymous_readable == 1)
			.orderby(Project.team)
			.orderby(Project.name)
			.run()
		)
		for team, name in spaces:
			lines.append(f"Allow: /g/community/{quote(str(team))}/space/{quote(str(name))}/")
	lines.append("Disallow: /g/")
	return "\n".join(lines)


# Roles that must never be what a self-registered account gets: each can read every General
# space, so with signup open anyone on the internet could read them.
UNSAFE_SIGNUP_ROLES = ("Gameplan Member", "Gameplan Admin", "System Manager")


def public_access_audit() -> dict:
	"""Everything that decides what people who are not signed in can read, in one place.

	`problems` lists what has to be fixed before public access is switched on, or now, if it
	already is. The rest is for a person to read and confirm: every community and space with
	its tier and who set it, and what is public right now.
	"""
	signup_enabled = not cint(frappe.get_website_settings("disable_signup"))
	signup_role = frappe.db.get_single_value("Portal Settings", "default_role") or ""
	report = frappe._dict(
		switch_on=bool(cint(frappe.conf.get(PUBLIC_ACCESS_CONFIG_KEY))),
		public_access_enabled=public_access_enabled(),
		signup_enabled=signup_enabled,
		signup_role=signup_role,
		communities=frappe.get_all(
			"GP Team",
			fields=["name", "title", "visibility", "visibility_set_by", "visibility_set_at", "archived_at"],
			order_by="title asc",
		),
		spaces=frappe.get_all(
			"GP Project",
			fields=[
				"name",
				"title",
				"team",
				"visibility",
				"is_anonymous_readable",
				"visibility_set_by",
				"visibility_set_at",
				"archived_at",
			],
			order_by="team asc, title asc",
		),
		drift=find_anonymous_readable_drift(),
		problems=[],
	)
	for space in report.spaces:
		space.public_discussions = (
			frappe.db.count("GP Discussion", {"project": space.name}) if space.is_anonymous_readable else 0
		)

	if signup_role in UNSAFE_SIGNUP_ROLES:
		report.problems.append(
			f"Portal Settings gives every new self-registered account the {signup_role} role, which"
			" reads every General space. Set Default Role at Time of Signup to Gameplan Guest."
		)
	if report.drift:
		report.problems.append(
			"is_anonymous_readable disagrees with the tiers for spaces "
			+ ", ".join(report.drift)
			+ ". Save each of them (or their community) to recompute it."
		)
	if report.switch_on and not report.public_access_enabled:
		report.problems.append("Public access is switched on but demo mode keeps it off on this site.")
	return report


def audit_public_access():
	"""Print the public access audit, and fail if it found a problem.

	Run it before switching public access on, and after any change to who may read what:

		bench --site <site> execute gameplan.public_access.audit_public_access

	If it lists anything public that nobody meant to publish, stop and fix that first.
	"""
	report = public_access_audit()
	state = "ON" if report.public_access_enabled else "off"
	print(f"Public access: {state} ({PUBLIC_ACCESS_CONFIG_KEY}={int(report.switch_on)})")
	if report.signup_enabled:
		print(f"Signup: open, new accounts get {report.signup_role or 'no Gameplan role'}")
	else:
		print("Signup: closed")

	print("\nCommunities")
	for community in report.communities:
		archived = "  (archived)" if community.archived_at else ""
		print(f"  {community.title} [{community.name}]: {visibility_tier(community.visibility)}{archived}")
		print(f"      set by {set_by(community)}")

	print("\nSpaces")
	for space in report.spaces:
		archived = "  (archived)" if space.archived_at else ""
		print(f"  {space.team} / {space.title} [{space.name}]: {visibility_tier(space.visibility)}{archived}")
		print(f"      set by {set_by(space)}")

	public = [space for space in report.spaces if space.is_anonymous_readable]
	print(f"\nReadable without signing in{'' if report.public_access_enabled else ' once switched on'}:")
	for space in public:
		print(f"  {space.team} / {space.title} [{space.name}]: {space.public_discussions} discussion(s)")
	if not public:
		print("  nothing")

	if report.problems:
		print("\nProblems")
		for problem in report.problems:
			print(f"  - {problem}")
		frappe.throw(f"Public access audit found {len(report.problems)} problem(s)")
	print("\nNo problems found. Check the lists above: is everything public meant to be?")


def set_by(row) -> str:
	if not row.visibility_set_by:
		return "nobody yet (the tier it was created or migrated with)"
	return f"{row.visibility_set_by} on {row.visibility_set_at}"
