import frappe


def execute():
	frappe.db.multisql(
		{
			"mariadb": """
				UPDATE `tabGP Review` AS review
				JOIN (
					SELECT `review`, COUNT(*) AS `report_count`, MAX(`creation`) AS `last_reported_at`
					FROM `tabGP Report`
					GROUP BY `review`
				) AS stats ON stats.`review` = review.`name`
				SET review.`report_count` = stats.`report_count`,
					review.`last_reported_at` = stats.`last_reported_at`
			""",
			"sqlite": """
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
				WHERE EXISTS (
					SELECT 1 FROM `tabGP Report`
					WHERE `tabGP Report`.`review` = `tabGP Review`.`name`
				)
			""",
		}
	)
