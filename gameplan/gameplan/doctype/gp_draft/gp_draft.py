# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document


class GPDraft(Document):
	@staticmethod
	def get_list(query):
		GPDraft = frappe.qb.DocType("GP Draft")
		query = query.where(GPDraft.owner == frappe.session.user)
		return query

	@frappe.whitelist()
	def publish(self):
		if self.owner != frappe.session.user:
			frappe.throw("You are not allowed to publish this draft")

		if self.type == "Discussion":
			content = remove_query_params_from_images(self.content)
			discussion = frappe.new_doc(
				"GP Discussion", title=self.title, content=content, project=self.project
			).insert()
			attachments = frappe.db.get_all(
				"File",
				filters={"attached_to_doctype": "GP Draft", "attached_to_name": self.name},
				fields=["file_name", "file_url", "is_private", "name"],
			)
			for attachment in attachments:
				file = frappe.new_doc(
					"File",
					file_name=attachment.file_name,
					file_url=attachment.file_url,
					is_private=attachment.is_private,
					attached_to_doctype=discussion.doctype,
					attached_to_name=discussion.name,
				)
				file.insert()

			self.delete()
			return discussion.name


def remove_query_params_from_images(content):
	# replace strings like src="/path/to/image.jpg?fid=param" with src="/path/to/image.jpg"
	# because when we publish draft, images linked to the draft are deleted
	# presence of fid=<name> in the image url prevents the image from being displayed
	pattern = r'(src="[^"]+)\?[^"]*(")'
	return re.sub(pattern, r"\1\2", content)
