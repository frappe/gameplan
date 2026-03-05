# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

import gameplan
from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord
from gameplan.mixins.mentions import HasMentions
from gameplan.mixins.reactions import HasReactions
from gameplan.mixins.tags import HasTags
from gameplan.utils import get_document_revisions, remove_empty_trailing_paragraphs


class GPComment(HasMentions, HasReactions, HasTags, Document):
	on_delete_set_null = ["GP Notification", "GP Discussion"]
	mentions_field = "content"
	tags_field = "content"

	def before_insert(self):
		if self.reference_doctype not in ["GP Discussion"]:
			return

		reference_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if reference_doc.meta.has_field("closed_at"):
			if reference_doc.closed_at:
				frappe.throw("Cannot add comment to a closed discussion")

	def after_insert(self):
		self.update_discussion_meta()
		self.update_task_meta()
		if self.reference_doctype == "GP Discussion":
			GPUnreadRecord.create_unread_records_for_comment(self)

	def on_trash(self):
		if self.reference_doctype == "GP Discussion":
			GPUnreadRecord.delete_unread_records_for_comment(self.name)

	def after_delete(self):
		self.update_discussion_meta()
		self.update_task_meta()

	def before_save(self):
		self.update_tags()

	def update_discussion_meta(self):
		if self.reference_doctype != "GP Discussion":
			return
		discussion = frappe.get_doc("GP Discussion", self.reference_name)
		discussion.update_last_post()
		discussion.update_post_count()
		discussion.update_participants_count()
		discussion.track_visit()
		discussion.save(ignore_permissions=True)

	def update_task_meta(self):
		if self.reference_doctype != "GP Task":
			return
		frappe.get_doc("GP Task", self.reference_name).update_comments_count()

	def validate(self):
		self.sanitize_content()
		self.de_duplicate_reactions()

	def sanitize_content(self):
		from gameplan.utils.sanitizer import sanitize_content

		self.content = remove_empty_trailing_paragraphs(self.content)
		self.content = sanitize_content(self.content)

	def on_update(self):
		self.notify_mentions()
		self.notify_reactions()

	@frappe.whitelist()
	def get_revisions(self, fieldname: str = "content"):
		return get_document_revisions(self.doctype, self.name, fieldname)


def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user

	if not gameplan.is_guest(user):
		return None

	escaped_user = frappe.db.escape(user)
	guest_projects_subquery = f"""(
		select `tabGP Guest Access`.project
		from `tabGP Guest Access`
		where `tabGP Guest Access`.user = {escaped_user}
	)"""

	return f"""(
		(`tabGP Comment`.reference_doctype = 'GP Discussion' and `tabGP Comment`.reference_name in (
			select `tabGP Discussion`.name
			from `tabGP Discussion`
			where `tabGP Discussion`.project in {guest_projects_subquery}
		))
		or
		(`tabGP Comment`.reference_doctype = 'GP Task' and `tabGP Comment`.reference_name in (
			select `tabGP Task`.name
			from `tabGP Task`
			where `tabGP Task`.project in {guest_projects_subquery}
		))
	)"""


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user

	if not gameplan.is_guest(user):
		return True

	project = None
	if doc.reference_doctype == "GP Discussion":
		project = frappe.db.get_value("GP Discussion", doc.reference_name, "project")
	elif doc.reference_doctype == "GP Task":
		project = frappe.db.get_value("GP Task", doc.reference_name, "project")

	if not project:
		return False

	return bool(frappe.db.exists("GP Guest Access", {"user": user, "project": project}))
