# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

"""Public contract for Gameplan demo data.

External callers depend on the names in this module:
- ``gameplan/hooks.py`` schedules :func:`generate_data_daily`.
- ``gameplan/www/g.py`` uses :func:`demo_data_enabled` and :func:`get_random_users`.

The actual replay lives in :mod:`gameplan.demo.seeder`.
"""

import os

import frappe

from gameplan.demo.seeder import DEMO_EMAIL_DOMAIN, DEMO_FILE_FOLDER, MAYA_EMAIL, Seeder

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixture")

# Every Gameplan doctype table is truncated on clear; these carry an
# autoincrement sequence that must restart so names stay stable across reseeds.
_SEQUENCE_DOCTYPES = [
	"GP Discussion",
	"GP Comment",
	"GP Poll",
	"GP Task",
	"GP Page",
	"GP Project",
	"GP Custom Emoji",
	"GP Notification",
	"GP Draft",
]


def generate(fixture_path: str | None = None, force: bool = False):
	"""Clear existing demo data and replay the event-log fixture.

	``fixture_path`` points at a directory containing ``events.jsonl`` and a
	``files/`` folder; it defaults to the bundled fixture. Refuses politely (no
	error) if the fixture is missing.
	"""
	_assert_not_in_migration()

	fixture_dir = fixture_path or FIXTURE_DIR
	events_path = os.path.join(fixture_dir, "events.jsonl")
	if not os.path.exists(events_path):
		print(f"Demo fixture not found at {events_path}. Nothing to generate.")
		return

	# clear() commits, so validate the whole log first: a fixture the seeder cannot
	# finish would otherwise leave the site wiped and the replay half-applied
	# (the failed events roll back, the committed delete does not).
	problems = Seeder.validate_events(events_path)
	if problems:
		shown = "\n".join(problems[:5])
		if len(problems) > 5:
			shown += f"\n... and {len(problems) - 5} more"
		frappe.throw(
			f"Refusing to clear the site: {events_path} cannot be replayed.\n{shown}",
			title="Invalid Demo Fixture",
		)

	if not clear(force=force):
		# Guard refused (real data present); never replay on top of it.
		return

	search_was_disabled = frappe.conf.get("disable_gameplan_search")
	mute_emails_before = frappe.flags.mute_emails
	frappe.conf.disable_gameplan_search = True
	frappe.flags.mute_emails = True
	try:
		seeder = Seeder(fixture_dir)
		seeder.run(events_path)
		frappe.db.commit()
	finally:
		frappe.conf.disable_gameplan_search = search_was_disabled
		frappe.flags.mute_emails = mute_emails_before

	_rebuild_search_index()
	print(f"Demo data generated: {dict(seeder.counts)}")


def clear(force: bool = False) -> bool:
	"""Delete all Gameplan data and the demo users, files and folder.

	Unless ``force`` is set, aborts if the site looks like it holds real data
	(any Gameplan row owned by a non-demo account). Returns ``True`` if the site
	was cleared, ``False`` if the guard refused.
	"""
	if not force and _has_real_data():
		print("Refusing to clear: non-demo Gameplan data detected. Pass force=True to override.")
		return False

	# Raw deletes (no FKs between Frappe tables), so table order does not matter.
	for doctype in _gameplan_doctypes():
		frappe.db.delete(doctype)

	for user in _demo_user_emails():
		frappe.delete_doc("User", user, ignore_permissions=True, force=True, delete_permanently=True)

	_delete_demo_files()
	_reset_sequences()
	frappe.db.commit()
	return True


def generate_data_daily():
	"""Scheduler entry point: regenerate demo data on sites that opt in.

	Runs with the real-data guard active (no ``force``): if the flag is ever set
	on a site that holds real Gameplan content, the nightly job refuses to clear
	rather than destroying it.
	"""
	if not demo_data_enabled():
		return

	generate()


def demo_data_enabled() -> bool:
	return bool(frappe.conf.get("gameplan_demo_enabled", False))


def get_random_users(limit: int | None = None) -> list[str]:
	"""Return demo user emails, always with Maya first (she is the demo viewer)."""
	emails = frappe.get_all(
		"User",
		filters={"enabled": 1, "email": ["like", f"%{DEMO_EMAIL_DOMAIN}"]},
		pluck="email",
		order_by="creation asc",
	)
	ordered = [MAYA_EMAIL] if MAYA_EMAIL in emails else []
	ordered += [email for email in emails if email != MAYA_EMAIL]
	return ordered[:limit] if limit else ordered


# ---- internals --------------------------------------------------------------


def _assert_not_in_migration():
	# Unread records and other side effects early-return under in_migrate/in_patch,
	# which would silently produce a broken, half-seeded demo.
	if frappe.flags.in_migrate or frappe.flags.in_patch:
		frappe.throw("Demo data cannot be generated during migrate/patch.")


def _gameplan_doctypes() -> list[str]:
	return frappe.get_all("DocType", filters={"module": "Gameplan", "issingle": 0}, pluck="name")


def _demo_user_emails() -> list[str]:
	return frappe.get_all("User", filters={"email": ["like", f"%{DEMO_EMAIL_DOMAIN}"]}, pluck="email")


# GP User Profile is created by the User `after_insert` hook, so it is always
# owned by Administrator, for demo and real users alike. Administrator ownership
# there is therefore not a real-data signal. Every other Gameplan doctype is only
# ever seeded as a demo user, so an Administrator-owned row elsewhere means real
# content (an admin session or an import job) that clear() must not destroy.
_ADMIN_OWNED_FRAMEWORK_DOCTYPES = {"GP User Profile"}


def _has_real_data() -> bool:
	"""True if any Gameplan row is owned by a real (non-demo) account.

	``clear()`` truncates every doctype in :func:`_gameplan_doctypes`, so the
	guard spans exactly that set; a hand-picked subset would silently drift out
	of sync with what gets deleted. A row is "real" when its owner is neither a
	demo user nor (for the framework-created profile rows) Administrator.
	"""
	demo_owner = f"%{DEMO_EMAIL_DOMAIN}"
	for doctype in _gameplan_doctypes():
		filters = [["owner", "not like", demo_owner]]
		if doctype in _ADMIN_OWNED_FRAMEWORK_DOCTYPES:
			filters.append(["owner", "!=", "Administrator"])
		if frappe.get_all(doctype, filters=filters, limit=1):
			return True
	return False


def _delete_demo_files():
	if not frappe.db.exists("File", DEMO_FILE_FOLDER):
		return
	for name in frappe.get_all("File", filters={"folder": DEMO_FILE_FOLDER}, pluck="name"):
		frappe.delete_doc("File", name, ignore_permissions=True, force=True, delete_permanently=True)
	frappe.delete_doc("File", DEMO_FILE_FOLDER, ignore_permissions=True, force=True)


def _reset_sequences():
	for doctype in _SEQUENCE_DOCTYPES:
		sequence = frappe.scrub(doctype) + "_id_seq"
		try:
			frappe.db.sql(f"ALTER SEQUENCE `{sequence}` RESTART WITH 1")
		except Exception:
			# Sequence may not exist on this DB backend; ignore.
			pass


def _rebuild_search_index():
	from gameplan.search_sqlite import build_index

	try:
		build_index()
	except Exception:
		frappe.log_error(title="Demo Search Index Rebuild Error")
