# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GPReaction(Document):
	"""One person's emoji on one post (a discussion, comment or poll).

	Reactions live in their own table, not as child rows of the post, so that saving
	the post never rewrites them. GP Reaction has no roles beyond System Manager: the
	app reads and writes reactions only through HasReactions."""


def on_doctype_update():
	frappe.db.add_index("GP Reaction", ["reference_doctype", "reference_name"])
