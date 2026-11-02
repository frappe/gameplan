from unittest.mock import patch

import frappe

from gameplan.moderation import removed_content
from gameplan.permissions import can_view_content, users_who_can_view_content
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_comment, create_community, create_discussion, create_space
from gameplan.visibility import VISIBILITY_ANONYMOUS, VISIBILITY_MEMBER_ACCESS


class TestModerationAudienceScaling(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.enterContext(patch.dict(frappe.conf, gameplan_public_access_enabled=1, gameplan_demo_enabled=0))
		self.community = create_community(
			"Moderated audience", visibility=VISIBILITY_ANONYMOUS, members=[self.member, self.second_member]
		)
		self.community.set_member_moderator(self.second_member.name, 1)
		self.space = create_space("Public audience", self.community, visibility=VISIBILITY_ANONYMOUS)
		self.discussion = create_discussion("Audience target", self.space, owner=self.member)
		self.reply = create_comment(self.discussion, content="Original reply", owner=self.member)

	def assert_audience_matches_scalar(self, doc):
		doc.reload()
		users = [
			self.member.name,
			self.second_member.name,
			self.outsider.name,
			self.admin.name,
			self.guest.name,
			"Guest",
			"Administrator",
		]
		expected = [user for user in users if can_view_content(user, doc)]
		self.assertEqual(users_who_can_view_content(users, doc), expected)

	def test_removed_reply_and_parent_discussion_audiences_are_moderator_only(self):
		with self.as_user(self.second_member):
			self.reply.hide("Hidden reply")
		self.assert_audience_matches_scalar(self.reply)
		with self.as_user(self.second_member):
			self.reply.restore()
			self.discussion.delete_spam("Removed parent")
		self.assert_audience_matches_scalar(self.discussion)
		self.assert_audience_matches_scalar(self.reply)

	def test_system_manager_with_guest_only_role_cannot_moderate_removed_content(self):
		self.guest.add_roles("System Manager")
		self.reply.hide("Hidden reply")
		self.assert_audience_matches_scalar(self.reply)

	def test_removed_queue_scope_has_bounded_role_reads_and_keeps_private_spaces_private(self):
		for index in range(20):
			create_space(f"Queue scale {index}", self.community)
		private = create_space(
			"Restricted queue", self.community, visibility=VISIBILITY_MEMBER_ACCESS, members=[self.member]
		)
		private_post = create_discussion("Restricted target", private, owner=self.member)
		private_post.hide("Restricted")
		with (
			self.as_user(self.second_member),
			patch.object(frappe, "get_roles", wraps=frappe.get_roles) as roles,
		):
			self.assertEqual(removed_content(self.community.name)["items"], [])
		self.assertLessEqual(roles.call_count, 10)

	def test_reaction_rechecks_removal_after_locking(self):
		get_doc = frappe.get_doc
		removed = False

		def locked_doc(doctype, name=None, *args, **kwargs):
			nonlocal removed
			if (
				doctype == "GP Discussion"
				and str(name) == str(self.discussion.name)
				and kwargs.get("for_update")
			):
				frappe.db.set_value(doctype, name, "hidden_at", frappe.utils.now())
				removed = True
			return get_doc(doctype, name, *args, **kwargs)

		with (
			patch.object(frappe, "get_doc", side_effect=locked_doc),
			self.assertRaises(frappe.PermissionError),
		):
			self.discussion.react([{"emoji": "👍", "operation": "add"}])
		self.assertTrue(removed)
		self.assertFalse(
			frappe.db.exists(
				"GP Reaction",
				{"reference_doctype": "GP Discussion", "reference_name": str(self.discussion.name)},
			)
		)

	def test_active_ban_pages_exclude_lifted_bans_and_bound_results(self):
		from gameplan.moderation import community_bans

		now = frappe.utils.now()
		for index in range(45):
			for action in ["Ban", "Unban"] if index == 0 else ["Ban"]:
				log = frappe.get_doc(
					doctype="GP Moderation Log",
					community=self.community.name,
					user=f"banned-{index}@example.test",
					action=action,
					reason="Test history",
				).insert(ignore_permissions=True, ignore_links=True)
				frappe.db.set_value(
					"GP Moderation Log",
					log.name,
					"creation",
					frappe.utils.add_to_date(now, seconds=1) if action == "Unban" else now,
				)
		first = community_bans(self.community.name)
		second = community_bans(self.community.name, start=40)
		self.assertEqual(len(first), 41)
		self.assertEqual(len(second), 4)
		self.assertNotIn("banned-0@example.test", [row.user for row in first + second])

	def test_deleted_reply_rejects_reactions_even_for_staff(self):
		frappe.db.set_value("GP Comment", self.reply.name, "deleted_at", frappe.utils.now())
		with self.assertRaises(frappe.PermissionError):
			self.reply.react([{"emoji": "👍", "operation": "add"}])
