# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe import _
from frappe.utils import cint

from gameplan.permissions import is_global_admin, users_who_can_view_space
from gameplan.public_access import (
	VISIBILITY_ANONYMOUS,
	VISIBILITY_GENERAL,
	VISIBILITY_TIERS,
	refresh_anonymous_readable,
	visibility_tier,
)
from gameplan.realtime import notify_unread_counts_changed
from gameplan.roles import GAMEPLAN_ROLES

# The fields `is_anonymous_readable` depends on, per doctype.
ANONYMOUS_READABLE_INPUTS = {
	"GP Team": ("visibility", "archived_at"),
	"GP Project": ("visibility", "archived_at", "team"),
}

# Per-user rows that point at a space and outlive losing access to it. Pins in
# GP User Profile.pinned_spaces are left alone: the sidebar only ever shows a pin for a
# space the user can list, so a stale one never renders, and it returns with the access.
SPACE_STATE_DOCTYPES = ("GP Unread Record", "GP Pinned Project", "GP Followed Project")


class HasVisibility:
	"""Visibility bookkeeping shared by GP Team and GP Project.

	Both carry `visibility`, `visibility_set_by` and `visibility_set_at`, and a legacy
	`is_private` column that nothing reads or writes any more. The controllers call these
	methods from their own lifecycle hooks.
	"""

	def set_default_visibility(self):
		"""Give a new record today's default tier, and refuse the retired `is_private` flag.

		Normally the tier is already set by now. A Select field without a default takes its
		first option (frappe/model/create_new.py), which is why General is listed first:
		reorder the options and new records silently change tier. A data import skips
		those defaults, so this fills the tier in for that path.

		A caller that still sends `is_private = 1` asked for a private record. Ignoring the
		flag would create a General one instead, readable by every signed-in user, so the
		insert fails. `is_private = 0` asks for what the default gives anyway.
		"""
		if cint(self.get("is_private")):
			frappe.throw(_("is_private is no longer accepted. Set visibility instead."))
		if not self.visibility:
			self.visibility = VISIBILITY_GENERAL

	def check_visibility_change_allowed(self):
		"""Only a Gameplan Admin changes a tier, or creates something on the Anonymous tier.

		Checked on the field rather than in one method, because a method is only one of the
		routes: a plain save, the Desk form and the generic REST routes all reach it too.
		Write permission is not enough on its own. Every member of a Member Access space may
		manage it, and a community admin manages every General space in the community.
		"""
		if is_global_admin(frappe.session.user):
			return
		if self.is_new():
			if visibility_tier(self.visibility) == VISIBILITY_ANONYMOUS:
				frappe.throw(
					_("Only Gameplan Admins can make something readable without signing in"),
					frappe.PermissionError,
				)
			return
		if self.has_value_changed("visibility"):
			frappe.throw(_("Only Gameplan Admins can change visibility"), frappe.PermissionError)

	def record_visibility_change(self):
		"""Stamp who changed the tier, and when.

		Runs on every save rather than inside one method, so a change made from Desk or a
		console is recorded as well as one made from the app.
		"""
		if self.has_value_changed("visibility"):
			self.visibility_set_by = frappe.session.user
			self.visibility_set_at = frappe.utils.now()

	def refresh_anonymous_readable_flags(self):
		"""Keep `GP Project.is_anonymous_readable` current for every space this record affects.

		Called from on_update, so every route that changes the answer recomputes it: a tier
		change, archive and unarchive (which save), and moving a space to another community.
		A community change recomputes all of its spaces, because theirs depends on it.
		"""
		inputs = ANONYMOUS_READABLE_INPUTS[self.doctype]
		# A read-only field is still writable through the generic document APIs.
		# Recompute the space flag on every save instead of trusting a submitted value.
		if (
			self.doctype == "GP Team"
			and self.get_doc_before_save()
			and not any(self.has_value_changed(field) for field in inputs)
		):
			return
		refresh_anonymous_readable(self.get_affected_space_names())
		if self.doctype == "GP Project":
			self.is_anonymous_readable = frappe.db.get_value("GP Project", self.name, "is_anonymous_readable")

	def reconcile_access_after_visibility_change(self):
		"""Drop the per-user state of everyone who can no longer read an affected space.

		Decided from what is stored, not from which way the tier moved: for every user who
		holds unread records, a pin or a follow on a space, ask whether they can still read
		it. Loosening therefore drops nothing, and the answer is right for any transition.
		"""
		before = self.get_doc_before_save()
		if not before or before.visibility == self.visibility:
			return

		lost_access = set()
		for space in self.get_affected_space_names():
			holders = users_with_space_state(space)
			lost = holders - set(users_who_can_view_space(holders, space))
			if lost:
				delete_space_state(space, lost)
				lost_access |= lost

		if lost_access:
			notify_unread_counts_changed(list(lost_access))

	def get_affected_space_names(self):
		"""The spaces whose readers depend on this record's tier."""
		if self.doctype == "GP Project":
			return [self.name]
		return frappe.get_all("GP Project", filters={"team": self.name}, pluck="name")

	@frappe.whitelist(methods=["POST"])
	def set_visibility(self, visibility: str):
		"""Change the tier through the same audited save used by Desk and REST."""
		validate_visibility_action(visibility)
		self.visibility = visibility
		self.save()

	@frappe.whitelist()
	def get_visibility_change_impact(self, visibility: str):
		"""Preview the actual reader rules inside a savepoint, then roll back the change."""
		validate_visibility_action(visibility)

		users = gameplan_users()
		spaces = self.get_affected_space_names()
		readers_before = {space: set(users_who_can_view_space(users, space)) for space in spaces}
		public_before = anonymous_readable_spaces(spaces)
		frappe.db.savepoint("visibility_impact")
		try:
			frappe.db.set_value(self.doctype, self.name, "visibility", visibility, update_modified=False)
			refresh_anonymous_readable(spaces)
			readers_after = {space: set(users_who_can_view_space(users, space)) for space in spaces}
			public_after = anonymous_readable_spaces(spaces)
		finally:
			frappe.db.rollback(save_point="visibility_impact")

		gaining, losing = set(), set()
		spaces_gaining, spaces_losing = [], []
		for space in spaces:
			gained = readers_after[space] - readers_before[space]
			lost = readers_before[space] - readers_after[space]
			gaining |= gained
			losing |= lost
			if gained:
				spaces_gaining.append(space)
			if lost:
				spaces_losing.append(space)

		return {
			"users_gaining_access": len(gaining),
			"users_losing_access": len(losing),
			"discussions_revealed": count_discussions(spaces_gaining),
			"spaces_losing_readers": len(spaces_losing),
			# Readable without signing in once the public access switch is on.
			"discussions_made_public": count_discussions(public_after - public_before),
			"discussions_no_longer_public": count_discussions(public_before - public_after),
			"leaving_anonymous": self.visibility == VISIBILITY_ANONYMOUS
			and visibility != VISIBILITY_ANONYMOUS,
		}


def validate_visibility_action(visibility):
	if not is_global_admin(frappe.session.user):
		frappe.throw(_("Only Gameplan Admins can change visibility"), frappe.PermissionError)
	if visibility not in VISIBILITY_TIERS:
		frappe.throw(_("Unknown visibility: {0}").format(visibility))


def users_with_space_state(space):
	"""Every user holding a SPACE_STATE_DOCTYPES row on `space`."""
	users = set()
	for doctype in SPACE_STATE_DOCTYPES:
		users.update(frappe.get_all(doctype, filters={"project": str(space)}, pluck="user", distinct=True))
	return users


def delete_space_state(space, users):
	for doctype in SPACE_STATE_DOCTYPES:
		frappe.db.delete(doctype, {"project": str(space), "user": ["in", list(users)]})


def gameplan_users():
	"""Every enabled user holding a Gameplan role."""
	return frappe.get_all(
		"User",
		filters={"enabled": 1, "roles.role": ["in", GAMEPLAN_ROLES]},
		pluck="name",
		distinct=True,
	)


def anonymous_readable_spaces(spaces):
	if not spaces:
		return set()
	return set(
		frappe.get_all(
			"GP Project",
			filters={"name": ["in", [str(space) for space in spaces]], "is_anonymous_readable": 1},
			pluck="name",
		)
	)


def count_discussions(spaces):
	if not spaces:
		return 0
	return frappe.db.count("GP Discussion", {"project": ["in", [str(space) for space in spaces]]})
