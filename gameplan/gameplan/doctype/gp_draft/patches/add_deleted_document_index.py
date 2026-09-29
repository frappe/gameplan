# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors

from ..gp_draft import add_indexes


def execute():
	"""Index Deleted Document by (deleted_doctype, deleted_name) for GP Draft naming"""
	add_indexes()
