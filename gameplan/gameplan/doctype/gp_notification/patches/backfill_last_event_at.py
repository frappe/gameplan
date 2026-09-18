import frappe


def execute():
	# Rows written before `last_event_at` existed each stand for one event that happened
	# when the row was created. Merged rows (`event_count` > 1) only start after this patch.
	notification = frappe.qb.DocType("GP Notification")
	(
		frappe.qb.update(notification)
		.set(notification.last_event_at, notification.creation)
		.set(notification.event_count, 1)
		.where(notification.last_event_at.isnull())
	).run()
