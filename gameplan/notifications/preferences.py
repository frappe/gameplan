# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Per-user notification preferences, read from GP User Profile."""

import frappe

DEFAULT_LEVEL = "Mentions only"
LEVELS = ("Mentions only", "Mute")

PREF_FIELDS = (
	"notification_level",
	"watch_own_discussions",
	"notify_reactions",
	"notify_poll_votes",
	"receive_notifications",
	"active_hours_enabled",
	"active_hours_start",
	"active_hours_end",
	"active_hours_days",
)

_DEFAULTS = frappe._dict(
	notification_level=DEFAULT_LEVEL,
	watch_own_discussions=0,
	notify_reactions=1,
	notify_poll_votes=1,
	receive_notifications=1,
	active_hours_enabled=0,
	active_hours_start=None,
	active_hours_end=None,
	active_hours_days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
)


def profile_prefs(user: str) -> frappe._dict:
	"""The notification fields of `user`'s profile, with defaults for a missing profile.

	Read fresh each time on purpose: it is one indexed lookup, and a cache on
	`frappe.local` would outlive a profile change inside the same request — or, in the
	test runner, the whole run.
	"""
	row = frappe.db.get_value("GP User Profile", {"user": user}, list(PREF_FIELDS), as_dict=True)
	prefs = frappe._dict(_DEFAULTS)
	if row:
		for field in PREF_FIELDS:
			if row.get(field) not in (None, ""):
				prefs[field] = row[field]
	return prefs


def bulk_levels(users: list[str]) -> dict[str, str]:
	"""`user -> notification_level` for many users in one query. Missing profiles default."""
	users = list(dict.fromkeys(users))
	levels = dict.fromkeys(users, DEFAULT_LEVEL)
	if not users:
		return levels
	rows = frappe.db.get_all(
		"GP User Profile",
		filters={"user": ["in", users]},
		fields=["user", "notification_level"],
	)
	for row in rows:
		if row.notification_level in LEVELS:
			levels[row.user] = row.notification_level
	return levels
