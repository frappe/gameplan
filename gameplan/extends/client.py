# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe
from frappe.database.query import RawCriterion
from frappe.model.base_document import get_controller
from frappe.utils import cint

import gameplan
from gameplan.public_payload import (
	check_public_filters,
	check_public_order_by,
	public_doctypes,
	public_list_fields,
	public_rows,
	refuse,
)


@frappe.whitelist(allow_guest=True)
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
	anonymous = gameplan.is_anonymous()
	if anonymous:
		start = max(cint(start), 0)
		limit = max(1, min(cint(limit) or 20, 1000))
		# Nobody is signed in: only public columns, filtered and sorted on public columns,
		# and the rows cleaned before they leave (see gameplan.public_payload).
		if parent or group_by:
			refuse("Not allowed without signing in")
		fields = public_list_fields(doctype, fields)
		check_public_filters(doctype, filters)
		check_public_order_by(doctype, order_by)
		debug = False
	# The query must always receive the doctype's row scope. For signed-in callers Frappe
	# applies it; the anonymous public path applies the same hooks below because Frappe's
	# generic Guest-role gate runs before it can reach them.
	query = frappe.qb.get_query(
		table=doctype,
		fields=fields,
		filters=filters,
		order_by=order_by,
		offset=start,
		limit=limit,
		group_by=group_by,
		# Frappe's query builder repeats the generic Guest role check before it applies
		# the query-condition hooks. The public wrapper has already fixed the doctype and
		# validated the request, so apply those hooks explicitly below instead.
		ignore_permissions=anonymous,
		parent_doctype=parent,
	)
	if anonymous:
		query = apply_anonymous_permission_filters(doctype, query)
	query = apply_custom_filters(doctype, query)
	rows = query.run(as_dict=True, debug=debug)
	return public_rows(doctype, rows) if anonymous else rows


def check_permissions(doctype, parent):
	user = frappe.session.user
	# Public-list endpoints accept a fixed public-doctype allowlist, validate their query
	# inputs, apply the anonymous row scope, and clean each returned row. The generic
	# doctype check runs before those safeguards and rejects their Guest requests.
	if gameplan.is_anonymous(user) and doctype in public_doctypes():
		return
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


def apply_anonymous_permission_filters(doctype, query):
	"""Apply the row scopes the query builder skips for an anonymous public list."""
	for method in frappe.get_hooks("permission_query_conditions", {}).get(doctype, []):
		condition = frappe.call(frappe.get_attr(method), frappe.session.user, doctype=doctype)
		if condition:
			query = query.where(RawCriterion(f"({condition})") if isinstance(condition, str) else condition)
	return query
