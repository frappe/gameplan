# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt


import frappe


def reset_space_for_user(project, user: str):
	project = str(project)
	frappe.db.delete("GP Space Subscription", {"user": user, "project": project})

	Subscription = frappe.qb.DocType("GP Discussion Subscription")
	Discussion = frappe.qb.DocType("GP Discussion")
	in_space = frappe.qb.from_(Discussion).select(Discussion.name).where(Discussion.project == project)
	(
		frappe.qb.from_(Subscription)
		.delete()
		.where(Subscription.user == user)
		.where(Subscription.discussion.isin(in_space))
	).run()
