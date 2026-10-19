# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The defaults in permissions.py that look dead but are not.

Mutation testing flagged four branches as survivors — no test changed its answer when
they were flipped — and they read like dead code:

  - `content_has_permission`'s trailing `return True`
  - `can_interact_with_content`'s global-admin short circuit
  - `can_interact_with_content`'s owner check for space-less content
  - `can_delete_content`'s explicit deny for space-less content

They are defaults in the security core, so "no test covers it" is the wrong reason to
delete one: removing a default converts a future *denied* into a future *allowed* (or,
for the deferring `return True`, breaks every desk permission read today). This module
pins what each one is actually for, so the next person deleting a survivor gets a red
test instead of a silent permission change.

All four are pinned by tests that go red when the branch changes, with one limit: the
owner check is pinned only in its allow direction. Its deny direction is guarded by
`can_view_content`, which runs first and already refuses anyone who is not the owner.
The last two are reached through a comment someone else wrote on a member's personal
task: the task's owner can see it and react to it, but not delete it.

The same trailing `return True` also ends `team_has_permission` (permissions.py:34) and
`project_has_permission` (L43) — load-bearing there too, but for a stronger reason, not
the same one. Unlike content_has_permission, neither hook decides `create` at all, so
ptype="create" falls through to their trailing default on every Space and Community
insert: an ordinary user action, not only the ptype=None dict read. Dropping either to
False would stop members creating spaces outright. Both are already pinned by
test_visibility.py::TestContainerManagement::
test_a_member_may_create_a_space_in_a_community_they_can_see (L207), which is why this
module does not re-test them.
"""

import frappe
from frappe.utils import cint

from gameplan.permissions import (
	can_delete_content,
	can_interact_with_content,
	can_view_content,
	content_has_permission,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_member,
	create_page,
	create_space,
	create_task,
	set_owner,
)

# Permission types frappe knows about that content_has_permission does not decide, plus
# the `None` that frappe.permissions.get_doc_permissions passes when it wants the whole
# evaluated dict rather than one answer. Every one of them lands on the trailing default.
UNGOVERNED_PTYPES = (None, "submit", "cancel", "amend", "import", "set_user_permissions")


class TestUngovernedPermissionTypes(GameplanTestCase):
	"""content_has_permission's trailing `return True` is "no opinion", not "allowed".

	A `has_permission` hook can only ever deny (frappe.permissions.has_controller_
	permissions: "Controllers can only deny permission, they can not explicitly grant any
	permission that wasn't already present"), so the honest answer for a permission type
	Gameplan does not model is True — defer to the doctype's role permissions.
	"""

	def setUp(self):
		super().setUp()
		self.community = create_community("Defaults Community", members=[self.member])
		self.space = create_space("Defaults Space", self.community)
		self.discussion = create_discussion("Defaults thread", self.space, owner=self.member)

	def test_the_content_hook_defers_on_permission_types_it_does_not_govern(self):
		for ptype in UNGOVERNED_PTYPES:
			with self.subTest(ptype=ptype):
				self.assertIs(content_has_permission(self.discussion, ptype, self.member.name), True)

	def test_deferring_is_a_blanket_answer_and_not_a_hole(self):
		"""Even for a user who cannot read the content, the answer is defer, not deny.

		That is safe precisely because the hook cannot grant: `submit` on a GP Discussion
		stays impossible because the doctype is not submittable and the role layer says so.
		If the trailing default were dropped to False instead, the hook would start
		denying permission types it was never asked to have an opinion on.
		"""
		self.assertIs(content_has_permission(self.discussion, "submit", self.outsider.name), True)
		# cint, because meta flags arrive as 0/"0"/False depending on how the doctype was
		# loaded, and only the truthiness is the contract here.
		self.assertFalse(cint(frappe.get_meta("GP Discussion").is_submittable))
		self.assertIs(
			frappe.has_permission(
				"GP Discussion", "submit", doc=self.discussion.name, user=self.outsider.name
			),
			False,
		)

	def test_the_evaluated_permission_dict_survives_the_content_hook(self):
		"""frappe.permissions.get_doc_permissions calls the hook with ptype=None.

		It is reachable over HTTP (frappe.client.get_doc_permissions, and desk form load),
		and a falsy answer there collapses the whole dict to `{None: 0}` — the document
		reads as having no permissions at all. This is the live caller that makes the
		trailing default load-bearing today, not just a guard for a future ptype.
		"""
		permissions = frappe.permissions.get_doc_permissions(self.discussion, user=self.member.name)

		self.assertTrue(permissions.get("read"))
		self.assertTrue(permissions.get("write"))


class TestInteractionFloor(GameplanTestCase):
	"""can_interact_with_content is the floor under the `write` permission.

	Its only caller (can_write_content) reaches it after can_edit_content has already
	said False, which is why its admin branch never fires from there: a global admin is
	always an editor. The branch still has to state the rule for the function itself —
	it is a named predicate about who may reach content to participate, and a global
	admin who could not is a wrong answer. The owner branch does fire from there, for
	the owner of a personal task on a comment someone else wrote on it.
	"""

	def setUp(self):
		super().setUp()
		self.personal_page = create_page("Interaction Personal Page", owner=self.member)
		self.task_comment = create_comment_on_personal_task(self.member, author=self.admin)

	def test_a_global_admin_can_interact_with_personal_content_they_do_not_own(self):
		self.assertIs(can_interact_with_content(self.admin.name, self.personal_page), True)

	def test_the_owner_can_interact_with_their_own_personal_content(self):
		self.assertIs(can_interact_with_content(self.member.name, self.personal_page), True)

	def test_a_stranger_cannot_interact_with_personal_content(self):
		self.assertIs(can_interact_with_content(self.second_member.name, self.personal_page), False)

	def test_the_task_owner_can_react_to_a_comment_on_their_personal_task(self):
		self.assertIs(can_interact_with_content(self.member.name, self.task_comment), True)
		self.assert_allowed(self.task_comment, "write", self.member)
		self.assert_not_allowed(self.task_comment, "write", self.second_member)


class TestPersonalContentHasNoModerators(GameplanTestCase):
	"""Space-less content answers to its author and the global admin, nobody else.

	can_delete_content's space-less `return False` is reached by one non-author who can
	see the content: the owner of a personal task, on a comment someone else wrote on
	it. test_the_task_owner_cannot_delete_a_comment_they_did_not_write pins that branch.
	The other tests pin the same rule by the paths around it: moderation stops at the
	edge of a space, space-less content stays deletable by its author and the global
	admin, and nobody else can see a personal page.
	"""

	def setUp(self):
		super().setUp()
		self.community_admin = create_member("defaults_community_admin@example.com", "Community Admin")
		self.community = create_community(
			"Moderation Community", members=[self.member], admins=[self.community_admin]
		)
		self.personal_page = create_page("Unmoderated Personal Page", owner=self.member)

	def test_a_community_admin_cannot_delete_personal_content(self):
		self.assertIs(can_delete_content(self.community_admin.name, self.personal_page), False)

	def test_the_owner_and_the_global_admin_can(self):
		self.assertIs(can_delete_content(self.member.name, self.personal_page), True)
		self.assertIs(can_delete_content(self.admin.name, self.personal_page), True)

	def test_nobody_else_can_even_view_personal_content(self):
		self.assertIs(can_view_content(self.community_admin.name, self.personal_page), False)
		self.assertIs(can_view_content(self.second_member.name, self.personal_page), False)

	def test_the_task_owner_cannot_delete_a_comment_they_did_not_write(self):
		comment = create_comment_on_personal_task(self.member, author=self.admin)

		self.assertIs(can_view_content(self.member.name, comment), True)
		self.assertIs(can_delete_content(self.member.name, comment), False)


def create_comment_on_personal_task(task_owner, *, author):
	task = create_task("Personal task with a comment", owner=task_owner)
	comment = frappe.get_doc(
		doctype="GP Comment",
		reference_doctype="GP Task",
		reference_name=task.name,
		content="Comment on a personal task",
	).insert(ignore_permissions=True)
	return set_owner(comment, author)
