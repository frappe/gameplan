import frappe

BATCH_SIZE = 500


def execute():
	fill("discussion", "GP Discussion", "project")
	fill("project", "GP Project", "team")


def fill(source_field: str, source_doctype: str, target_field: str):
	"""Copy `target_field` onto the notifications that have a `source_field` but no value.

	Walked in batches of BATCH_SIZE by name, which is an autoincrement: the table can hold
	far more rows than one statement should carry. The cursor moves past every row it has
	read, not only the ones it filled, so a row whose source is gone cannot be fetched
	again forever.
	"""
	Notification = frappe.qb.DocType("GP Notification")
	after = 0
	while True:
		rows = frappe.get_all(
			"GP Notification",
			filters={
				target_field: ["is", "not set"],
				source_field: ["is", "set"],
				"name": [">", after],
			},
			fields=["name", source_field],
			order_by="name asc",
			limit=BATCH_SIZE,
		)
		if not rows:
			return
		after = rows[-1].name

		values = _source_values(source_doctype, target_field, source_field, rows)
		batches = {}
		for row in rows:
			value = values.get(str(row[source_field]))
			if value:
				batches.setdefault(value, []).append(row.name)

		for value, names in batches.items():
			(
				frappe.qb.update(Notification)
				.set(Notification[target_field], value)
				.where(Notification.name.isin(names))
			).run()


def _source_values(source_doctype: str, target_field: str, source_field: str, rows: list) -> dict:
	sources = list({str(row[source_field]) for row in rows})
	return {
		str(name): value
		for name, value in frappe.get_all(
			source_doctype,
			filters={"name": ["in", sources]},
			fields=["name", target_field],
			as_list=True,
		)
	}
