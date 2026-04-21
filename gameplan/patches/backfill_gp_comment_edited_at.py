import frappe


def execute():
	versions = frappe.qb.get_query(
		"Version",
		fields=["docname", "creation"],
		filters={
			"ref_doctype": "GP Comment",
			"data": ["like", '%["content",%'],
		},
		order_by="creation asc",
	).run(as_dict=True)

	latest_revisions = {}
	for version in versions:
		latest_revisions[version.docname] = version.creation

	for comment, edited_at in latest_revisions.items():
		if frappe.db.exists("GP Comment", comment):
			frappe.db.set_value("GP Comment", comment, "edited_at", edited_at, update_modified=False)
