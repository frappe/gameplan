# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe

doctypes = {
	"Team": "GP Team",
	"Team Project": "GP Project",
	"Team Discussion": "GP Discussion",
	"Team Task": "GP Task",
	"Team Comment": "GP Comment",
	"Team Member": "GP Member",
	"Team Discussion Visit": "GP Discussion Visit",
	"Team Notification": "GP Notification",
	"Team User Profile": "GP User Profile",
	"Team Activity": "GP Activity",
	"Team Reaction": "GP Reaction",
}


def execute():
	rename_doctypes()
	create_sequences()
	rename_doctype_links()


def rename_doctypes():
	for old in doctypes:
		new = doctypes[old]
		if not frappe.db.exists("DocType", new):
			print(f"Renaming {old} to {new}")
			frappe.rename_doc("DocType", old, new, force=True, ignore_if_exists=True)


def create_sequences():
	doctypes = [
		"GP Discussion",
		"GP Comment",
		"GP Project",
		"GP Notification",
		"GP Task",
		"GP Discussion Visit",
		"GP Member",
		"GP Reaction",
	]
	for doctype in doctypes:
		sequence_name = frappe.scrub(doctype + "_id_seq")
		frappe.db.sql_ddl(f"drop sequence if exists {sequence_name}")
		last_name = frappe.db.get_all(doctype, fields=["max(name) as last"])[0].last
		start_value = (last_name or 0) + 1
		print(f"Creating sequence for {doctype} starting at {start_value}")
		frappe.db.create_sequence(
			doctype, start_value=start_value, check_not_exists=True, cache=frappe.db.SEQUENCE_CACHE
		)


def rename_doctype_links():
	doctypes_with_links = {
		"GP Comment": "reference_doctype",
		"GP Activity": "reference_doctype",
		"GP Member": "parenttype",
		"GP Reaction": "parenttype",
	}
	doctype_values = list(doctypes.keys())
	for doctype in doctypes_with_links:
		fieldname = doctypes_with_links[doctype]
		if frappe.db.exists(doctype, {fieldname: ("in", doctype_values)}):
			print(f"Updating {fieldname} in {doctype}")
			for dt in doctypes:
				old = dt
				new = doctypes[dt]
				frappe.db.set_value(
					doctype, dn={fieldname: old}, field={fieldname: new}, update_modified=False
				)
