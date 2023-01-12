# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe


class ManageMembersMixin:
	@frappe.whitelist()
	def invite_members(self, emails):
		existing_members = [d.email for d in self.members]
		for email in emails:
			if not frappe.utils.validate_email_address(email):
				continue

			if email in existing_members:
				continue

			if frappe.db.exists("User", email):
				self.append(
					"members", {"email": email, "user": email, "status": "Accepted"},
				)
			else:
				member = self.append(
					"members",
					{
						"email": email,
						"status": "Invited",
						"role": "Member",
						"key": frappe.generate_hash(length=8),
					},
				)
				self.invite_via_email(member)
		self.save()

	def invite_via_email(self, member):
		invite_link = frappe.utils.get_url(
			f"/api/method/gameplan.api.accept_invitation?key={member.key}"
		)
		title = f"Team: {self.title}" if self.doctype == "GP Team" else f"Project: {self.title}"
		if frappe.local.dev_server:
			print(f"Invite link for {member.email}: {invite_link}")

		frappe.sendmail(
			recipients=member.email,
			subject=f"You have been invited to join {self.title}",
			template="team_invitation",
			args={"title": title, "invite_link": invite_link},
			now=True,
		)

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

	@frappe.whitelist()
	def remove_member(self, user):
		for member in self.members:
			if member.user == user:
				self.remove(member)
				self.save()