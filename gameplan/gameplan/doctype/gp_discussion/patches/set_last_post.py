# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
import frappe


def execute():
	frappe.db.sql("""
		UPDATE `tabGP Discussion` d
		INNER JOIN (
			SELECT discussion, creation, owner, name, type,
				ROW_NUMBER() OVER (PARTITION BY discussion ORDER BY creation DESC) as rn
			FROM (
				SELECT reference_name as discussion, creation, owner, name, 'GP Comment' as type
				FROM `tabGP Comment`
				WHERE reference_doctype = 'GP Discussion'
				UNION ALL
				SELECT discussion, creation, owner, name, 'GP Poll' as type
				FROM `tabGP Poll`
			) combined_posts
		) p ON d.name = p.discussion AND p.rn = 1
		SET
			d.last_post_type = p.type,
			d.last_post = p.name,
			d.last_post_at = p.creation,
			d.last_post_by = p.owner
	""")
