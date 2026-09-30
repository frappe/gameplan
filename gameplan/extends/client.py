# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe
from frappe.model.base_document import get_controller


@frappe.whitelist()
def get_list(
	doctype=None,
	fields=None,
	filters=None,
	order_by=None,
	start=0,
	limit=20,
	group_by=None,
	parent=None,
	debug=False,
):
	check_permissions(doctype, parent)
	# `frappe.qb.get_query` ignores permissions unless told otherwise, and then every row of
	# the doctype comes back: every private discussion, and every user's drafts and
	# bookmarks. Asking for them applies each doctype's permission_query_conditions, as
	# frappe.get_list and the /api/v2/document list route do.
	query = frappe.qb.get_query(
		table=doctype,
		fields=fields,
		filters=filters,
		order_by=order_by,
		offset=start,
		limit=limit,
		group_by=group_by,
		ignore_permissions=False,
		parent_doctype=parent,
	)
	query = apply_custom_filters(doctype, query)
	return query.run(as_dict=True, debug=debug)


def check_permissions(doctype, parent):
	user = frappe.session.user
	if not frappe.has_permission(
		doctype, "select", user=user, parent_doctype=parent
	) and not frappe.has_permission(doctype, "read", user=user, parent_doctype=parent):
		frappe.throw(f"Insufficient Permission for {doctype}", frappe.PermissionError)


def apply_custom_filters(doctype, query):
	"""Apply custom filters to query"""
	controller = get_controller(doctype)
	if hasattr(controller, "get_list_query"):
		return_value = controller.get_list_query(query)
		if return_value is not None:
			query = return_value

	return query
