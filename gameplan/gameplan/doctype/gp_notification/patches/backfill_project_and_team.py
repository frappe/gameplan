import frappe


def execute():
	fill("discussion", "GP Discussion", "project")
	fill("project", "GP Project", "team")


def fill(source_field: str, source_doctype: str, target_field: str):
	rows = frappe.get_all(
		"GP Notification",
		filters={target_field: ["is", "not set"], source_field: ["is", "set"]},
		fields=["name", source_field],
	)
	if not rows:
		return

	sources = list({str(row[source_field]) for row in rows})
	values = {
		str(name): value
		for name, value in frappe.get_all(
			source_doctype,
			filters={"name": ["in", sources]},
			fields=["name", target_field],
			as_list=True,
		)
	}

	batches = {}
	for row in rows:
		value = values.get(str(row[source_field]))
		if value:
			batches.setdefault(value, []).append(row.name)

	Notification = frappe.qb.DocType("GP Notification")
	for value, names in batches.items():
		(
			frappe.qb.update(Notification)
			.set(Notification[target_field], value)
			.where(Notification.name.isin(names))
		).run()
