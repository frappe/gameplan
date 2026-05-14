from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"User": [
				{
					"fieldname": "weekly_digest",
					"label": "Weekly Digest",
					"fieldtype": "Check",
					"default": "0",
					"insert_after": "thread_notify",
				}
			]
		},
		ignore_validate=True,
	)
