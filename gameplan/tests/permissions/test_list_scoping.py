# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""List filters, asserted from both sides.

Every filter in this file answers an enumeration with "your rows only". A test that
asserts nothing but "I can see mine" passes just as happily against a filter that hands
back everybody's rows, so each case below also names a row belonging to somebody else
and asserts it is absent. That second half is the one that tests the filter.

Enumeration goes through `frappe.get_list` — the generic list API the SPA reaches over
/api/v2, and the path `permission_query_conditions` guards. It is a separate door from
the per-document `has_permission` checks the permission matrix walks: a doctype can
refuse to hand over a document by name and still list it.
"""

import frappe

from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_page,
	create_poll,
	create_space,
	create_task,
	set_owner,
)


class ListScopingTestCase(GameplanTestCase):
	def assert_listed_for(self, doctype, user, *, visible, hidden):
		"""Assert `user` enumerating `doctype` gets `visible` and not `hidden`."""
		with self.as_user(user):
			listed = {str(name) for name in frappe.get_list(doctype, pluck="name", limit_page_length=0)}

		self.assertIn(str(visible.name), listed, f"{user.name} should see {doctype} {visible.name}")
		self.assertNotIn(str(hidden.name), listed, f"{user.name} must not see {doctype} {hidden.name}")


class TestPersonalRowListScoping(ListScopingTestCase):
	"""Rows that belong to exactly one user.

	A space-less page and a discussion-less poll have no space to inherit visibility
	from, and a draft or a bookmark never had one: for all four the owner is the whole
	audience, so enumeration must stop at them.
	"""

	def setUp(self):
		super().setUp()
		self.community = create_community("Personal Row Community", members=[self.member, self.second_member])
		self.space = create_space("Personal Row Space", self.community)
		self.discussion = create_discussion("Personal Row Discussion", self.space, owner=self.member)

	def create_draft(self, title, owner):
		draft = frappe.get_doc(doctype="GP Draft", title=title, content="Draft content").insert(
			ignore_permissions=True
		)
		return set_owner(draft, owner)

	def create_bookmark(self, user):
		return frappe.get_doc(doctype="GP Bookmark", user=user.name, discussion=self.discussion.name).insert(
			ignore_permissions=True
		)

	def test_a_space_less_page_is_listed_only_for_its_owner(self):
		mine = create_page("My Personal Page", owner=self.member)
		theirs = create_page("Their Personal Page", owner=self.second_member)

		self.assert_listed_for("GP Page", self.member, visible=mine, hidden=theirs)

	def test_a_discussion_less_poll_is_listed_only_for_its_owner(self):
		mine = create_poll("My Loose Poll", None, owner=self.member)
		theirs = create_poll("Their Loose Poll", None, owner=self.second_member)

		self.assert_listed_for("GP Poll", self.member, visible=mine, hidden=theirs)

	def test_a_draft_is_listed_only_for_its_owner(self):
		mine = self.create_draft("My Draft", self.member)
		theirs = self.create_draft("Their Draft", self.second_member)

		self.assert_listed_for("GP Draft", self.member, visible=mine, hidden=theirs)

	def test_a_bookmark_is_listed_only_for_the_user_it_belongs_to(self):
		# A bookmark is scoped by its `user` field rather than by `owner`: it is the
		# reading list of the user it names, whoever created the row.
		mine = self.create_bookmark(self.member)
		theirs = self.create_bookmark(self.second_member)

		self.assert_listed_for("GP Bookmark", self.member, visible=mine, hidden=theirs)


class TestCommentListScoping(ListScopingTestCase):
	"""A comment is listed from the space of whatever it hangs off.

	Discussions and tasks are two separate branches of the filter, and a comment reaches
	the list through exactly one of them, so both are asserted: a filter that lost the
	task branch would still look correct measured on discussion comments alone.
	"""

	def setUp(self):
		super().setUp()
		self.community = create_community(
			"Comment Scope Community", members=[self.member, self.second_member]
		)
		self.visible_space = create_space("Comment Visible Space", self.community)
		self.hidden_space = create_space(
			"Comment Hidden Space", self.community, is_private=1, members=[self.second_member]
		)

	def comment_on_task(self, task, owner):
		comment = frappe.get_doc(
			doctype="GP Comment",
			reference_doctype="GP Task",
			reference_name=task.name,
			content="Task comment",
		).insert(ignore_permissions=True)
		return set_owner(comment, owner)

	def test_a_discussion_comment_is_listed_only_from_a_space_the_user_can_see(self):
		visible = create_comment(
			create_discussion("Visible Comment Thread", self.visible_space, owner=self.member),
			owner=self.member,
		)
		hidden = create_comment(
			create_discussion("Hidden Comment Thread", self.hidden_space, owner=self.second_member),
			owner=self.second_member,
		)

		self.assert_listed_for("GP Comment", self.member, visible=visible, hidden=hidden)

	def test_a_task_comment_is_listed_only_from_a_space_the_user_can_see(self):
		visible = self.comment_on_task(
			create_task("Visible Comment Task", self.visible_space, owner=self.member), self.member
		)
		hidden = self.comment_on_task(
			create_task("Hidden Comment Task", self.hidden_space, owner=self.second_member),
			self.second_member,
		)

		self.assert_listed_for("GP Comment", self.member, visible=visible, hidden=hidden)


class TestMembershipListScoping(ListScopingTestCase):
	"""Membership is what puts a private community or space in your list.

	Communities and spaces keep their members in the same child table, told apart only
	by `parenttype`, so each list has to be asserted against a private container the
	user belongs to as well as one they do not: a membership lookup that stopped
	distinguishing the two would empty the user's own list rather than fill it.
	"""

	def test_a_private_community_is_listed_only_for_its_own_members(self):
		mine = create_community("My Private Community", is_private=1, members=[self.member])
		theirs = create_community("Their Private Community", is_private=1, members=[self.second_member])

		self.assert_listed_for("GP Team", self.member, visible=mine, hidden=theirs)

	def test_a_private_space_is_listed_only_for_its_own_members(self):
		community = create_community("Space Membership Community", members=[self.member, self.second_member])
		mine = create_space("My Private Space", community, is_private=1, members=[self.member])
		theirs = create_space("Their Private Space", community, is_private=1, members=[self.second_member])

		self.assert_listed_for("GP Project", self.member, visible=mine, hidden=theirs)
