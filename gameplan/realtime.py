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
NOTIFICATION_CHANGED = "gameplan:notification_changed"
USERS_CHANGED = "gameplan:users_changed"


def notify_unread_counts_changed(users: str | list[str]):
	"""Tell each given user that their space and community unread counts moved."""
	if isinstance(users, str):
		users = [users]
	for user in {user for user in users if user}:
		realtime.publish_realtime(UNREAD_COUNTS_CHANGED, user=user, after_commit=True)


def notify_notification_changed(user: str, notification=None):
	"""Tell one user that a notification of theirs was written, merged or read.

	The message carries two things. `count` is the user's unread total after the change,
	so the badge can be refreshed without a round trip. `notification` is the row that
	changed — `name`, `event_count`, `read`, `last_event_at` — or None for a bulk clear
	(`clear_notifications`, mark-all-as-read) where no single row is the story.

	The row is what lets a tab tell its own echo from real news: this event goes to every
	session of the user who caused it too. A tab already holding that row with the same
	`event_count` and `read` has nothing left to do; anything else — a row it has never
	seen, a merge that bumped the count, a mark-as-read from elsewhere — means reload. The
	unread total alone could not carry that: a repeat event merging into a row that is
	already unread leaves the total exactly where it was.

	Time cannot make that call either. Clicking a notification marks it read in the tab
	and, one navigation later, has the server clear the rest of that thread's
	notifications (`GPDiscussion.track_visit`), so any window wide enough to cover the
	echo also swallows the genuine change arriving right behind it.
	"""
	message = {"count": unread_notification_count(user), "notification": None}
	if notification is not None:
		message["notification"] = {
			"name": notification.name,
			"event_count": notification.event_count,
			"read": notification.read,
			"last_event_at": str(notification.last_event_at) if notification.last_event_at else None,
		}
	realtime.publish_realtime(NOTIFICATION_CHANGED, message=message, user=user, after_commit=True)


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
