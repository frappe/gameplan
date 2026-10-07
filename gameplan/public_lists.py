# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""The lists the public view of the app reads, for people who are not signed in.

frappe's own list route (`/api/v2/document/<doctype>`) is closed to them for Gameplan
doctypes (see `gameplan.public_access.refuse_generic_routes_for_anonymous`), because its
rows cannot be cleaned on the way out. These go through `gameplan.extends.client.get_list`
instead, which takes only public columns from an anonymous caller and cleans every row.

One endpoint per doctype rather than one taking a `doctype` argument: frappe-ui's useList
cannot pass the doctype to a custom URL, and a short fixed list is also the allowlist of
what the public view may list at all.
"""

import frappe
from frappe.utils import cint

from gameplan.extends.client import get_list

# Enough for every comment on a long thread; not a way to dump a table.
MAX_ROWS = 1000


def public_list(doctype, fields, filters, order_by, start, limit):
	limit = cint(limit) or 20
	limit = max(1, min(limit, MAX_ROWS))
	rows = get_list(
		doctype=doctype,
		fields=frappe.parse_json(fields),
		filters=frappe.parse_json(filters),
		order_by=order_by,
		start=max(cint(start), 0),
		limit=limit,
	)
	frappe.response["has_next_page"] = len(rows) == limit
	return rows


@frappe.whitelist(allow_guest=True, methods=["GET"])
def communities(fields=None, filters=None, order_by=None, start=0, limit=20):
	return public_list("GP Team", fields, filters, order_by, start, limit)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def spaces(fields=None, filters=None, order_by=None, start=0, limit=20):
	return public_list("GP Project", fields, filters, order_by, start, limit)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def comments(fields=None, filters=None, order_by=None, start=0, limit=20):
	return public_list("GP Comment", fields, filters, order_by, start, limit)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def polls(fields=None, filters=None, order_by=None, start=0, limit=20):
	return public_list("GP Poll", fields, filters, order_by, start, limit)
