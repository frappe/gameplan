# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.base_document import get_controller

@frappe.whitelist()
def get_list(doctype, **kwargs):
	controller = get_controller(doctype)
	if hasattr(controller, "get_list_query"):
		check_permissions(doctype, kwargs.get("parent"))
		query = frappe.qb.get_query(
			table=doctype,
			fields=kwargs.get("fields"),
			filters=kwargs.get("filters"),
			order_by=kwargs.get("order_by"),
			offset=kwargs.get("start"),
			limit=kwargs.get("limit", 20),
			group_by=kwargs.get("group_by"),
		)
		return_value = controller.get_list_query(query)
		if return_value is not None:
			query = return_value
		return query.run(as_dict=True, debug=kwargs.get("debug"))
	return frappe.client.get_list(
		doctype,
		fields=kwargs.get("fields"),
		filters=kwargs.get("filters"),
		order_by=kwargs.get("order_by"),
		limit_start=kwargs.get("limit_start"),
		limit_page_length=kwargs.get("limit_page_length",20),
		parent=kwargs.get("parent"),
		debug=kwargs.get("debug", False),
		as_dict=kwargs.get("as_dict", True),
		or_filters=kwargs.get("or_filters"),
	)

def check_permissions(doctype, parent):
	user = frappe.session.user
	if (
		not frappe.has_permission(doctype, "select", user=user, parent_doctype=parent)
		and not frappe.has_permission(doctype, "read", user=user, parent_doctype=parent)
	):
		frappe.throw(f'Insufficient Permission for {doctype}', frappe.PermissionError)

@frappe.whitelist()
def batch(requests):
	from frappe.handler import handle
	from frappe.app import handle_exception
	requests = frappe.parse_json(requests)
	responses = []

	for i, request_params in enumerate(requests):
		savepoint = f'batch_request_{i}'
		try:
			frappe.db.savepoint(savepoint)
			frappe.form_dict.update(request_params)
			response = handle()
			frappe.db.release_savepoint(savepoint)
		except Exception as e:
			frappe.db.rollback(save_point=savepoint)
			response = handle_exception(e)

		responses.append(response)

	return [r.json for r in responses]
