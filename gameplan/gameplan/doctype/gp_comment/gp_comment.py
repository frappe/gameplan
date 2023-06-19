# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from gameplan.search import GameplanSearch
from gameplan.mixins.mentions import HasMentions
from gameplan.mixins.reactions import HasReactions
from gameplan.utils import remove_empty_trailing_paragraphs

class GPComment(HasMentions, HasReactions, Document):
	on_delete_set_null = ["GP Notification"]
	mentions_field = 'content'

	def before_insert(self):
		if self.reference_doctype not in ["GP Discussion"]:
			return

		reference_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if reference_doc.meta.has_field("closed_at"):
			if reference_doc.closed_at:
				frappe.throw("Cannot add comment to a closed discussion")

	def after_insert(self):
		if self.reference_doctype not in ["GP Discussion", "GP Task"]:
			return
		reference_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if reference_doc.meta.has_field("last_post_at"):
			reference_doc.set("last_post_at", frappe.utils.now())
		if reference_doc.meta.has_field("last_post_by"):
			reference_doc.set("last_post_by", frappe.session.user)
		if reference_doc.meta.has_field("comments_count"):
			reference_doc.set("comments_count", reference_doc.comments_count + 1)
		if reference_doc.doctype == 'GP Discussion':
			reference_doc.update_participants_count()
			reference_doc.track_visit()
		reference_doc.save(ignore_permissions=True)

	def on_trash(self):
		if self.reference_doctype not in ["GP Discussion", "GP Task"]:
			return
		reference_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if reference_doc.meta.has_field("comments_count"):
			reference_doc.db_set("comments_count", reference_doc.comments_count - 1)

	def validate(self):
		self.content = remove_empty_trailing_paragraphs(self.content)
		self.de_duplicate_reactions()

	def on_update(self):
		self.update_discussion_index()
		self.notify_mentions()
		self.notify_reactions()

	def update_discussion_index(self):
		if self.reference_doctype in ["GP Discussion", "GP Task"]:
			search  = GameplanSearch()
			if self.deleted_at:
				search.remove_doc(self)
			else:
				search.index_doc(self)
