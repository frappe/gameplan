import frappe

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

DEFAULTS = {
	"notification_level": "Mentions only",
	"notification_channel": "In-app",
	"participation_level": "Watch",
	"active_hours_days": frappe.as_json(WEEKDAYS),
}


def execute():
	profile = frappe.qb.DocType("GP User Profile")
	for field, value in DEFAULTS.items():
		column = profile[field]
		(frappe.qb.update(profile).set(column, value).where(column.isnull() | (column == ""))).run()
