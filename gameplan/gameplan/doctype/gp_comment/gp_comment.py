# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord
from gameplan.mixins.mentions import HasMentions
from gameplan.mixins.reactions import HasReactions
from gameplan.mixins.tags import HasTags
from gameplan.utils import remove_empty_trailing_paragraphs


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
	def get_revisions(self, fieldname="content"):
		revisions = frappe.qb.get_query(
			"Version",
			fields=["data", "creation", "owner"],
			filters={
				"ref_doctype": self.doctype,
				"docname": self.name,
				"data": ["like", f'%"{fieldname}"%'],
			},
			order_by="creation desc",
		).run(as_dict=True)
		response = []
		for revision in revisions:
			data = frappe.parse_json(revision.data) if revision.data else {}
			changes = data.get("changed") or []
			change = next((change for change in changes if change[0] == fieldname), None)
			if not change:
				continue
			response.append(
				{
					"owner": revision.owner,
					"creation": revision.creation,
					"old_value": change[1] or "",
					"new_value": change[2] or "",
				}
			)
		return response
