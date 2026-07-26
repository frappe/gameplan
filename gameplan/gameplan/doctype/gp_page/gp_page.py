# Copyright (c) 2023, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from gameplan.mixins.attachments import HasAttachments
from gameplan.permissions import content_has_permission, page_query_conditions
from gameplan.utils import url_safe_slug


class GPPage(HasAttachments, Document):
	attachments_field = "content"

	def validate(self):
		self.check_if_project_is_archived()

	def before_save(self):
		self.slug = url_safe_slug(self.title)

	def on_update(self):
		self.attach_files_in_content()

	def on_trash(self):
		if not self.flags.from_gameplan_delete_cascade:
			self.check_if_project_is_archived()

	def check_if_project_is_archived(self):
		if not self.project:
			return

		project = frappe.db.get_value("GP Project", self.project, ["name", "archived_at"], as_dict=True)
		if project and project.archived_at:
			frappe.throw(f"Project {project.name} is archived. Cannot modify pages.")


def has_permission(doc, ptype="read", user=None):
	return content_has_permission(doc, ptype, user)


def get_permission_query_conditions(user):
	return page_query_conditions(user)
