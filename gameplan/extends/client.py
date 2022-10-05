# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.base_document import get_controller


@frappe.whitelist()
def get_list(doctype=None, fields=None, filters=None, order_by=None, start=0, limit=20, parent=None, debug=False):
	query = frappe.qb.engine.get_query(
		table=doctype,
		fields=fields,
		filters=filters,
		order_by=order_by,
		start=start,
		limit=limit,
        parent=parent
	)
	if order_by:
		parts = order_by.split(" ")
		orderby_field = parts[0]
		orderby_direction = parts[1] if len(parts) > 1 else "asc"
		query = query.orderby(orderby_field, order=frappe._dict(value=orderby_direction))

	query = apply_custom_filters(doctype, query)
	return query.run(as_dict=True, debug=debug)

def apply_custom_filters(doctype, query):
	"""Apply custom filters to query"""
	controller = get_controller(doctype)
	if hasattr(controller, "get_list_query"):
		return_value = controller.get_list_query(query)
		if return_value is not None:
			query = return_value

	return query