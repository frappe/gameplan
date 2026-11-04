import frappe

from gameplan.api import set_discussion_read_state
from gameplan.community_bans import set_ban
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_space
from gameplan.visibility import VISIBILITY_MEMBER_ACCESS


class TestReaderState(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Read markers", members=[self.member])
		self.space = create_space("Read markers", self.community)
		self.discussion = create_discussion("Read markers", self.space)

	def test_banned_and_archived_readers_can_update_their_own_read_state(self):
		for archived in (False, True):
			with self.subTest(archived=archived):
				if archived:
					self.space.archive()
				else:
					set_ban(self.community.name, self.member.name, 1, "Read only")
				unread = frappe.get_doc(
					doctype="GP Unread Record",
					user=self.member.name,
					project=self.space.name,
					discussion=self.discussion.name,
					is_unread=1,
				).insert(ignore_permissions=True)
				notification = frappe.get_doc(
					doctype="GP Notification",
					to_user=self.member.name,
					discussion=self.discussion.name,
					type="Mention",
					read=0,
				).insert(ignore_permissions=True)
				with self.as_user(self.member):
					set_discussion_read_state(str(self.discussion.name))
					self.assertEqual(frappe.db.get_value("GP Unread Record", unread.name, "is_unread"), 0)
					self.assertEqual(frappe.db.get_value("GP Notification", notification.name, "read"), 1)
					set_discussion_read_state(str(self.discussion.name), unread=True)
					self.assertTrue(
						frappe.db.exists(
							"GP Unread Record",
							{"discussion": self.discussion.name, "user": self.member.name, "is_unread": 1},
						)
					)
				if not archived:
					set_ban(self.community.name, self.member.name, 0)

	def test_inaccessible_and_removed_discussions_do_not_accept_read_markers(self):
		private = create_space("Restricted", self.community, visibility=VISIBILITY_MEMBER_ACCESS)
		self.discussion.move_to_project(private.name)
		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			set_discussion_read_state(str(self.discussion.name))
		self.discussion.hide("Unavailable")
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			set_discussion_read_state(str(self.discussion.name))
