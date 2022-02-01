# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TeamProject(Document):
	def as_dict(self, *args, **kwargs) -> dict:
		d = super().as_dict(*args, **kwargs)
		d.members = frappe.get_doc("Team", d.team).as_dict()["members"]
		return d
