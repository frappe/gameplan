# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DiscourseIDMap(Document):
	pass


def on_doctype_update():
	# The importer probes this table once per topic (resume check) and once per
	# category/user lookup. Without these it is a full scan of a table that grows to
	# topics + users + categories rows.
	frappe.db.add_unique(
		"Discourse ID Map",
		["discourse_table", "discourse_id"],
		constraint_name="unique_discourse_source",
	)
	frappe.db.add_index(
		"Discourse ID Map",
		["reference_doctype", "reference_name"],
		index_name="reference",
	)
