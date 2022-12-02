# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class GPInvitation(Document):
	def before_insert(self):
		frappe.utils.validate_email_address(self.email, True)
		if self.type == 'Team Access' and not self.team:
			frappe.throw('Team is required')
		elif self.type == 'Project Guest Access' and not self.project:
			frappe.throw('Project is required')

		self.key = frappe.generate_hash(length=12)
		self.invited_by = frappe.session.user
		self.status = 'Invited'

	def after_insert(self):
		self.invite_via_email()

	def invite_via_email(self):
		invite_link = frappe.utils.get_url(
			f"/api/method/gameplan.api.accept_invitation?key={self.key}"
		)
		if frappe.local.dev_server:
			print(f"Invite link for {self.email}: {invite_link}")

		title, template = '', ''
		if self.type == 'Team Member':
			title = f'Team: {self.team}'
			template = 'team_invitation'
		elif self.type == 'Project Guest Member':
			title = f'Project: {self.project}'
			template = 'project_guest_invitation'

		frappe.sendmail(
			recipients=self.email,
			subject=f"You have been invited to join {title}",
			template=template,
			args={"title": title, "invite_link": invite_link},
			now=True,
		)
		self.db_set('email_sent_at', frappe.utils.now())

	def accept(self):
		if self.status == 'Expired':
			frappe.throw('Invalid or expired key')

		user = self.create_user_if_not_exists()
		if self.type == 'Team Access':
			user.append_roles('Teams User')
			user.save(ignore_permissions=True)
			# add user to team
			team = frappe.get_doc("Team", self.team)
			team.add_member(user.name)
			team.save(ignore_permissions=True)
		elif self.type == 'Project Guest Access':
			user.append_roles('Gameplan Guest')
			user.save(ignore_permissions=True)
			# create guest access
			guest_access = frappe.get_doc(doctype='GP Guest Access')
			guest_access.user = user.name
			guest_access.project = self.project
			guest_access.save(ignore_permissions=True)

		self.status = 'Accepted'
		self.accepted_at = frappe.utils.now()
		self.save(ignore_permissions=True)

	def create_user_if_not_exists(self):
		if not frappe.db.exists("User", self.email):
			first_name = self.email.split("@")[0].title()
			user = frappe.get_doc(
				doctype="User",
				user_type="Website User",
				email=self.email,
				send_welcome_email=0,
				first_name=first_name,
			).insert(ignore_permissions=True)
		else:
			user = frappe.get_doc("User", self.email)
		return user
