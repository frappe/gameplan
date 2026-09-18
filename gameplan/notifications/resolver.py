# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Who should be told about an event.

Two inputs decide it. The user's global level (`GP User Profile.notification_level`,
Mentions only or Mute) is the default for every discussion they have not touched. A
`GP Discussion Subscription` row is a deliberate choice on one discussion — Mute, Mentions
only or Watch — and it wins over the global level whenever it exists. Nothing else (being
mentioned, commenting, reading, joining a space) ever changes a user's state.

A `GP Space Subscription` row is the third input, and a narrow one: it says the user wants
to hear about discussions *starting* in (or moving into or out of) that space. It never
changes what they hear about inside a discussion.

Reactions and poll votes are about the user's own content and follow only their own
toggles (see HasReactions.notify_reactions and notify_poll_vote below).
"""

import frappe
from frappe.utils import get_fullname

from gameplan.notifications import records
from gameplan.notifications.preferences import bulk_levels, profile_prefs
from gameplan.permissions import can_view_space, users_who_can_view_content

STATES = ("Mute", "Mentions only", "Watch")


def discussion_of(doc) -> str | None:
	"""The discussion a piece of content lives in, or None (tasks, task comments, pages)."""
	if doc.doctype == "GP Discussion":
		return doc.name
	if doc.doctype == "GP Comment" and doc.reference_doctype == "GP Discussion":
		return doc.reference_name
	if doc.doctype == "GP Poll":
		return doc.discussion
	return None


def subscription_state(user: str, discussion: str) -> str | None:
	"""The explicit state `user` chose on `discussion`, or None when they never chose."""
	return frappe.db.get_value(
		"GP Discussion Subscription", {"user": user, "discussion": discussion}, "state"
	)


def effective_discussion_state(user: str, discussion: str, level: str | None = None) -> str:
	"""Mute, Mentions only or Watch — the explicit choice if there is one, else the global level.

	The global level is never Watch, so Watch only ever comes from a row: watching is always
	a deliberate act, which keeps "every comment" off the table as a default.
	"""
	state = subscription_state(user, discussion)
	if state in STATES:
		return state
	level = level or profile_prefs(user).notification_level
	return "Mute" if level == "Mute" else "Mentions only"


def bulk_discussion_states(users: list[str], discussion: str) -> dict[str, str]:
	"""`effective_discussion_state` for many users with two queries instead of two each."""
	users = list(dict.fromkeys(users))
	if not users:
		return {}
	levels = bulk_levels(users)
	states = {user: ("Mute" if levels[user] == "Mute" else "Mentions only") for user in users}
	rows = frappe.db.get_all(
		"GP Discussion Subscription",
		filters={"discussion": discussion, "user": ["in", users]},
		fields=["user", "state"],
	)
	for row in rows:
		if row.state in STATES:
			states[row.user] = row.state
	return states


def is_muted(user: str, discussion: str) -> bool:
	return effective_discussion_state(user, discussion) == "Mute"


def discussion_watchers(discussion: str) -> list[str]:
	"""Users with an explicit Watch on `discussion`. Only rows can say Watch (see above)."""
	return frappe.db.get_all(
		"GP Discussion Subscription",
		filters={"discussion": discussion, "state": "Watch"},
		pluck="user",
	)


def notify_comment(comment_doc, already_notified: set[str] | None = None) -> list[str]:
	"""Tell everyone watching the discussion that `comment_doc` was posted in it.

	Skips the author, anyone the mention pass already reached for this same comment (one
	comment, one notification), and anyone who cannot open the discussion. Repeat comments
	fold into one unread row per watcher: "3 new comments in <title>".

	Returns the users notified.
	"""
	discussion = discussion_of(comment_doc)
	if not discussion:
		return []

	already_notified = already_notified or set()
	candidates = [
		user
		for user in discussion_watchers(discussion)
		if user != comment_doc.owner and user not in already_notified
	]
	recipients = users_who_can_view_content(candidates, comment_doc)
	if not recipients:
		return []

	title = frappe.db.get_value("GP Discussion", discussion, "title")
	author = get_fullname(comment_doc.owner)
	for user in recipients:
		records.write_or_merge(
			to_user=user,
			type="Comment",
			merge=True,
			from_user=comment_doc.owner,
			discussion=discussion,
			message=f"{author} commented on {title}",
			merged_message=f"{{count}} new comments in {title}",
		)
	return recipients


def space_subscribers(projects: list) -> list[str]:
	"""Users with the space toggle on for any of `projects`, each once."""
	projects = [str(project) for project in projects if project]
	if not projects:
		return []
	users = frappe.db.get_all("GP Space Subscription", filters={"project": ["in", projects]}, pluck="user")
	return list(dict.fromkeys(users))


def notify_new_discussion(discussion_doc) -> list[str]:
	"""Tell the space's subscribers that `discussion_doc` was started in it.

	Runs once, at creation — a discussion moving into the space is a Moved event, not a
	new one. Skips the author and anyone who cannot open the space. Never merges: each
	discussion is its own row, since each one is a different thing to go and read.
	"""
	author = discussion_doc.owner
	candidates = [user for user in space_subscribers([discussion_doc.project]) if user != author]
	recipients = users_who_can_view_content(candidates, discussion_doc)
	if not recipients:
		return []

	space = frappe.db.get_value("GP Project", discussion_doc.project, "title")
	author_name = get_fullname(author)
	for user in recipients:
		records.write_or_merge(
			to_user=user,
			type="New Discussion",
			merge=False,
			from_user=author,
			discussion=discussion_doc.name,
			project=discussion_doc.project,
			team=discussion_doc.team,
			message=f"{author_name} started a discussion in {space}",
		)
	return recipients


def notify_added(user: str, *, project=None, team=None, actor: str | None = None):
	"""Tell `user` that `actor` put them in a space or a community.

	Joining on one's own is not news, so `actor == user` writes nothing. A grant that has
	no acting person behind it (a guest accepting an invitation, where the session is still
	Guest) is worded without one.
	"""
	if not user or actor == user:
		return
	if project:
		target = frappe.db.get_value("GP Project", project, "title")
	else:
		target = frappe.db.get_value("GP Team", team, "title")
	if actor and actor != "Guest":
		message = f"{get_fullname(actor)} added you to {target}"
		from_user = actor
	else:
		message = f"You were added to {target}"
		from_user = None
	records.write_or_merge(
		to_user=user,
		type="Added",
		merge=False,
		from_user=from_user,
		project=str(project) if project else None,
		team=team,
		message=message,
	)


def notify_discussion_moved(discussion_doc, old_project, actor: str) -> list[str]:
	"""Tell the subscribers of the old and the new space that `discussion_doc` moved.

	The discussion's own mute wins — a Mute there means "nothing about this thread" — and
	so does access: someone subscribed to the old space who cannot open the new one is
	not told where it went.
	"""
	candidates = [user for user in space_subscribers([old_project, discussion_doc.project]) if user != actor]
	states = bulk_discussion_states(candidates, discussion_doc.name)
	candidates = [user for user in candidates if states.get(user) != "Mute"]
	recipients = users_who_can_view_content(candidates, discussion_doc)
	if not recipients:
		return []

	space = frappe.db.get_value("GP Project", discussion_doc.project, "title")
	mover = get_fullname(actor)
	for user in recipients:
		records.write_or_merge(
			to_user=user,
			type="Moved",
			merge=False,
			from_user=actor,
			discussion=discussion_doc.name,
			project=discussion_doc.project,
			team=discussion_doc.team,
			message=f"{mover} moved {discussion_doc.title} to {space}",
		)
	return recipients


def notify_space_moved(project_doc, actor: str) -> list[str]:
	"""Tell the space's subscribers that it now sits in another community."""
	candidates = [user for user in space_subscribers([project_doc.name]) if user != actor]
	recipients = [user for user in candidates if can_view_space(user, project_doc)]
	if not recipients:
		return []

	community = frappe.db.get_value("GP Team", project_doc.team, "title")
	mover = get_fullname(actor)
	for user in recipients:
		records.write_or_merge(
			to_user=user,
			type="Moved",
			merge=False,
			from_user=actor,
			project=str(project_doc.name),
			team=project_doc.team,
			message=f"{mover} moved {project_doc.title} to {community}",
		)
	return recipients


def notify_poll_vote(poll_doc, voter: str):
	"""Tell the poll's author that `voter` voted, if they want to hear about votes.

	Votes fold into one unread row per poll ("3 people voted on your poll"); the row is
	linked to the discussion so opening it clears the row. An anonymous poll names nobody
	and links no sender. Retracting a vote is not an event.
	"""
	owner = poll_doc.owner
	if voter == owner or not profile_prefs(owner).notify_poll_votes:
		return
	if poll_doc.anonymous:
		message = "1 person voted on your poll"
		from_user = None
	else:
		message = f"{get_fullname(voter)} voted on your poll"
		from_user = voter
	records.write_or_merge(
		to_user=owner,
		type="Poll Vote",
		merge=True,
		from_user=from_user,
		discussion=poll_doc.discussion,
		poll=poll_doc.name,
		message=message,
		merged_message="{count} people voted on your poll",
	)
