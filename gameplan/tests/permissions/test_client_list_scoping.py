# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The SPA's query-builder lists must apply the same row permissions as frappe.get_list."""

import frappe

from gameplan.extends.client import get_list as get_client_list
from gameplan.public_access import VISIBILITY_MEMBER_ACCESS
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_page,
	create_poll,
	create_space,
	create_task,
)

# Doctypes for which setUp creates rows the second member must not see.
FIXTURE_HIDDEN_DOCTYPES = {
	"GP Activity",
	"GP Bookmark",
	"GP Comment",
	"GP Discussion",
	"GP Discussion Visit",
	"GP Draft",
	"GP Notification",
	"GP Page",
	"GP Poll",
	"GP Task",
}


def row_scoped_doctypes():
	return sorted(frappe.get_hooks("permission_query_conditions", {}).keys() & set(gameplan_doctypes()))


def gameplan_doctypes():
	return frappe.get_all("DocType", filters={"module": "Gameplan", "istable": 0}, pluck="name")


class TestClientListScoping(GameplanTestCase):
	def setUp(self):
		super().setUp()
		community = create_community("Scoping Community", members=[self.member, self.second_member])
		space = create_space(
			"Scoping Private Space", community, visibility=VISIBILITY_MEMBER_ACCESS, members=[self.member]
		)
		discussion = create_discussion("Scoping Discussion", space, owner=self.member)
		create_comment(discussion, owner=self.member)
		create_poll("Scoping Poll", discussion, owner=self.member)
		create_task("Scoping Task", space, owner=self.member)
		create_page("Scoping Page", space, owner=self.member)
		discussion.log_activity("Discussion Closed")
		frappe.get_doc(
			doctype="GP Notification",
			from_user=self.second_member.name,
			to_user=self.member.name,
			type="Mention",
			message="Scoping notification",
			discussion=discussion.name,
			project=space.name,
		).insert(ignore_permissions=True)
		with self.as_user(self.member):
			frappe.get_doc(
				doctype="GP Draft", title="Scoping Draft", content="body", type="Discussion", mode="New"
			).insert()
			discussion = frappe.get_doc("GP Discussion", discussion.name)
			discussion.add_bookmark()
			discussion.track_visit()

	def test_every_row_scoped_doctype_is_scoped_on_the_client_list_too(self):
		doctypes = row_scoped_doctypes()
		# Not vacuous: each of these has rows the outsider must not see.
		self.assertLessEqual(FIXTURE_HIDDEN_DOCTYPES, set(doctypes))
		for doctype in FIXTURE_HIDDEN_DOCTYPES:
			with self.subTest(fixture=doctype):
				everything = set(frappe.get_all(doctype, pluck="name"))
				with self.as_user(self.second_member):
					visible = set(frappe.get_list(doctype, pluck="name", limit_page_length=0))
				self.assertTrue(everything - visible, f"{doctype}: the fixtures hide nothing")

		for doctype in doctypes:
			with self.subTest(doctype=doctype), self.as_user(self.second_member):
				allowed = {str(name) for name in frappe.get_list(doctype, pluck="name", limit_page_length=0)}
				try:
					listed = {
						str(row.name) for row in get_client_list(doctype=doctype, fields=["name"], limit=0)
					}
				except frappe.PermissionError:
					continue
				self.assertLessEqual(listed, allowed, f"{doctype}: the client list shows rows get_list hides")
