import frappe


def execute():
	"""Preserve legacy indefinite Community bans in indexed current-state records."""
	from gameplan.moderation_logs import latest_logs
	from gameplan.restrictions import restriction_name

	Log = frappe.qb.DocType("GP Moderation Log")
	after = ""
	while True:
		rows = (
			latest_logs(["community", "user"], ["Ban", "Unban"])
			.select(Log.name, Log.user, Log.community, Log.reason)
			.where(
				(Log.action == "Ban")
				& (Log.name > after)
				& Log.community.isnotnull()
				& (Log.community != "")
				& Log.user.isnotnull()
			)
			.orderby(Log.name)
			.limit(500)
			.run(as_dict=True)
		)
		if not rows:
			break
		for row in rows:
			name = restriction_name(row.user, row.community)
			if not frappe.db.exists("GP User Restriction", name):
				frappe.get_doc(
					doctype="GP User Restriction",
					name=name,
					user=row.user,
					community=row.community,
					active=1,
					reason=row.reason,
				).db_insert()
		after = rows[-1].name
