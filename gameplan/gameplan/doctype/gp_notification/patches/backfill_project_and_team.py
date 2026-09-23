import frappe


def execute():
	frappe.db.sql("""
		UPDATE `tabGP Notification`
		SET project = (
			SELECT `tabGP Discussion`.project
			FROM `tabGP Discussion`
			WHERE `tabGP Discussion`.name = `tabGP Notification`.discussion
		)
		WHERE project IS NULL AND discussion IS NOT NULL
	""")
	frappe.db.sql("""
		UPDATE `tabGP Notification`
		SET team = (
			SELECT `tabGP Project`.team
			FROM `tabGP Project`
			WHERE `tabGP Project`.name = `tabGP Notification`.project
		)
		WHERE team IS NULL AND project IS NOT NULL
	""")
