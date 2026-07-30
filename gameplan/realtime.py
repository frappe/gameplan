# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Realtime events Gameplan publishes to the browser.

One function per event, and each event names *what changed* rather than what the client
should refetch — the client owns that decision. The previous `refetch_resource` helper
inverted this: it named a frappe-ui `createResource` cache key, so the server had to know
how the client stored its data. When the frontend moved to `useCall`/`useList` those keys
stopped resolving and every push became a silent no-op, with nothing to fail loudly.

Event names are mirrored by `GameplanSocketEvents` in frontend/src/socket.ts; renaming one
means changing both sides. Everything is published `after_commit` so a rolled-back request
never announces a change that did not happen. Frappe dedupes identical (event, message,
room) triples within a request, so publishing the same event twice for one user emits once.
"""

from frappe.realtime import publish_to_user, publish_to_website

# `gameplan:` namespaces these against frappe's own realtime events (`list_update`,
# `doc_update`, ...) and against other apps sharing the site.
UNREAD_COUNTS_CHANGED = "gameplan:unread_counts_changed"
NOTIFICATION_COUNT_CHANGED = "gameplan:notification_count_changed"
USERS_CHANGED = "gameplan:users_changed"


def notify_unread_counts_changed(users: str | list[str]):
	"""Tell each given user that their space and community unread counts moved."""
	if isinstance(users, str):
		users = [users]
	for user in {user for user in users if user}:
		publish_to_user(user, UNREAD_COUNTS_CHANGED, after_commit=True)


def notify_notification_count_changed(user: str):
	"""Tell one user that their unread notification count moved."""
	publish_to_user(user, NOTIFICATION_COUNT_CHANGED, after_commit=True)


def notify_users_changed():
	"""Tell every open session that the shared user list changed (name, avatar, role).

	Broadcast rather than per-user on purpose: a profile edit changes what *other* people
	render, so telling only the editor — as the old `refetch_resource("Users")` call did,
	since it defaulted to the session user — leaves every other session stale.

	The *website* room, not the site room. Only System Users join the site room ("all"),
	and Gameplan members are Website Users, so a plain roomless broadcast would reach
	nobody here. Every socket joins the website room.
	"""
	publish_to_website(USERS_CHANGED, after_commit=True)
