# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Cypress seed API for Gameplan E2E tests.

This is the new seed surface (eventually replacing test_api.py). It is intentionally
NOT named test_* so that backend test discovery ignores it. Every entry point is gated
behind `enable_ui_tests` in site_config.json, exactly like test_api.py.

`reset(scenario=None)` wipes all Gameplan data, forces the four persona users into a known
state, then optionally builds a named scenario and returns its ids dict.
"""

from contextlib import contextmanager

import frappe

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
	if not frappe.conf.enable_ui_tests:
		frappe.throw("Cannot run UI tests. Set 'enable_ui_tests' in site_config.json to continue.")

	return frappe.whitelist()(fn)


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

	frappe.get_doc("User", "Administrator").add_roles("Gameplan Admin")


def _reset_personas():
	keep_users = ["Administrator", "Guest", *[email for email, _, _ in PERSONAS]]
	for user in frappe.get_all("User", filters={"name": ["not in", keep_users]}):
		frappe.delete_doc("User", user.name)

	for email, first_name, role in PERSONAS:
		if frappe.db.exists("User", email):
			user = frappe.get_doc("User", email)
			user.first_name = first_name
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
	original = frappe.session.user
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.set_user(original)


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


SCENARIOS = {
	"onboarded": _onboarded,
	"space_with_discussion": _space_with_discussion,
	"private_space_with_guest": _private_space_with_guest,
	"two_communities": _two_communities,
	"unread_discussion": _unread_discussion,
}


@whitelist
def rebuild_search_index():
	from gameplan.search_sqlite import GameplanSearch

	GameplanSearch().build_index()
