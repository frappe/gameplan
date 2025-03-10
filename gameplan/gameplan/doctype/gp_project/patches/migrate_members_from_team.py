# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors

import frappe


def execute():
	private_projects = frappe.db.get_all("GP Project", filters={"is_private": 1}, fields=["name", "team"])

	for p in private_projects:
		if not p.team:
			continue

		team = frappe.get_cached_doc("GP Team", p.team)
		project = frappe.get_doc("GP Project", p.name)

		for member in team.members:
			project.add_member(member.user)
