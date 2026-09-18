# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from gameplan.mixins.on_delete import delete_linked_records
from gameplan.notifications.cleanup import reset_space_for_user
from gameplan.notifications.resolver import notify_added


class GPGuestAccess(Document):
	# The row is the guest's whole reach into a space, so it is where "you were added"
	# and "you no longer have it" both belong — every path that grants or revokes a guest
	# (invite, accept, remove_guest, remove_guest_access) goes through it.
	def after_insert(self):
		notify_added(self.user, project=self.project, team=self.team, actor=frappe.session.user)

	def on_trash(self):
		projects = [self.project]
		if not self.project:
			projects = frappe.get_all("GP Project", {"team": self.team}, pluck="name")
		for project in projects:
			reset_space_for_user(project, self.user)


def on_user_delete(doc, method):
	delete_linked_records("User", doc.name, ["GP Guest Access"])
