# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe import _
from frappe.utils import cint

from gameplan.permissions import is_global_admin, users_who_can_view_space
from gameplan.realtime import notify_unread_counts_changed
from gameplan.roles import GAMEPLAN_ROLES
from gameplan.visibility import (
	VISIBILITY_ANONYMOUS,
	VISIBILITY_GENERAL,
	VISIBILITY_TIERS,
	refresh_anonymous_readable,
	visibility_tier,
)

# Per-user rows that point at a space and outlive losing access to it. Pins in
# GP User Profile.pinned_spaces are left alone: the sidebar only ever shows a pin for a
# space the user can list, so a stale one never renders, and it returns with the access.
SPACE_STATE_DOCTYPES = ("GP Unread Record", "GP Pinned Project", "GP Followed Project")


class HasVisibility:
	"""Shared visibility validation, audit stamps and access-state updates."""

	def set_default_visibility(self):
		"""Default to General; reject is_private=1 inserts rather than exposing them."""
		if cint(self.get("is_private")):
			frappe.throw(_("is_private is no longer accepted. Set visibility instead."))
		if not self.visibility:
			self.visibility = VISIBILITY_GENERAL

	def check_visibility_change_allowed(self):
		"""Require a global admin for tier changes and Anonymous inserts on every save route."""
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
		"""Stamp tier changes from all save routes, including Desk and imports."""
		if self.has_value_changed("visibility"):
			self.visibility_set_by = frappe.session.user
			self.visibility_set_at = frappe.utils.now()

	def refresh_anonymous_readable_flags(self):
		"""Refresh affected spaces after tier, archive or community changes."""
		refresh_anonymous_readable(self.get_affected_space_names())

	def reconcile_access_after_visibility_change(self):
		"""Delete unread, pin and follow rows only for users who lost access to affected spaces."""
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
		raise NotImplementedError

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

		gained = {space: readers_after[space] - readers_before[space] for space in spaces}
		lost = {space: readers_before[space] - readers_after[space] for space in spaces}

		return {
			"users_gaining_access": len(set().union(*gained.values())),
			"users_losing_access": len(set().union(*lost.values())),
			"discussions_revealed": count_discussions([space for space in spaces if gained[space]]),
			"spaces_losing_readers": sum(bool(lost[space]) for space in spaces),
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
