# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GPInvitation(Document):
	def before_insert(self):
		frappe.utils.validate_email_address(self.email, True)
		if self.role == "Gameplan Guest" and not (self.teams or self.projects):
			frappe.throw("Project is required to invite as Guest")

		if self.role != "Gameplan Guest":
			self.teams = None
			self.projects = None

		self.key = frappe.generate_hash(length=12)
		self.invited_by = frappe.session.user
		self.status = "Pending"

	def after_insert(self):
		# grant_access() accepts the invitation itself, so the key would be dead on
		# arrival and the mail would ask for a step the invitee has already skipped.
		if self.flags.skip_invite_email:
			return
		self.invite_via_email()

	def invite_via_email(self):
		invite_link = frappe.utils.get_url(f"/api/method/gameplan.api.accept_invitation?key={self.key}")
		if frappe.local.dev_server:
			print(f"Invite link for {self.email}: {invite_link}")
			return

		title = "Gameplan"
		template = "gameplan_invitation"

		frappe.sendmail(
			recipients=self.email,
			subject=f"You have been invited to join {title}",
			template=template,
			args={"title": title, "invite_link": invite_link},
			now=True,
		)
		self.db_set("email_sent_at", frappe.utils.now())

	def notify_access_granted(self):
		"""Tell someone their existing account can now open Gameplan.

		No key and no link to accept: `grant_access` already did that. They sign in the
		way they always have.
		"""
		app_link = frappe.utils.get_url("/g")
		if frappe.local.dev_server:
			print(f"Access granted to {self.email}: {app_link}")
			return

		frappe.sendmail(
			recipients=self.email,
			subject="You now have access to Gameplan",
			template="gameplan_access_granted",
			args={"app_link": app_link},
			now=True,
		)
		self.db_set("email_sent_at", frappe.utils.now())

	def accept(self):
		if self.status == "Expired":
			frappe.throw("Invalid or expired key")

		user = self.create_user_if_not_exists()
		user.append_roles(self.role)
		user.save(ignore_permissions=True)
		self.create_guest_access(user)

		self.status = "Accepted"
		self.accepted_at = frappe.utils.now()
		self.save(ignore_permissions=True)

	def get_password_link(self):
		return password_link(frappe.get_doc("User", self.email))

	def create_guest_access(self, user):
		if self.role == "Gameplan Guest":
			teams = frappe.parse_json(self.teams) if self.teams else []
			for team in teams:
				guest_access = frappe.get_doc(doctype="GP Guest Access")
				guest_access.user = user.name
				guest_access.team = team
				guest_access.save(ignore_permissions=True)

			projects = frappe.parse_json(self.projects) if self.projects else []
			for project in projects:
				guest_access = frappe.get_doc(doctype="GP Guest Access")
				guest_access.user = user.name
				guest_access.project = project
				guest_access.save(ignore_permissions=True)

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


def grant_access(email, role, projects=None):
	"""Give an account that already exists its role now, with no email round trip.

	The invitation row is still written and then accepted here, for two reasons. It
	keeps `accept()` the single definition of what getting access means, including the
	`GP Guest Access` rows a guest needs, so the two paths cannot drift. And it leaves
	the same audit trail as any other invitation: who granted it, and when.
	"""
	invitation = frappe.get_doc(doctype="GP Invitation", email=email, role=role, projects=projects)
	invitation.flags.skip_invite_email = True
	invitation.insert(ignore_permissions=True)
	invitation.accept()
	invitation.notify_access_granted()
	return invitation


def expire_invitations():
	"""expire invitations after 3 days"""
	from frappe.utils import add_days, now

	days = 3
	invitations_to_expire = frappe.db.get_all(
		"GP Invitation",
		filters={"status": "Pending", "creation": ["<", add_days(now(), -days)]},
	)
	for invitation in invitations_to_expire:
		invitation = frappe.get_doc("GP Invitation", invitation.name)
		invitation.status = "Expired"
		invitation.save(ignore_permissions=True)


def password_link(user, password_expired=False):
	from frappe.utils import now_datetime, sha256_hash

	key = frappe.generate_hash()
	hashed_key = sha256_hash(key)
	user.reset_password_key = hashed_key
	user.last_reset_password_key_generated_on = now_datetime()
	user.save(ignore_permissions=True)
	frappe.db.commit()
	url = "/update-password?key=" + key
	if password_expired:
		url = "/update-password?key=" + key + "&password_expired=true"

	return url
