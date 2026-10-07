# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Canonical executable spec of Gameplan's permission model.

Permissive philosophy (see AGENTS.md):
  - Members create and edit anything they can see (edits are shown in revisions).
  - Delete is the only gated action: owner, global admin, or — within the spaces they
    can see — community admin.
  - General requires a signed-in member. Anonymous allows public reading when both
    community and space allow it; signed-in guests can participate without a grant.
  - Member Access spaces are visible only to their members and to guests granted access;
    content inherits its space's visibility. Visibility is checked first, so this bounds
    the previous rule: a community admin who is not a member of a private space in their
    own community cannot read its content, and therefore cannot moderate or delete it
    either. That is intended — see the `community_admin` rows below.

This table is the source of truth for who may read/write/delete content. To extend:
  - Add content doctypes to the world builder in setUp (append to self.content).
  - Add actors or spaces by adding rows/blocks to EXPECTATIONS below.
"""

from unittest.mock import patch

import frappe

from gameplan.public_access import VISIBILITY_ANONYMOUS, VISIBILITY_GENERAL, VISIBILITY_MEMBER_ACCESS
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_member,
	create_page,
	create_poll,
	create_space,
	create_task,
	grant_guest_access,
)

# Order matches the (read, write, delete) tuples in EXPECTATIONS.
ACTIONS = ("read", "write", "delete")

# space kind -> actor -> (read, write, delete)
EXPECTATIONS = {
	"general_space": {
		"admin": (True, True, True),
		"member": (True, True, True),  # owner of the content
		"second_member": (True, True, False),  # community member, not owner
		"community_admin": (True, True, True),  # may moderate anything they can see
		"outsider": (True, True, False),  # Gameplan Member, not in community
		"guest": (False, False, False),  # guest access only to the private space
	},
	"member_access_space": {
		"admin": (True, True, True),
		"member": (True, True, True),  # space member + owner
		"second_member": (False, False, False),  # community member but not space member
		# A community admin's moderation power stops at the private-space boundary:
		# can_view_space requires space membership when the space is private, so the
		# admin cannot even read the content, let alone delete it.
		"community_admin": (False, False, False),
		"outsider": (False, False, False),
		# Member-OWNED content. write == "may interact" (react/comment), which a
		# guest with space access holds even on someone else's post: a clean-doc
		# permission check reports no protected-field change, so it passes. Editing
		# another's content is blocked separately at save time by
		# content_has_permission's write branch (see
		# permissions._protected_fields_changed and
		# features/test_guest_participation.py). delete stays False: a guest may
		# delete only content they own.
		"guest": (True, True, False),
	},
	"anonymous_space": {
		"admin": (True, True, True),
		"member": (True, True, True),
		"second_member": (True, True, False),
		"community_admin": (True, True, True),
		"outsider": (True, True, False),
		"guest": (True, True, False),  # signed-in guest, without an explicit grant
	},
}


class TestPermissionMatrix(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community_admin = create_member("matrix_community_admin@example.com", "Community Admin")
		self.community = create_community(
			"Matrix Community",
			members=[self.member, self.second_member],
			admins=[self.community_admin],
		)
		self.general_space = create_space(
			"Matrix General Space", self.community, visibility=VISIBILITY_GENERAL
		)
		self.private_space = create_space(
			"Matrix Private Space", self.community, visibility=VISIBILITY_MEMBER_ACCESS, members=[self.member]
		)
		grant_guest_access(self.guest, self.private_space)
		self.anonymous_community = create_community(
			"Matrix Anonymous Community",
			visibility=VISIBILITY_ANONYMOUS,
			members=[self.member, self.second_member],
			admins=[self.community_admin],
		)
		self.anonymous_space = create_space(
			"Matrix Anonymous Space", self.anonymous_community, visibility=VISIBILITY_ANONYMOUS
		)
		public_switch = patch.dict(frappe.conf, gameplan_public_access_enabled=1, gameplan_demo_enabled=0)
		public_switch.start()
		self.addCleanup(public_switch.stop)

		self.content = {}
		for kind, space in (
			("general_space", self.general_space),
			("member_access_space", self.private_space),
			("anonymous_space", self.anonymous_space),
		):
			discussion = create_discussion(f"{kind} discussion", space, owner=self.member)
			self.content[kind] = {
				"GP Discussion": discussion,
				"GP Comment": create_comment(discussion, owner=self.member),
				"GP Poll": create_poll(f"{kind} poll", discussion, owner=self.member),
				"GP Page": create_page(f"{kind} page", space, owner=self.member),
				"GP Task": create_task(f"{kind} task", space, owner=self.member),
			}

	def actor(self, name):
		return getattr(self, name)

	def test_content_permission_matrix(self):
		for kind, actors in EXPECTATIONS.items():
			for actor_name, expected in actors.items():
				user = self.actor(actor_name)
				for action, allowed in zip(ACTIONS, expected, strict=True):
					for doctype, doc in self.content[kind].items():
						with self.subTest(space=kind, actor=actor_name, action=action, doctype=doctype):
							self.assert_permission(doc, action, user, allowed)
