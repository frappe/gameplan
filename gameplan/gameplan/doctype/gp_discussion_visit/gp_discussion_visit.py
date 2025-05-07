# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

import gameplan


class GPDiscussionVisit(Document):
	def after_insert(self):
		gameplan.refetch_resource("UnreadItems", user=self.user)

	def on_change(self):
		if self.has_value_changed("last_visit"):
			gameplan.refetch_resource("UnreadItems", user=self.user)


def on_doctype_update():
	frappe.db.add_index("GP Discussion Visit", ["user", "discussion", "last_visit"])


def after_doctype_insert():
	frappe.db.add_unique("GP Discussion Visit", ["discussion", "user"])
