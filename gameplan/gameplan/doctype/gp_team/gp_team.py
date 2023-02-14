# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
import gameplan
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from gameplan.gemoji import get_random_gemoji
from gameplan.mixins.archivable import Archivable
from pypika.terms import ExistsCriterion

class GPTeam(Archivable, Document):
	on_delete_cascade = ["GP Project"]
	on_delete_set_null = ["GP Notification"]

	def as_dict(self, *args, **kwargs) -> dict:
		members = [m.user for m in self.members]
		if self.is_private and frappe.session.user not in members:
			frappe.throw("Not permitted", frappe.PermissionError)

		d = super().as_dict(*args, **kwargs)
		return d

	@staticmethod
	def get_list_query(query):
		Team = frappe.qb.DocType('GP Team')
		Member = frappe.qb.DocType('GP Member')
		member_exists = (
			frappe.qb.from_(Member)
				.select(Member.name)
				.where(Member.parenttype == 'GP Team')
				.where(Member.parent == Team.name)
				.where(Member.user == frappe.session.user)
		)
		query = query.where(
			(Team.is_private == 0) | ((Team.is_private == 1) & ExistsCriterion(member_exists))
		)
		is_guest = gameplan.is_guest()
		if is_guest:
			Team = frappe.qb.DocType('GP Team')
			GuestAccess = frappe.qb.DocType('GP Guest Access')
			team_list = GuestAccess.select(GuestAccess.team).where(GuestAccess.user == frappe.session.user)
			query = query.where(Team.name.isin(team_list))
		return query

	def before_insert(self):
		if not self.name:
			slug = frappe.scrub(self.title).replace("_", "-")
			self.name = append_number_if_name_exists("GP Team", slug)

		if not self.icon:
			self.icon = get_random_gemoji().emoji

		if not self.readme:
			self.readme = f"""
			<h3>Welcome to the {self.title} team page!</h3>
			<p>You can add a brief introduction about the team, important links, resources, and other important information here.</p>
		"""

		self.add_member(frappe.session.user)

	def add_member(self, email):
		if email not in [member.user for member in self.members]:
			self.append("members", {
				"email": email,
				"user": email,
				"status": "Accepted"
			})

	@frappe.whitelist()
	def add_members(self, users):
		for user in users:
			self.add_member(user)
		self.save()

	@frappe.whitelist()
	def remove_member(self, user):
		for member in self.members:
			if member.user == user:
				self.remove(member)
				self.save()
				break
