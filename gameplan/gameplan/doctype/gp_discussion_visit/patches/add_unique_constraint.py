# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe

from gameplan.gameplan.doctype.gp_discussion_visit.gp_discussion_visit import after_doctype_insert


def execute():
	delete_duplicates()
	after_doctype_insert()


def delete_duplicates():
	from frappe.query_builder.functions import Count

	DiscussionVisit = frappe.qb.DocType("GP Discussion Visit")
	duplicates = (
		frappe.qb.from_(DiscussionVisit)
		.select(DiscussionVisit.name)
		.groupby(DiscussionVisit.discussion, DiscussionVisit.user)
		.having(Count(DiscussionVisit.name) > 1)
	).run(as_dict=1, pluck="name")

	if duplicates:
		for name in duplicates:
			frappe.delete_doc_if_exists("GP Discussion Visit", name)
