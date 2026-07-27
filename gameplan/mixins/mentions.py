# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe
from frappe.utils import cint, get_fullname

import gameplan
from gameplan.utils import extract_mentions, extract_rich_quote_authors


class HasMentions:
	def notify_mentions(self):
		mentions_field = getattr(self, "mentions_field", None)
		if not mentions_field:
			return

		mentions = extract_mentions(self.get(mentions_field))
		notified_users = set()
		for mention in mentions:
			# Handle special "everyone" mention
			if mention.email == "_everyone_":
				self._notify_everyone_mention()
				continue

			self._notify_user(mention.email, is_everyone=False)
			notified_users.add(mention.email)
		self._notify_rich_quote_authors(mentions_field, notified_users)

	def _notify_rich_quote_authors(self, mentions_field, notified_users):
		authors = extract_rich_quote_authors(self.get(mentions_field))
		for author in authors:
			if author in notified_users:
				continue
			self._notify_user(author, is_everyone=False, notification_type="Rich Quote")

	def _notify_everyone_mention(self):
		"""Notify every active user who can actually open this post.

		The audience is resolved in a fixed handful of set-based queries instead of
		asking can_view_content once per user: that form costs 2-3 queries each, so an
		@everyone on a 500-member site added ~1,500 synchronous queries inline in the
		request that created the discussion.
		"""
		for user_email in self._everyone_audience():
			self._create_notification(user_email, is_everyone=True)

	def _everyone_audience(self):
		"""The active non-guest users an @everyone here should reach.

		Same rule as _can_notify (author excluded, no one who cannot view the content),
		resolved in bulk.
		"""
		# A user holding both Gameplan roles comes back twice from the roles join.
		users = dict.fromkeys(self._get_all_active_gameplan_users())
		return self._users_who_can_view([user for user in users if user != self.owner])

	def _users_who_can_view(self, users):
		"""The subset of `users` that `can_view_content` would return True for.

		A set-based mirror of can_view_space / can_view_community with the membership
		rows loaded up front, so the query count stays flat as the member list grows.
		Keep it in step with `gameplan.permissions`.
		"""
		from gameplan.permissions import get_content_project, get_project_info, is_global_admin

		project = get_content_project(self)
		if not project:
			# Space-less content is visible to its owner and to global admins only.
			return [user for user in users if is_global_admin(user) or user == self.owner]

		project_info = get_project_info(project)
		if not project_info:
			return []

		space_members = _membership_users("GP Project", project_info.name)
		community_members = _membership_users("GP Team", project_info.team) if project_info.team else set()
		guests = _guest_access_users(project_info.name)
		community_is_private = (
			cint(frappe.db.get_value("GP Team", project_info.team, "is_private")) if project_info.team else 0
		)

		def can_view(user):
			if is_global_admin(user):
				return True
			if gameplan.is_guest(user):
				return user in guests
			if cint(project_info.is_private):
				return user in space_members
			return not community_is_private or user in community_members

		return [user for user in users if can_view(user)]

	def _can_notify(self, user_email):
		"""Nobody gets notified about their own post, or about content they cannot open.

		The mention autocomplete offers every active user and @everyone fans out to all
		of them, so both can address people outside the space. A notification row links
		the discussion/task and the bell shows its title, so notifying someone without
		access would leak that title and hand them a dead link.
		"""
		from gameplan.permissions import can_view_content

		if user_email == self.owner:
			return False
		return can_view_content(user_email, self)

	def _notify_user(self, user_email, is_everyone=False, notification_type="Mention"):
		"""Create a notification for a specific user, if they may be notified at all."""
		if not self._can_notify(user_email):
			return
		self._create_notification(user_email, is_everyone, notification_type)

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

		notification = frappe.get_doc(doctype="GP Notification")
		notification.message = self._get_notification_message(is_everyone, notification_type)
		notification.update(values)
		notification.insert(ignore_permissions=True)

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


def _membership_users(parenttype, parent):
	"""Every user on `parent`'s membership table, as a set."""
	Member = frappe.qb.DocType("GP Member")
	rows = (
		frappe.qb.from_(Member)
		.select(Member.user)
		.where(Member.parenttype == parenttype)
		.where(Member.parent == parent)
		.run()
	)
	return {row[0] for row in rows}


def _guest_access_users(project):
	"""Every user holding guest access to `project`, as a set."""
	GuestAccess = frappe.qb.DocType("GP Guest Access")
	rows = frappe.qb.from_(GuestAccess).select(GuestAccess.user).where(GuestAccess.project == project).run()
	return {row[0] for row in rows}
