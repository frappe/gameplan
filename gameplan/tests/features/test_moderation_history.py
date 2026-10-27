import frappe

from gameplan.community_bans import set_ban
from gameplan.moderation_history import history
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_comment, create_community, create_discussion, create_space
from gameplan.visibility import VISIBILITY_MEMBER_ACCESS


class TestModerationHistory(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("History", members=[self.member, self.second_member])
		self.community.set_member_moderator(self.second_member.name, 1)
		self.space = create_space("History Space", self.community)
		self.discussion = create_discussion("History topic", self.space, owner=self.member)
		self.reply = create_comment(self.discussion, content="Private original body", owner=self.member)

	def entries(self, **filters):
		with self.as_user(self.second_member):
			return history(self.community.name, **filters)["items"]

	def test_post_history_retains_actions_and_returns_only_metadata(self):
		with self.as_user(self.second_member):
			self.reply.hide("Off topic")
			self.reply.restore()
			self.reply.delete_spam("Repeated spam")
		rows = self.entries(kind="reply", target=str(self.reply.name))
		self.assertEqual([row.action for row in rows], ["Delete Spam", "Restore", "Hide"])
		self.assertEqual({row.owner for row in rows}, {self.second_member.name})
		self.assertEqual(rows[-1].reason, "Off topic")
		self.assertTrue(all(row.creation for row in rows))
		self.assertNotIn("Private original body", frappe.as_json(rows))
		self.assertNotIn("content", rows[0])
		self.assertNotIn("title", rows[0])

	def test_ordinary_members_guests_and_other_community_staff_cannot_read_history(self):
		other = create_community("Other staff", admins=[self.outsider])
		self.reply.hide("Restricted reason")
		for user in (self.member, self.guest, self.outsider, "Guest"):
			with self.subTest(user=str(user)), self.as_user(user), self.assertRaises(frappe.PermissionError):
				history(self.community.name)
		with self.as_user(self.outsider):
			self.assertEqual(history(other.name)["items"], [])
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("GP Moderation Log", self.entries()[0].name).check_permission("read")

	def test_private_space_history_requires_current_space_access(self):
		private = create_space("Private history", self.community, visibility=VISIBILITY_MEMBER_ACCESS)
		self.discussion.reload()
		self.discussion.project = private.name
		self.discussion.save()
		self.discussion.hide("Private discussion reason")
		self.reply.hide("Private reply reason")
		self.assertEqual(self.entries(), [])
		with self.as_user(self.admin):
			self.assertEqual(len(history(self.community.name)["items"]), 2)

	def test_history_follows_a_moved_discussion_and_its_replies(self):
		self.discussion.hide("Moved discussion")
		self.discussion.restore()
		self.reply.hide("Moved reply")
		other = create_community("Destination", members=[self.second_member])
		other.set_member_moderator(self.second_member.name, 1)
		space = create_space("Destination Space", other)
		self.discussion.reload()
		self.discussion.project = space.name
		self.discussion.save()
		self.assertEqual(self.entries(), [])
		with self.as_user(self.second_member):
			self.assertEqual(len(history(other.name)["items"]), 3)

	def test_missing_targets_stay_in_restricted_storage_and_do_not_fill_pages(self):
		for index in range(42):
			frappe.get_doc(
				doctype="GP Moderation Log", discussion=f"missing-{index}", action="Hide", reason="Orphan"
			).insert(ignore_permissions=True)
		self.reply.hide("Visible history")
		self.assertEqual(len(self.entries()), 1)
		log = self.entries()[0]
		frappe.db.delete("GP Comment", {"name": self.reply.name})
		self.assertEqual(self.entries(), [])
		self.assertTrue(frappe.db.exists("GP Moderation Log", log.name))

	def test_user_filter_returns_only_this_community_ban_history(self):
		other = create_community("Other bans")
		set_ban(self.community.name, self.member.name, 1, "Spam")
		set_ban(self.community.name, self.member.name, 0)
		set_ban(other.name, self.member.name, 1, "Other Community reason")
		self.reply.hide("Post action")
		rows = self.entries(kind="user", target=self.member.name)
		self.assertEqual([row.action for row in rows], ["Unban", "Ban"])
		self.assertEqual({row.user for row in rows}, {self.member.name})
		self.assertNotIn("Other Community reason", frappe.as_json(self.entries()))

	def test_target_filters_do_not_cross_post_types(self):
		self.discussion.hide("Discussion reason")
		self.reply.hide("Reply reason")
		rows = self.entries(kind="discussion", target=str(self.discussion.name))
		self.assertEqual([row.action for row in rows], ["Hide"])
		self.assertEqual(rows[0].reason, "Discussion reason")
		self.assertEqual(self.entries(kind="reply", target="missing"), [])

	def test_pages_are_bounded_and_deterministic_when_timestamps_match(self):
		for index in range(45):
			frappe.get_doc(
				doctype="GP Moderation Log", comment=self.reply.name, action="Restore", reason=str(index)
			).insert(ignore_permissions=True)
		Log = frappe.qb.DocType("GP Moderation Log")
		frappe.qb.update(Log).set(Log.creation, "2026-01-01 00:00:00").where(
			Log.comment == self.reply.name
		).run()
		with self.as_user(self.second_member):
			first = history(self.community.name)
			last = history(self.community.name, start=40)
			self.assertTrue(first["has_more"])
			self.assertFalse(last["has_more"])
			self.assertEqual(len(first["items"]), 40)
			self.assertEqual(len(last["items"]), 5)
			names = [row.name for row in first["items"] + last["items"]]
			self.assertEqual(names, sorted(set(names), reverse=True))
			self.assertEqual(history(self.community.name, start=-10), first)

	def test_invalid_filters_are_rejected(self):
		for filters in ({"kind": "file"}, {"target": "untyped"}, {"target": ["!=", ""]}):
			with self.subTest(filters=filters), self.assertRaises((frappe.ValidationError, TypeError)):
				history(self.community.name, **filters)
