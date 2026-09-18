import frappe


def execute():
	profile = frappe.qb.DocType("GP User Profile")
	(
		frappe.qb.update(profile)
		.set(profile.notification_channel, "In-app")
		.where(profile.notification_channel.isnull() | (profile.notification_channel == ""))
	).run()
