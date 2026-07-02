import frappe


def execute():
	Project = frappe.qb.DocType("GP Project")
	(frappe.qb.update(Project).set(Project.visibility, "Private").where(Project.is_private == 1)).run()
	(
		frappe.qb.update(Project)
		.set(Project.visibility, "Members")
		.where((Project.is_private == 0) & ((Project.visibility.isnull()) | (Project.visibility == "")))
	).run()
