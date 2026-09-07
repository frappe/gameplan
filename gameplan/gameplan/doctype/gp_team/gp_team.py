# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import cint
from pypika.terms import ExistsCriterion

import gameplan
from gameplan.mixins.archivable import Archivable
from gameplan.permissions import (
	apply_team_query_filter,
	is_global_admin,
	require_can_manage_community,
)
from gameplan.utils import validate_type


class GPTeam(Archivable, Document):
	on_delete_cascade = ["GP Project"]
	on_delete_set_null = ["GP Notification"]

	def as_dict(self, *args, **kwargs) -> dict:
		"""Hide a private community from everyone but its members and global admins.

		The admin bypass is not cosmetic. `frappe.api.v2.execute_doc_method` serialises the
		document with `as_dict` AFTER running the requested method, so a throw here loses the
		write that already ran: the request ends in a rollback and the admin sees only
		"Not permitted". That silently broke every whitelisted method on a private community
		an admin does not belong to — archive, merge_into_team, add_members, remove_member,
		set_member_admin — even though `can_manage_community` grants all of them.
		"""
		user = frappe.session.user
		if self.is_private and not is_global_admin(user) and user not in [m.user for m in self.members]:
			frappe.throw("Not permitted", frappe.PermissionError)

		d = super().as_dict(*args, **kwargs)
		return d

	@staticmethod
	def get_list_query(query):
		return apply_team_query_filter(query)

	def before_insert(self):
		if not self.name:
			slug = frappe.scrub(self.title).replace("_", "-")
			self.name = append_number_if_name_exists("GP Team", slug)
		if frappe.session.user != "Guest":
			self.add_member(frappe.session.user, is_admin=1)

	def after_insert(self):
		self.create_general_space()

	def create_general_space(self):
		# The migration that creates `Default` suppresses this so orphaned spaces can be
		# reassigned into it without a stray General being created first.
		if self.flags.skip_general_space:
			return

		# Guarantee every community has at least one public landing space.
		# Skip if any space already exists in this team (covers the migration path
		# where Default may inherit pre-existing orphaned spaces).
		if frappe.db.exists("GP Project", {"team": self.name}):
			return

		frappe.get_doc(doctype="GP Project", title="General", team=self.name, is_private=0).insert(
			ignore_permissions=True
		)

	def add_member(self, email, is_admin=0):
		member = self.get_member(email)
		if member:
			member.is_admin = cint(member.is_admin) or cint(is_admin)
			return

		self.append(
			"members",
			{"email": email, "user": email, "status": "Accepted", "is_admin": is_admin},
		)

	@frappe.whitelist(methods=["POST"])
	def add_members(self, users):
		require_can_manage_community(self)
		for user in users:
			self.add_member(user)
		self.save()

	@frappe.whitelist(methods=["POST"])
	def remove_member(self, user):
		require_can_manage_community(self)
		member = self.get_member(user)
		if not member:
			return

		self.ensure_can_remove_member(member)
		self.remove(member)
		self.remove_private_space_memberships(user)
		self.save()

	@frappe.whitelist(methods=["POST"])
	def remove_guest_access(self, user):
		require_can_manage_community(self)
		for access_name in self.get_guest_access_names(user):
			frappe.delete_doc("GP Guest Access", access_name, ignore_permissions=True)

	@frappe.whitelist(methods=["POST"])
	def remove_guest_invitation(self, invitation):
		require_can_manage_community(self)
		invitation = frappe.get_doc("GP Invitation", invitation)
		if invitation.role != "Gameplan Guest" or invitation.status != "Pending":
			frappe.throw("Invalid guest invitation")

		# Compare as str (project names are ints for autoincrement doctypes), but keep
		# the invitation's original project values so they round-trip unchanged.
		project_names = {str(project) for project in self.get_project_names()}
		invitation_projects = frappe.parse_json(invitation.projects or "[]")
		remaining_projects = [project for project in invitation_projects if str(project) not in project_names]
		if len(remaining_projects) == len(invitation_projects):
			frappe.throw("Not permitted", frappe.PermissionError)

		if remaining_projects:
			invitation.projects = frappe.as_json(remaining_projects)
			invitation.save(ignore_permissions=True)
			return

		frappe.delete_doc("GP Invitation", invitation.name, ignore_permissions=True)

	@frappe.whitelist(methods=["POST"])
	def merge_into_team(self, team: str):
		if self.archived_at:
			frappe.throw(_("Cannot merge an archived community"))

		require_can_manage_community(self)
		target = self.get_merge_target(team)
		require_can_manage_community(target)

		self.move_spaces_to(target.name)
		self.copy_members_to(target)
		self.archive()

	@frappe.whitelist(methods=["POST"])
	def set_member_admin(self, user, is_admin):
		require_can_manage_community(self)
		member = self.get_member(user)
		if not member:
			frappe.throw("Member not found")

		if member.is_admin and not cint(is_admin):
			self.ensure_can_remove_admin(member)

		member.is_admin = cint(is_admin)
		self.save()

	def get_member(self, user):
		return next((member for member in self.members if member.user == user), None)

	def ensure_can_remove_member(self, member):
		if member.is_admin:
			self.ensure_can_remove_admin(member)

	def ensure_can_remove_admin(self, member):
		if self.count_admins(excluding_user=member.user) == 0:
			frappe.throw("A community must have at least one admin")

	def count_admins(self, excluding_user=None):
		return len(
			[
				member
				for member in self.members
				if member.is_admin and member.user and member.user != excluding_user
			]
		)

	def remove_private_space_memberships(self, user):
		for project_name in self.get_project_names(is_private=1):
			project = frappe.get_doc("GP Project", project_name)
			member = next((member for member in project.members if member.user == user), None)
			if member:
				project.remove(member)
				project.save(ignore_permissions=True)

	def get_guest_access_names(self, user):
		project_names = self.get_project_names()
		if not project_names:
			return []

		return frappe.qb.get_query(
			"GP Guest Access",
			filters={"user": user, "project": ["in", project_names]},
			fields=["name"],
		).run(pluck=True)

	def get_project_names(self, is_private=None):
		filters = {"team": self.name}
		if is_private is not None:
			filters["is_private"] = is_private

		return frappe.qb.get_query("GP Project", filters=filters, fields=["name"]).run(pluck=True)

	def get_merge_target(self, team: str):
		if not team or team == self.name:
			frappe.throw(_("Select a different community to merge into"))
		if not frappe.db.exists("GP Team", team):
			frappe.throw(_('Invalid community "{0}"').format(team))

		target = frappe.get_doc("GP Team", team)
		if target.archived_at:
			frappe.throw(_("Cannot merge into an archived community"))
		return target

	def move_spaces_to(self, team: str):
		for project_name in self.get_project_names():
			project = frappe.get_doc("GP Project", project_name)
			project.move_to_team(team)

	def copy_members_to(self, target):
		for member in self.members:
			if member.user:
				target.add_member(member.user, is_admin=member.is_admin)
		# The merge caller has already asserted manage-community permission on target.
		target.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
@validate_type
def join_team(team: str):
	"""Add the session user to one community.

	Membership is what puts a community and its public spaces in the sidebar. This is
	the single-community counterpart of `update_joined_teams`, which rewrites the whole
	joined list. Only active, public communities can be joined; a private one is invite
	only.

	Lives at module level rather than on the doc because a plain member has no write
	permission on GP Team, and the document method route demands one for POST.
	"""
	doc = get_team_for_membership_change(team)
	if doc.is_private:
		frappe.throw(_("This community is invite only"), frappe.PermissionError)

	if doc.get_member(frappe.session.user):
		return

	doc.add_member(frappe.session.user)
	doc.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
@validate_type
def leave_team(team: str):
	"""Remove the session user from one community.

	Drops the membership row only, exactly like `update_joined_teams`, so rejoining a
	public community restores what the member had. Private space memberships stay, in
	contrast to `GPTeam.remove_member`, which an admin uses to revoke someone's access.
	"""
	doc = get_team_for_membership_change(team)
	member = doc.get_member(frappe.session.user)
	if not member:
		return

	if member.is_admin and doc.count_admins(excluding_user=frappe.session.user) == 0:
		frappe.throw(_("Make someone else an admin before you leave this community"))

	doc.remove(member)
	doc.save(ignore_permissions=True)


def get_team_for_membership_change(team: str):
	if gameplan.is_guest():
		frappe.throw(_("Guests cannot join or leave communities"), frappe.PermissionError)

	doc = frappe.get_doc("GP Team", team)
	doc.check_permission("read")
	if doc.archived_at:
		frappe.throw(_("This community is archived"))
	return doc


@frappe.whitelist(methods=["POST"])
@validate_type
def update_joined_teams(teams: list = None, sidebar_badge_style: str | None = None):
	if gameplan.is_guest():
		frappe.throw("Guests cannot manage communities")

	ordered_team_names = list(dict.fromkeys(teams or []))
	team_names = set(ordered_team_names)
	if not team_names:
		frappe.throw("Select at least one community")

	accessible_team_names = set(get_accessible_team_names())
	if invalid_teams := team_names - accessible_team_names:
		frappe.throw(f"Not permitted to join: {', '.join(sorted(invalid_teams))}")

	user = frappe.session.user
	for team_name in accessible_team_names:
		team = frappe.get_doc("GP Team", team_name)
		member = next((member for member in team.members if member.user == user), None)

		if team_name in team_names and not member:
			team.append("members", {"user": user})
			team.save(ignore_permissions=True)
		elif team_name not in team_names and member:
			team.remove(member)
			team.save(ignore_permissions=True)

	save_session_user_sidebar_preferences(ordered_team_names, sidebar_badge_style)
	return ordered_team_names


def save_session_user_sidebar_preferences(team_names: list[str], sidebar_badge_style: str | None = None):
	from gameplan.gameplan.doctype.gp_user_profile.gp_user_profile import get_session_user_profile

	profile = get_session_user_profile()
	profile.community_order = frappe.as_json(team_names)
	if sidebar_badge_style is not None:
		profile.sidebar_badge_style = get_valid_sidebar_badge_style(sidebar_badge_style)
	profile.save(ignore_permissions=True)


def get_valid_sidebar_badge_style(sidebar_badge_style: str):
	if sidebar_badge_style not in {"Unread count", "Dot"}:
		frappe.throw("Invalid sidebar badge style")
	return sidebar_badge_style


def get_public_team_names():
	"""Every community anyone may join, newest last.

	Public and not archived, which is the same pair of conditions
	`get_accessible_team_names` applies to the public half of its result. This one takes
	no user, so it can answer for an account that has no session yet.
	"""
	Team = frappe.qb.DocType("GP Team")
	return (
		frappe.qb.from_(Team)
		.select(Team.name)
		.where(Team.is_private == 0)
		.where(Team.archived_at.isnull())
		.orderby(Team.creation)
	).run(pluck=True)


def get_accessible_team_names():
	Team = frappe.qb.DocType("GP Team")
	Member = frappe.qb.DocType("GP Member")
	member_exists = (
		frappe.qb.from_(Member)
		.select(Member.name)
		.where(Member.parenttype == "GP Team")
		.where(Member.parent == Team.name)
		.where(Member.user == frappe.session.user)
	)
	query = (
		frappe.qb.from_(Team)
		.select(Team.name)
		.where(Team.archived_at.isnull())
		.where((Team.is_private == 0) | ((Team.is_private == 1) & ExistsCriterion(member_exists)))
	)

	return [team.name for team in query.run(as_dict=True)]
