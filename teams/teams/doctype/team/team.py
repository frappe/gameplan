# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from teams.unsplash import get_random as get_random_image


class Team(Document):
	def as_dict(self, *args, **kwargs) -> dict:
		d = super().as_dict(*args, **kwargs)
		for member in d.members:
			if member.user:
				member.full_name = frappe.db.get_value("User", member.user, "full_name")
		return d

	def before_insert(self):
		if not self.name:
			slug = frappe.scrub(self.title)
			self.name = append_number_if_name_exists("Team", slug)

		if not self.description:
			self.description = f"""
			<strong>Welcome to the {self.title} team page!</strong>
			<p>You can add a brief introduction about the team, important links, resources, and other important information here.</p>
		"""

		if not self.cover_image:
			image = get_random_image({"query": self.title, "orientation": "landscape"})
			self.cover_image = image["urls"]["raw"]

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
			args={"team": self, "invite_link": self.get_invitation_link(member)},
			now=True,
		)

	def accept_invitation(self, key):
		for row in self.members:
			if row.key == key:
				if not frappe.db.exists("User", row.email):
					user = frappe.get_doc(
						doctype="User",
						user_type="Website User",
						email=row.email,
						send_welcome_email=0,
						first_name=row.email.split("@")[0],
					).insert(ignore_permissions=True)
					user.add_roles("Team Project User", "System Manager")
				else:
					user = frappe.get_doc("User", row.email)
				row.user = user.name
				row.status = "Accepted"
				self.save()
				return user

	def get_invitation_link(self, member):
		return frappe.utils.get_url(
			f"/api/method/teams.api.accept_invitation?key={member.key}"
		)