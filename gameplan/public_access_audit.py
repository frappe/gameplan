# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Operator checks for public access and signup configuration."""

import frappe
from frappe.utils import cint

from gameplan.public_access import PUBLIC_ACCESS_CONFIG_KEY, public_access_enabled
from gameplan.visibility import find_anonymous_readable_drift, visibility_tier

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

		bench --site <site> execute gameplan.public_access_audit.audit_public_access

	If it lists anything public that nobody meant to publish, stop and fix that first.
	"""
	report = public_access_audit()
	state = "ON" if report.public_access_enabled else "off"
	print(f"Public access: {state} ({PUBLIC_ACCESS_CONFIG_KEY}={int(report.switch_on)})")
	if report.signup_enabled:
		print(f"Signup: open, new accounts get {report.signup_role or 'no Gameplan role'}")
	else:
		print("Signup: closed")

	for label, rows in (("Communities", report.communities), ("Spaces", report.spaces)):
		print(f"\n{label}")
		for row in rows:
			archived = "  (archived)" if row.archived_at else ""
			title = f"{row.team} / {row.title}" if label == "Spaces" else row.title
			print(f"  {title} [{row.name}]: {visibility_tier(row.visibility)}{archived}")
			print(f"      set by {set_by(row)}")

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
