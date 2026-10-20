# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import sha256_hash

import gameplan
from gameplan.gameplan.doctype.gp_team.gp_team import get_public_team_names


class GPInvitation(Document):
	def before_insert(self):
		frappe.utils.validate_email_address(self.email, True)
		if self.role == "Gameplan Guest" and not (self.teams or self.projects):
			frappe.throw("Project is required to invite as Guest")

		if self.role != "Gameplan Guest":
			self.teams = None
			self.projects = None

		if self.role == "Gameplan Admin" and not gameplan.is_admin():
			frappe.throw("Only admins can invite admins", frappe.PermissionError)

		# Only the invite link carries the key. The row keeps its hash, so reading the
		# invitation does not give anyone a link that works.
		self.flags.invite_key = frappe.generate_hash(length=32)
		self.key = sha256_hash(self.flags.invite_key)
		self.invited_by = frappe.session.user
		self.status = "Pending"

	def after_insert(self):
		# grant_access() accepts the invitation itself, so the key would be dead on
		# arrival and the mail would ask for a step the invitee has already skipped.
		if self.flags.skip_invite_email:
			return
		self.invite_via_email()

	def invite_via_email(self):
		invite_link = frappe.utils.get_url(
			f"/api/method/gameplan.api.accept_invitation?key={self.flags.invite_key}"
		)
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
		"""Grant the invitation's role and access, and record whether it created the account."""
		# A key works once: accepting it, or letting it expire, ends it.
		if self.status != "Pending":
			frappe.throw("Invalid or expired key")

		created_account = not frappe.db.exists("User", self.email)
		user = self.create_user() if created_account else frappe.get_doc("User", self.email)
		user.append_roles(self.role)
		user.save(ignore_permissions=True)
		self.create_guest_access(user)
		self.join_public_communities(user)

		self.status = "Accepted"
		self.accepted_at = frappe.utils.now()
		self.created_account = created_account
		self.save(ignore_permissions=True)

	def created_account_awaits_password(self):
		"""Whether accepting this invitation created its account, and no password has been set on it yet."""
		if not self.created_account:
			return False
		return not frappe.db.get_value("User", self.email, "last_password_reset_date")

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

	def join_public_communities(self, user):
		"""Put a new member in every public community, so the app is not empty on day one.

		Membership is not what grants access here: a public community is already readable
		by everyone (see `team_access_criterion`). It is what the sidebar lists, so without
		this a new account signs in to an empty shell and has to go and find the
		communities before anything appears.

		Guests are skipped. Their reach is exactly the `GP Guest Access` rows
		`create_guest_access` just wrote, and joining them to everything would undo that.
		"""
		if self.role == "Gameplan Guest":
			return

		for team_name in get_public_team_names():
			team = frappe.get_doc("GP Team", team_name)
			if team.get_member(user.name):
				continue
			team.add_member(user.name)
			# Saving the community re-validates every row already in `members`, so one row
			# left pointing at a deleted account would stop anyone new from joining. The row
			# being added here is safe by construction: `user` is a User document that was
			# just loaded or created.
			team.flags.ignore_links = True
			team.save(ignore_permissions=True)

	def create_user(self):
		return frappe.get_doc(
			doctype="User",
			user_type="Website User",
			email=self.email,
			send_welcome_email=0,
			first_name=self.email.split("@")[0].title(),
		).insert(ignore_permissions=True)


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


def get_invitation(key):
	"""The invitation an invite link's key belongs to, or None."""
	if not key:
		return None
	name = frappe.db.get_value("GP Invitation", {"key": sha256_hash(key)})
	return frappe.get_doc("GP Invitation", name) if name else None


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
	url = "/update-password?key=" + key
	if password_expired:
		url = "/update-password?key=" + key + "&password_expired=true"

	return url
