import frappe


def execute():
	profile = frappe.qb.DocType("GP User Profile")
	(
		frappe.qb.update(profile)
		.set(profile.notification_level, "Mentions only")
		.where(profile.notification_level.isnull() | (profile.notification_level == ""))
	).run()
