# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe
from frappe.utils import get_fullname

from gameplan.notifications import records
from gameplan.notifications.resolver import bulk_discussion_states, discussion_of, is_muted
from gameplan.permissions import users_who_can_view_content
from gameplan.utils import extract_mentions, extract_rich_quote_authors


class HasMentions:
	def notify_mentions(self):
		"""Notify the people this post mentions, quotes, or addresses with @everyone.

		Returns the set of users a notification was written for, so the comment fan-out
		that runs next can leave them out: someone watching a discussion who is also
		mentioned in a comment gets that one mention, not a second "new comment" row.
		"""
		mentions_field = getattr(self, "mentions_field", None)
		if not mentions_field:
			return set()

		mentions = extract_mentions(self.get(mentions_field))
		notified_users = set()
		reached = set()
		for mention in mentions:
			# Handle special "everyone" mention
			if mention.email == "_everyone_":
				reached.update(self._notify_everyone_mention())
				continue

			if self._notify_user(mention.email, is_everyone=False):
				reached.add(mention.email)
			notified_users.add(mention.email)
		reached.update(self._notify_rich_quote_authors(mentions_field, notified_users))
		return reached

	def _notify_rich_quote_authors(self, mentions_field, notified_users):
		authors = extract_rich_quote_authors(self.get(mentions_field))
		reached = set()
		for author in authors:
			if author in notified_users:
				continue
			if self._notify_user(author, is_everyone=False, notification_type="Rich Quote"):
				reached.add(author)
		return reached

	def _notify_everyone_mention(self):
		"""Notify every active user who can actually open this post.

		The audience is resolved in a fixed handful of set-based queries instead of
		asking can_view_content once per user: that form costs 2-3 queries each, so an
		@everyone on a 500-member site added ~1,500 synchronous queries inline in the
		request that created the discussion.

		@everyone is a mention, so a user who muted this discussion — explicitly, or by
		default under a global Mute — is left out, resolved in bulk the same way.
		"""
		audience = self._everyone_audience()
		discussion = discussion_of(self)
		if discussion:
			states = bulk_discussion_states(audience, discussion)
			audience = [user for user in audience if states.get(user) != "Mute"]
		for user_email in audience:
			self._create_notification(user_email, is_everyone=True)
		return set(audience)

	def _everyone_audience(self):
		"""The active non-guest users an @everyone here should reach.

		Same rule as _can_notify (author excluded, no one who cannot view the content),
		resolved in bulk. The author is filtered out here, before the permission call:
		users_who_can_view_content answers only "who can see it", and the author
		trivially can.
		"""
		users = self._get_all_active_gameplan_users()
		return users_who_can_view_content([user for user in users if user != self.owner], self)

	def _can_notify(self, user_email):
		"""Nobody gets notified about their own post, about content they cannot open, or
		about a discussion they muted.

		The mention autocomplete offers every active user and @everyone fans out to all
		of them, so both can address people outside the space. A notification row links
		the discussion/task and the bell shows its title, so notifying someone without
		access would leak that title and hand them a dead link.

		Mute is the last check and applies only inside a discussion: a muted discussion is
		the one place a mention does not get through, because muting a specific thread is
		the most pointed signal a user can give. Task mentions have no discussion and are
		unaffected.
		"""
		from gameplan.permissions import can_view_content

		if user_email == self.owner:
			return False
		# A mention or rich quote outlives the account it points at: delete the user (or
		# paste content quoting one) and the email stays in the HTML forever. None of the
		# permission checks below require the User row to exist, and GP Notification.to_user
		# is a Link — so without this the notification insert raises LinkValidationError and
		# takes the whole post save down with it.
		if not frappe.db.exists("User", user_email):
			return False
		if not can_view_content(user_email, self):
			return False
		discussion = discussion_of(self)
		if discussion and is_muted(user_email, discussion):
			return False
		return True

	def _notify_user(self, user_email, is_everyone=False, notification_type="Mention"):
		"""Create a notification for a specific user, if they may be notified at all.

		Returns True when a notification was (or already) exists for them."""
		if not self._can_notify(user_email):
			return False
		self._create_notification(user_email, is_everyone, notification_type)
		return True

	def _create_notification(self, user_email, is_everyone=False, notification_type="Mention"):
		"""Write the notification row. Callers must have cleared `user_email` first."""
		values = frappe._dict(
			from_user=self.owner,
			to_user=user_email,
			type=notification_type,
		)

		if self.doctype == "GP Discussion":
			values.discussion = self.name
		elif self.doctype == "GP Task":
			values.task = self.name
			values.project = self.project
		elif self.doctype == "GP Comment":
			values.comment = self.name
			if self.reference_doctype == "GP Discussion":
				values.discussion = self.reference_name
			elif self.reference_doctype == "GP Task":
				values.task = self.reference_name
				values.project = frappe.db.get_value("GP Task", self.reference_name, "project")

		# Skip if notification already exists
		if frappe.db.exists("GP Notification", values):
			return

		records.write_or_merge(
			message=self._get_notification_message(is_everyone, notification_type),
			merge=False,
			**values,
		)

	def _get_notification_message(self, is_everyone, notification_type):
		author = get_fullname(self.owner)
		post_label = "task" if self._is_task_context() else "post"
		if notification_type == "Rich Quote":
			return f"{author} quoted you in a {post_label}"
		if is_everyone:
			return f"{author} mentioned everyone in a {post_label}"
		return f"{author} mentioned you in a {post_label}"

	def _is_task_context(self):
		return "GP Task" in [self.doctype, self.get("reference_doctype")]

	def _get_all_active_gameplan_users(self):
		"""Get all active Gameplan users except guests"""
		return frappe.qb.get_query(
			"User", filters={"enabled": 1, "roles.role": ["in", ["Gameplan Admin", "Gameplan Member"]]}
		).run(pluck="name")
