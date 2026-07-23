# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Canonical executable spec of Gameplan's permission model.

Permissive philosophy (see AGENTS.md and test_permissions_backend.py):
  - Members create and edit anything they can see (edits are shown in revisions).
  - Delete is the only gated action: owner, community admin, or global admin.
  - Private spaces are visible only to their members and to guests granted access;
    content inherits its space's visibility.

This table is the source of truth for who may read/write/delete content. To extend:
  - Add content doctypes to the world builder in setUp (append to self.content).
  - Add actors or spaces by adding rows/blocks to EXPECTATIONS below.
"""

from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_space,
	grant_guest_access,
)

# Order matches the (read, write, delete) tuples in EXPECTATIONS.
ACTIONS = ("read", "write", "delete")

# space kind -> actor -> (read, write, delete)
EXPECTATIONS = {
	"public_space": {
		"admin": (True, True, True),
		"member": (True, True, True),  # owner of the content
		"second_member": (True, True, False),  # community member, not owner
		"outsider": (True, True, False),  # Gameplan Member, not in community
		"guest": (False, False, False),  # guest access only to the private space
	},
	"private_space": {
		"admin": (True, True, True),
		"member": (True, True, True),  # space member + owner
		"second_member": (False, False, False),  # community member but not space member
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
}


class TestPermissionMatrix(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Matrix Community", members=[self.member, self.second_member])
		self.public_space = create_space("Matrix Public Space", self.community)
		self.private_space = create_space(
			"Matrix Private Space", self.community, is_private=1, members=[self.member]
		)
		grant_guest_access(self.guest, self.private_space)

		self.content = {}
		for kind, space in (("public_space", self.public_space), ("private_space", self.private_space)):
			discussion = create_discussion(f"{kind} discussion", space, owner=self.member)
			comment = create_comment(discussion, owner=self.member)
			self.content[kind] = {
				"GP Discussion": discussion,
				"GP Comment": comment,
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
