# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GPReaction(Document):
	pass


def on_doctype_update():
	# Reactions are always read as a child table: parenttype + parentfield + parent. The
	# framework's default index is on `parent` alone, which MariaDB skips in favour of a
	# full scan once the table is large (116k rows on the imported forum).
	frappe.db.add_index("GP Reaction", ["parenttype", "parentfield", "parent"])
