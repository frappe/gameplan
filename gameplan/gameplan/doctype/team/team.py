# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from gameplan.gemoji import get_random_gemoji
from gameplan.mixins.archivable import Archivable
from gameplan.mixins.manage_members import ManageMembersMixin


class Team(ManageMembersMixin, Archivable, Document):
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

	@staticmethod
	def get_list_query(query):
		is_guest = 'Gameplan Guest' in frappe.get_roles()
		if is_guest:
			Team = frappe.qb.DocType('Team')
			GuestAccess = frappe.qb.DocType('GP Guest Access')
			team_list = GuestAccess.select(GuestAccess.team).where(GuestAccess.user == frappe.session.user)
			query = query.where(Team.name.isin(team_list))
		return query

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

	def add_member(self, email):
		if email not in [member.user for member in self.members]:
			self.append("members", {
				"email": email,
				"user": email,
				"status": "Accepted"
			})

	@frappe.whitelist()
	def invite_members(self, emails):
		for email in emails:
			frappe.utils.validate_email_address(email, True)

		existing_members = [m.user for m in self.members]
		for email in emails:
			if email not in existing_members:
				frappe.get_doc(
					doctype='GP Invitation',
					email=email,
					type='Team Access',
					team=self.name,
				).insert(ignore_permissions=True)
