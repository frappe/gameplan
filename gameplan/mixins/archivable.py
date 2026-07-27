# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe
from frappe import _


class Archivable:
	"""
	Mixin to add archive and unarchive methods to a DocType. `archived_at` (Datetime) and
	`archived_by` (Link to User) fields are required for this mixin to work.
	"""

	@frappe.whitelist(methods=["POST"])
	def archive(self):
		self.archived_at = frappe.utils.now()
		self.archived_by = frappe.session.user
		self.save()

	@frappe.whitelist(methods=["POST"])
	def unarchive(self):
		self.archived_at = None
		self.archived_by = None
		self.save()


def check_if_space_is_archived(doc, *, action, content_type):
	"""Reject content mutations that touch an archived Space.

	A save that changes `project` touches both the destination on the current
	document and the source on the stored document. Checking both prevents content
	from escaping an archived Space as part of the same save. Polls reach their
	Space through a discussion; resolving that link here keeps every archive gate
	on the same path.
	"""
	space_names = [_get_space_name(doc)]
	previous_doc = doc.get_doc_before_save()
	if previous_doc:
		space_names.append(_get_space_name(previous_doc))

	for space_name in dict.fromkeys(space_names):
		space = frappe.db.get_value(
			"GP Project",
			space_name,
			["title", "archived_at"],
			as_dict=True,
		)
		if space and space.archived_at:
			frappe.throw(
				_("Space {0} is archived. Cannot {1} {2}.").format(
					space.title,
					action,
					content_type,
				)
			)


def _get_space_name(doc):
	if space_name := doc.get("project"):
		return space_name
	if discussion_name := doc.get("discussion"):
		return frappe.db.get_value("GP Discussion", discussion_name, "project")
