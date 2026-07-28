# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Cypress seed API for Gameplan E2E tests.

This is the only seed surface for Cypress. It is intentionally NOT named test_* so that
backend test discovery ignores it, and every entry point goes through the layered
`whitelist` gate below.

`reset(scenario=None)` wipes all Gameplan data, forces the four persona users into a known
state, then optionally builds a named scenario and returns its ids dict.
"""

from contextlib import contextmanager
from functools import wraps

import frappe
from frappe.tests.utils import whitelist_for_tests
from frappe.utils import cint

# Roles this seed API may mint an invitation for. `gameplan.api.accept_invitation` is
# `allow_guest`, GET-reachable, and hands the invitation's role straight to
# `user.append_roles`, so an unrestricted `role` here would be a privilege-escalation
# primitive: mint yourself a "Gameplan Admin" invitation, then open the link.
INVITABLE_ROLES = ("Gameplan Member", "Gameplan Guest")

PERSONAS = [
	("member@example.com", "Member", "Gameplan Member"),
	("member2@example.com", "Second Member", "Gameplan Member"),
	("guest@example.com", "Guest", "Gameplan Guest"),
	("outsider@example.com", "Outsider", "Gameplan Member"),
]

MEMBER = "member@example.com"
SECOND_MEMBER = "member2@example.com"
GUEST = "guest@example.com"


def whitelist(fn):
	"""POST-only whitelist for the Cypress seed API, behind three independent gates.

	These endpoints delete every Gameplan row and every framework `User` bar the
	personas, so one truthy config key is not a boundary worth having. Bench installs an
	app by putting its repo directory on `sys.path`, so this file is present on every
	production server and packaging cannot exclude it — the gating has to be at runtime.

	Gate 1 is frappe's own `whitelist_for_tests`, which refuses unless the process is a
	test run, a dev server (`bench start`, or `DEV_SERVER=1 bench serve`) with
	`allow_tests` in the site config, or CI. A production server is none of those, which
	makes this module dead there whatever `site_config.json` says.

	Gate 2 is `enable_ui_tests`, read through `cint` so a *string* like "0" or "false" in
	`site_config.json` reads as disabled rather than as a truthy string.

	Gate 3 is System Manager. Cypress drives every one of these as Administrator, whom
	`frappe.only_for` waves through, so the check only costs a logged-in non-admin — which
	is exactly who should not be able to wipe the site.
	"""

	@wraps(fn)
	def guarded(*args, **kwargs):
		if not cint(frappe.conf.enable_ui_tests):
			frappe.throw(
				"Cannot run UI tests. Set 'enable_ui_tests' to 1 in site_config.json to continue. "
				'The value is read with cint, so the quoted strings "true"/"false"/"0" all read '
				"as disabled — use a number or a JSON boolean."
			)
		frappe.only_for("System Manager", message=True)
		return fn(*args, **kwargs)

	return whitelist_for_tests(methods=["POST"])(guarded)


@whitelist
def reset(scenario=None):
	"""Wipe Gameplan data, reset personas, optionally build a scenario. Returns its ids."""
	_delete_gameplan_data()
	_reset_personas()

	if scenario is None:
		return {}

	if scenario not in SCENARIOS:
		valid = ", ".join(sorted(SCENARIOS))
		frappe.throw(f"Unknown scenario '{scenario}'. Valid scenarios: {valid}")

	return SCENARIOS[scenario]()


def _delete_gameplan_data():
	for doctype in frappe.get_all("DocType", filters={"module": "Gameplan"}, pluck="name"):
		frappe.db.delete(doctype)

	administrator = frappe.get_doc("User", "Administrator")
	for role in list(administrator.roles):
		if role.role.startswith("Gameplan "):
			administrator.remove(role)
	administrator.append_roles("Gameplan Admin")
	administrator.save(ignore_permissions=True)


def _reset_personas():
	keep_users = ["Administrator", "Guest", *[email for email, _, _ in PERSONAS]]
	for user in frappe.get_all("User", filters={"name": ["not in", keep_users]}):
		frappe.delete_doc("User", user.name)

	for email, first_name, role in PERSONAS:
		if frappe.db.exists("User", email):
			user = frappe.get_doc("User", email)
			user.first_name = first_name
			user.middle_name = None
			user.last_name = None
		else:
			user = frappe.get_doc(
				doctype="User",
				email=email,
				first_name=first_name,
				send_welcome_email=0,
			)
		user.enabled = 1
		user.new_password = "admin"
		# Personas use a shared trivial password; the site's password policy would reject it.
		user.flags.ignore_password_policy = True
		user.save(ignore_permissions=True)
		if role not in frappe.get_roles(email):
			user.add_roles(role)


# -- scenario builders -------------------------------------------------------


@contextmanager
def _as_user(user):
	"""Run a block as `user` so documents get the right owner at insert time.

	Owner matters beyond the `owner` column: GP Discussion's `after_insert` creates an
	unread record for every space member *except* the owner. Inserting as Administrator
	and rewriting `owner` afterwards would leave the seeded owner holding an unread
	record for their own post — a state the product can never produce.
	"""
	original_user = frappe.session.user
	original_sid = frappe.session.sid
	original_data = frappe.session.data
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.set_user(original_user)
		# frappe.set_user() also overwrites session.sid (with the username) and clears
		# session.data. Left that way, the caller's real session no longer resolves and
		# every request after this one in the same Cypress session falls back to Guest.
		frappe.session.sid = original_sid
		frappe.session.data = original_data


def _create_community(title):
	"""Community that always includes member + member2 so their sidebars resolve."""
	community = frappe.get_doc(doctype="GP Team", title=title)
	for email in (MEMBER, SECOND_MEMBER):
		community.append("members", {"user": email})
	community.insert(ignore_permissions=True)
	return community


def _general_space(community):
	return frappe.db.get_value("GP Project", {"team": community.name, "title": "General"}, "name")


def _create_space(title, community, *, is_private=0, members=()):
	space = frappe.get_doc(doctype="GP Project", title=title, team=community.name, is_private=is_private)
	for email in members:
		space.append("members", {"user": email})
	space.insert(ignore_permissions=True)
	return space


def _create_discussion(title, space, *, content="Seed content", owner=MEMBER):
	with _as_user(owner):
		return frappe.get_doc(doctype="GP Discussion", title=title, project=space, content=content).insert(
			ignore_permissions=True
		)


def _create_page(title, space, *, content="Seed content", owner=MEMBER):
	with _as_user(owner):
		return frappe.get_doc(doctype="GP Page", title=title, project=space, content=content).insert(
			ignore_permissions=True
		)


def _onboarded():
	community = _create_community("Acme")
	return {"community": community.name, "space": _general_space(community)}


def _space_with_discussion():
	community = _create_community("Acme")
	space = _create_space("Engineering", community)
	discussion = _create_discussion("Welcome thread", space.name)
	return {
		"community": community.name,
		"space": space.name,
		# The empty auto-created General space: a second space to move content into, and
		# the one place a spec can assert an empty state.
		"general_space": _general_space(community),
		"discussion": discussion.name,
		"discussion_slug": discussion.slug,
	}


def _private_space_with_guest():
	community = _create_community("Acme")
	general = _general_space(community)
	private_space = _create_space("Secret Plans", community, is_private=1, members=[MEMBER])
	frappe.get_doc(doctype="GP Guest Access", user=GUEST, project=private_space.name).insert(
		ignore_permissions=True
	)
	# Both discussions share the word "roadmap" so a single search separates who may see
	# what: member is in the private space, member2 is only in the community.
	public_discussion = _create_discussion(
		"Public roadmap", general, content="Roadmap notes everyone in the community can read."
	)
	discussion = _create_discussion(
		"Secret thread", private_space.name, content="Roadmap notes only the space members can read."
	)
	return {
		"community": community.name,
		"space": general,
		"private_space": private_space.name,
		"discussion": discussion.name,
		"public_discussion": public_discussion.name,
	}


def _unread_discussion():
	"""One community, two spaces, and a post the member has not read.

	The unread record is not seeded: GP Discussion's `after_insert` creates one for every
	space member except the owner, so a post written by member2 is genuinely unread for
	member.
	"""
	community = _create_community("Acme")
	general = _general_space(community)
	second_space = _create_space("Product", community)
	discussion = _create_discussion(
		"Unread thread", general, content="Something to catch up on.", owner=SECOND_MEMBER
	)
	return {
		"community": community.name,
		"space": general,
		"second_space": second_space.name,
		"discussion": discussion.name,
	}


def _two_communities():
	alpha = _create_community("Alpha")
	beta = _create_community("Beta")
	alpha_space = _create_space("Alpha Space", alpha)
	beta_space = _create_space("Beta Space", beta)
	return {
		"communities": [alpha.name, beta.name],
		"spaces": [alpha_space.name, beta_space.name],
	}


def _search_page():
	acme = _create_community("Acme")
	general = _general_space(acme)
	engineering = _create_space("Engineering", acme)
	beta = _create_community("Beta")
	beta_space = _create_space("Beta Space", beta)

	launch_tag = '<span class="tag-item" data-tag-label="launch">#launch</span>'
	target = _create_discussion(
		"Launch roadmap",
		engineering.name,
		content=f"<p>The launch roadmap is ready.</p>{launch_tag}",
	)
	_create_discussion(
		"Design roadmap",
		engineering.name,
		content=f"<p>A roadmap written by another author.</p>{launch_tag}",
		owner=SECOND_MEMBER,
	)
	_create_discussion(
		"Beta roadmap",
		beta_space.name,
		content=f"<p>A roadmap in another community.</p>{launch_tag}",
	)
	_create_discussion(
		"General roadmap",
		general,
		content=f"<p>A roadmap in another space.</p>{launch_tag}",
	)
	_create_page("Engineering roadmap page", engineering.name)
	_create_discussion(
		"Untagged roadmap",
		engineering.name,
		content='<p>A roadmap with a different tag.</p><span class="tag-item" '
		'data-tag-label="planning">#planning</span>',
	)

	return {
		"community": acme.name,
		"space": engineering.name,
		"discussion": target.name,
	}


SCENARIOS = {
	"onboarded": _onboarded,
	"space_with_discussion": _space_with_discussion,
	"private_space_with_guest": _private_space_with_guest,
	"search_page": _search_page,
	"two_communities": _two_communities,
	"unread_discussion": _unread_discussion,
}


@whitelist
def rebuild_search_index():
	"""Rebuild the search index from scratch, discarding rows from earlier scenarios.

	A bare `build_index()` would not: `reset()` has just deleted every Gameplan row, and
	`build_index` only clears `search_fts` when it is creating the index file, so each
	scenario's rows would pile up on the last one's. See `rebuild_index`.
	"""
	from gameplan.search_sqlite import rebuild_index

	rebuild_index()


@whitelist
def create_invitation(email, role="Gameplan Member", projects=None):
	"""Mint a pending GP Invitation and return its key so a spec can drive the
	accept journey (visit /api/method/gameplan.api.accept_invitation?key=...).

	`role` is restricted to `INVITABLE_ROLES`: the accept endpoint is `allow_guest` and
	GET-reachable, so a caller-chosen role would let anyone hand themselves
	"Gameplan Admin" by minting an invitation and opening its link. The specs only ever
	need the two non-privileged roles.

	`invite_via_email` short-circuits when `dev_server` is set, so we toggle it
	to keep the seed from sending (or failing to send) a real email.
	"""
	if role not in INVITABLE_ROLES:
		frappe.throw(
			f"Cannot mint an invitation for role {role!r}. "
			f"This seed endpoint only issues: {', '.join(INVITABLE_ROLES)}."
		)

	previous = getattr(frappe.local, "dev_server", None)
	frappe.local.dev_server = True
	try:
		invitation = frappe.get_doc(
			doctype="GP Invitation",
			email=email,
			role=role,
			projects=frappe.as_json(projects) if projects else None,
		).insert(ignore_permissions=True)
	finally:
		frappe.local.dev_server = previous

	return {"name": invitation.name, "email": invitation.email, "key": invitation.key}
