import frappe


def execute():
	notification = frappe.qb.DocType("GP Notification")
	(
		frappe.qb.update(notification)
		.set(notification.last_event_at, notification.creation)
		.set(notification.event_count, 1)
		.where(notification.last_event_at.isnull())
	).run()
