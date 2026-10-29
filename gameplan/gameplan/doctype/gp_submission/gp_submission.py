# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from gameplan.mixins.attachments import HasAttachments


class GPSubmission(HasAttachments, Document):
	def validate(self):
		if not self.is_new() or self.status != "Pending":
			frappe.throw("Submitted content and decisions cannot be edited", frappe.PermissionError)
		if not self.project and not self.discussion:
			frappe.throw("Choose a Space or a discussion")
		from gameplan.approval_files import validate_submission_files
		from gameplan.utils.sanitizer import sanitize_content

		self.content = sanitize_content(self.content)
		validate_submission_files(self)

	def after_insert(self):
		self.attach_files_in_content()

	def on_trash(self):
		frappe.throw("Submission history cannot be deleted", frappe.PermissionError)

	def notify_update(self):
		# A shared DocType room must not announce private submission IDs.
		pass


def on_doctype_update():
	frappe.db.add_index("GP Submission", ["owner", "status"], "author_submissions")
	frappe.db.add_index("GP Submission", ["status", "creation"], "approval_queue")
