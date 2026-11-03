import frappe


def execute():
	frappe.db.sql(
		"""
		UPDATE `tabGP Review`
		SET
			`report_count` = (
				SELECT COUNT(*) FROM `tabGP Report`
				WHERE `tabGP Report`.`review` = `tabGP Review`.`name`
			),
			`last_reported_at` = (
				SELECT MAX(`creation`) FROM `tabGP Report`
				WHERE `tabGP Report`.`review` = `tabGP Review`.`name`
			)
		"""
	)
