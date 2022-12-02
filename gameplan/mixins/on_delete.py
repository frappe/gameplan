# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def on_trash(doc, method):
	to_delete = getattr(doc, "on_delete_cascade", [])
	for doctype in to_delete:
		for record in get_linked_records(doc.doctype, doc.name, doctype):
			frappe.delete_doc(doctype, record.name)

	to_set_null = getattr(doc, "on_delete_set_null", [])
	for doctype in to_set_null:
		linked_records = get_linked_records(doc.doctype, doc.name, doctype)
		for record in linked_records:
			if record.fieldtype == 'Link':
				frappe.db.set_value(doctype, record.name, record.fieldname, None)
			elif record.fieldtype == 'Dynamic Link':
				frappe.db.set_value(doctype, record.name, {
					record.fieldname: None,
					record.doctype_fieldname: None
				})


def delete_linked_records(doctype, name, linked_doctypes):
	for linked_doctype in linked_doctypes:
		for record in get_linked_records(doctype, name, linked_doctype):
			frappe.delete_doc(linked_doctype, record.name)


def get_linked_records(link_doctype, link_name, doctype):
	records = []
	meta = frappe.get_meta(doctype)
	link_fields = meta.get("fields", {"fieldtype": "Link", "options": link_doctype})
	for field in link_fields:
		result = frappe.db.get_all(doctype, {field.fieldname: link_name})
		for r in result:
			r.fieldname = field.fieldname
			r.fieldtype = 'Link'
		records += result

	dynamic_link_fields = meta.get("fields", {"fieldtype": "Dynamic Link"})
	for field in dynamic_link_fields:
		result = frappe.db.get_all(doctype, {field.options: link_doctype, field.fieldname: link_name})
		for r in result:
			r.fieldname = field.fieldname
			r.doctype_fieldname = field.options
			r.fieldtype = 'Dynamic Link'
		records += result

	return records
