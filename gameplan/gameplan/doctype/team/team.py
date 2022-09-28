# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from gameplan.gemoji import get_random_gemoji
from gameplan.mixins.manage_members import ManageMembersMixin


class Team(ManageMembersMixin, Document):
	on_delete_cascade = ["Team Project"]
	on_delete_set_null = ["Team Notification"]

	def as_dict(self, *args, **kwargs) -> dict:
		d = super().as_dict(*args, **kwargs)
		for member in d.members:
			if member.user:
				full_name, user_image = frappe.db.get_value(
					"User", member.user, ["full_name", "user_image"]
				)
				member.full_name = full_name
				member.user_image = user_image
		return d

	def before_insert(self):
		if not self.name:
			slug = frappe.scrub(self.title).replace("_", "-")
			self.name = append_number_if_name_exists("Team", slug)

		if not self.icon:
			self.icon = get_random_gemoji().emoji

		if not self.readme:
			self.readme = f"""
			<h3>Welcome to the {self.title} team page!</h3>
			<p>You can add a brief introduction about the team, important links, resources, and other important information here.</p>
		"""

		self.append(
			"members",
			{
				"email": frappe.session.user,
				"user": frappe.session.user,
				"status": "Accepted",
				"role": "Owner",
			},
		)

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
			{
				"email": email,
				"status": "Invited",
				"role": "Member",
				"key": frappe.utils.generate_hash(length=8),
			},
		)
		self.save()
		frappe.sendmail(
			recipients=email,
			subject=f"You have been invited to join {self.title}",
			template="team_invitation",
			args={
				"title": f"Team: {self.title}",
				"invite_link": self.get_invitation_link(member),
			},
			now=True,
		)

	def get_invitation_link(self, member):
		return frappe.utils.get_url(
			f"/api/method/gameplan.api.accept_invitation?key={member.key}"
		)