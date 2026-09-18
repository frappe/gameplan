# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GPDiscussionSubscription(Document):
	"""One user's explicit notification state on one discussion: Mute, Mentions only or Watch.

	The row *is* the "explicitly set" marker. A discussion with no row for a user follows
	their global `GP User Profile.notification_level`; writing a row pins it, and deleting
	the row hands it back to the global default. That is what lets a later change to the
	global level reach every untouched discussion without a single row being rewritten,
	while leaving every deliberate choice alone (see gameplan/notifications/resolver.py).
	"""

	def before_insert(self):
		if not self.user:
			self.user = frappe.session.user


def on_doctype_update():
	# One choice per (user, discussion); the second index is the watcher fan-out on a new
	# comment ("who has Watch on this discussion?").
	frappe.db.add_unique("GP Discussion Subscription", ["user", "discussion"])
	frappe.db.add_index("GP Discussion Subscription", ["discussion", "state"])
