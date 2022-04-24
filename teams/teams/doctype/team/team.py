# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from teams.gemoji import get_random_gemoji
from teams.mixins.manage_members import ManageMembersMixin
from teams.unsplash import get_random as get_random_image
from teams.utils import validate_url


class Team(ManageMembersMixin, Document):
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
			slug = frappe.scrub(self.title)
			self.name = append_number_if_name_exists("Team", slug)

		if not self.icon:
			self.icon = get_random_gemoji().emoji

		if not self.description:
			self.description = f"""
			<strong>Welcome to the {self.title} team page!</strong>
			<p>You can add a brief introduction about the team, important links, resources, and other important information here.</p>
		"""

		if not self.cover_image:
			try:
				image = get_random_image({"query": self.title, "orientation": "landscape"})
				self.cover_image = image["urls"]["raw"]
			except:
				pass

		self.append(
			"members",
			{
				"email": frappe.session.user,
				"user": frappe.session.user,
				"status": "Accepted",
				"role": "Owner",
			},
		)

	def before_save(self):
		for link in self.links:
			if link.is_new():
				valid_url = validate_url(link.url)
				if not valid_url:
					frappe.throw(f'Invalid URL: {link.url}')
				else:
					link.url = valid_url


	def on_trash(self):
		for project in frappe.db.get_all("Team Project", {"team": self.name}):
			frappe.delete_doc("Team Project", project.name)

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
			f"/api/method/teams.api.accept_invitation?key={member.key}"
		)