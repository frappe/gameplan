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

import frappe
from frappe import realtime
from frappe.query_builder.functions import Count

# `realtime.publish_realtime` rather than the newer named helpers (`publish_to_user`,
# `publish_to_website`): those only exist on frappe develop, and Gameplan is also tested
# against v16, where importing them fails at module load. Going through the module object
# instead of importing the function also keeps `patch("frappe.realtime.publish_realtime")`
# effective in tests, since the lookup happens at call time.

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
		realtime.publish_realtime(UNREAD_COUNTS_CHANGED, user=user, after_commit=True)


def notify_notification_count_changed(user: str):
	"""Tell one user that their unread notification count moved, and what it now is.

	The number rides along so a tab can recognise the echo of its own change: this event
	goes to every session of the user who caused it too, and a tab already showing that
	number has nothing left to do. Anything else is news.

	Time cannot make that call. Clicking a notification marks it read in the tab and, one
	navigation later, has the server clear the rest of that thread's notifications
	(`GPDiscussion.track_visit`), so any window wide enough to cover the echo also swallows
	the genuine count change arriving right behind it.
	"""
	realtime.publish_realtime(
		NOTIFICATION_COUNT_CHANGED,
		message={"count": unread_notification_count(user)},
		user=user,
		after_commit=True,
	)


def unread_notification_count(user: str) -> int:
	"""How many unread notifications `user` has right now.

	Shared with `gameplan.api.unread_notifications`, which is what the badge fetches: the
	pushed number and the fetched one have to be counted the same way, or the client cannot
	compare them to tell an echo from a change.
	"""
	Notification = frappe.qb.DocType("GP Notification")
	rows = (
		frappe.qb.from_(Notification)
		.select(Count(Notification.name))
		.where((Notification.to_user == user) & (Notification.read == 0))
	).run()
	return rows[0][0] if rows else 0


def notify_users_changed():
	"""Tell every open session that the shared user list changed (name, avatar, role).

	Broadcast rather than per-user on purpose: a profile edit changes what *other* people
	render, so telling only the editor — as the old `refetch_resource("Users")` call did,
	since it defaulted to the session user — leaves every other session stale.

	The *website* room, not the site room. Only System Users join the site room ("all"),
	and Gameplan members are Website Users, so a plain roomless broadcast would reach
	nobody here. Every socket joins the website room.
	"""
	realtime.publish_realtime(USERS_CHANGED, room=realtime.get_website_room(), after_commit=True)
