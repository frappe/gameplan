# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord
from gameplan.mixins.attachments import HasAttachments
from gameplan.mixins.mentions import HasMentions
from gameplan.mixins.reactions import HasReactions
from gameplan.mixins.tags import HasTags
from gameplan.permissions import comment_query_conditions, content_has_permission
from gameplan.utils import get_document_revisions, remove_empty_trailing_paragraphs


class GPComment(HasAttachments, HasMentions, HasReactions, HasTags, Document):
	on_delete_cascade = ["GP Draft"]
	on_delete_set_null = ["GP Notification", "GP Discussion"]
	mentions_field = "content"
	tags_field = "content"
	attachments_field = "content"

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
		self.set_edited_at()
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

	def set_edited_at(self):
		if not self.get_doc_before_save():
			return

		if self.has_value_changed("content"):
			self.edited_at = frappe.utils.now()

	def on_update(self):
		self.notify_mentions()
		self.notify_reactions()
		self.attach_files_in_content()

	@frappe.whitelist()
	def get_revisions(self, fieldname="content"):
		return get_document_revisions(self.doctype, self.name, fieldname)


def get_permission_query_conditions(user):
	return comment_query_conditions(user)


def has_permission(doc, ptype="read", user=None):
	return content_has_permission(doc, ptype, user)


def on_doctype_update():
	add_indexes()


def add_indexes():
	# Speeds up the "commented by user" lookups (participating feed and
	# get_participating_unread_count): WHERE owner = ? AND reference_doctype = ?
	# returning reference_name. Without it MariaDB full-scans GP Comment as a
	# per-row dependent subquery — ~18s on large sites vs ~20ms with the index.
	frappe.db.add_index("GP Comment", ["owner", "reference_doctype", "reference_name"], "owner_reference")
