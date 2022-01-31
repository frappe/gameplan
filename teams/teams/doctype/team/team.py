# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists


class Team(Document):
	def before_insert(self):
		if not self.name:
			slug = frappe.scrub(self.title)
			self.name = append_number_if_name_exists("Team", slug)

	@frappe.whitelist()
	def send_invitation(self, email):
		for row in self.members:
			if row.email == email:
				if row.status == "Invited":
					frappe.throw(f"Invitation already sent to {email}")
				if row.status == "Accepted":
					frappe.throw(f"{email} is already a member of this project")

		member = self.append(
			"members",
			{"email": email, "status": "Invited", "key": frappe.utils.generate_hash(length=8)},
		)
		self.save()
		frappe.sendmail(
			recipients=email,
			subject=f"You have been invited to join {self.title}",
			template="team_invitation",
			args={"team": self, "invite_link": self.get_invitation_link(member)},
			now=True,
		)

	def accept_invitation(self, key):
		for row in self.members:
			if row.key == key:
				user = frappe.get_doc(
					doctype="User",
					user_type="Website User",
					email=row.email,
					send_welcome_email=0,
					first_name=row.email.split("@")[0],
				).insert(ignore_permissions=True)
				row.user = user.name
				row.status = "Accepted"
				self.save()
				return user

	def get_invitation_link(self, member):
		return frappe.utils.get_url(
			f"/api/method/teams.api.accept_invitation?key={member.key}"
		)