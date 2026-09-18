import frappe


def execute():
	# `project` and `team` are fetch_from fields, so rows written since that was added
	# already carry them. Older rows may not, and the inbox's community/space filters
	# read these two columns. Rows whose discussion was deleted (link nulled) are left
	# as they are: there is nothing to derive from.
	#
	# Raw SQL with correlated subqueries: query-builder does not parenthesise a subquery
	# used as a SET value, and SQLite has no join form of UPDATE.
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
