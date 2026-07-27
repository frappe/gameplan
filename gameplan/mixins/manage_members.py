# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe


class ManageMembersMixin:
	def accept_invitation(self, key):
		for row in self.members:
			if row.key == key:
				if not frappe.db.exists("User", row.email):
					first_name = row.email.split("@")[0].title()
					user = frappe.get_doc(
						doctype="User",
						user_type="Website User",
						email=row.email,
						send_welcome_email=0,
						first_name=first_name,
					).insert(ignore_permissions=True)
					user.add_roles("Gameplan Member")
				else:
					user = frappe.get_doc("User", row.email)
				row.user = user.name
				row.status = "Accepted"
				self.save()
				return user

	@frappe.whitelist(methods=["POST"])
	def remove_member(self, user):
		for member in self.members:
			if member.user == user:
				self.remove(member)
				self.save()
