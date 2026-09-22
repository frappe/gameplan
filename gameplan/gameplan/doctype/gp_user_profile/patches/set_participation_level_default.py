import frappe


def execute():
	profile = frappe.qb.DocType("GP User Profile")
	(
		frappe.qb.update(profile)
		.set(profile.participation_level, "Watch")
		.where(profile.participation_level.isnull() | (profile.participation_level == ""))
	).run()
