import frappe


def execute():
	# Same reason as set_notification_defaults: rows that predate the fields get the
	# starting values written out, so "never touched" reads the same for everyone.
	profile = frappe.qb.DocType("GP User Profile")
	(
		frappe.qb.update(profile)
		.set(profile.receive_notifications, 1)
		.where(profile.receive_notifications.isnull())
	).run()
	(
		frappe.qb.update(profile)
		.set(profile.active_hours_enabled, 0)
		.where(profile.active_hours_enabled.isnull())
	).run()
	(
		frappe.qb.update(profile)
		.set(profile.active_hours_days, frappe.as_json(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]))
		.where(profile.active_hours_days.isnull() | (profile.active_hours_days == ""))
	).run()
