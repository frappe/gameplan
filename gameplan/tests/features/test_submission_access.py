from unittest.mock import patch

import frappe

from gameplan.approval_access import can_read_submission
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_space
from gameplan.visibility import VISIBILITY_MEMBER_ACCESS


class TestSubmissionAccess(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community(
			"Submissions", members=[self.member, self.second_member, self.outsider]
		)
		self.community.set_member_moderator(self.second_member.name, 1)
		self.space = create_space("Pending", self.community)

	def submission(self, **values):
		with self.as_user(self.member):
			return frappe.get_doc(
				doctype="GP Submission",
				project=self.space.name,
				content="Held words",
				request_key=frappe.generate_hash(),
				status="Pending",
				**values,
			).insert(ignore_permissions=True)

	def test_only_author_and_current_moderators_can_read_or_list_submissions(self):
		doc = self.submission()
		for user, allowed in (
			(self.member, True),
			(self.second_member, True),
			(self.outsider, False),
			(self.guest, False),
			("Guest", False),
		):
			with self.subTest(user=str(user)), self.as_user(user):
				self.assertEqual(bool(can_read_submission(doc)), allowed)
				if allowed:
					frappe.get_doc("GP Submission", doc.name).check_permission("read")
					self.assertEqual(
						frappe.get_list("GP Submission", filters={"name": doc.name}, pluck="name"), [doc.name]
					)
				else:
					with self.assertRaises(frappe.PermissionError):
						frappe.get_doc("GP Submission", doc.name).check_permission("read")
					if user == "Guest":
						with self.assertRaises(frappe.PermissionError):
							frappe.get_list("GP Submission", filters={"name": doc.name}, pluck="name")
					else:
						self.assertEqual(
							frappe.get_list("GP Submission", filters={"name": doc.name}, pluck="name"), []
						)

	def test_generic_create_edit_delete_and_shared_realtime_are_closed(self):
		for user in (self.member, self.second_member):
			with self.as_user(user), self.assertRaises(frappe.PermissionError):
				frappe.get_doc(
					doctype="GP Submission", project=self.space.name, content="Forged", request_key="forged"
				).insert()
		doc = self.submission()
		for action in (
			lambda: doc.save(ignore_permissions=True),
			lambda: doc.delete(ignore_permissions=True),
		):
			with self.assertRaises(frappe.PermissionError):
				action()
		with patch.object(frappe, "publish_realtime") as publish:
			doc.notify_update()
			publish.assert_not_called()

	def test_private_space_access_and_reply_moves_apply_to_both_read_paths(self):
		parent = create_discussion("Moving parent", self.space)
		doc = self.submission(discussion=parent.name)
		private = create_space(
			"Private submissions", self.community, visibility=VISIBILITY_MEMBER_ACCESS, members=[self.member]
		)
		parent.move_to_project(private.name)
		with self.as_user(self.second_member):
			self.assertFalse(can_read_submission(doc))
			self.assertEqual(frappe.get_list("GP Submission", filters={"name": doc.name}, pluck="name"), [])
		private.add_member(self.second_member.name)
		with self.as_user(self.second_member):
			self.assertTrue(can_read_submission(doc))
			self.assertEqual(
				frappe.get_list("GP Submission", filters={"name": doc.name}, pluck="name"), [doc.name]
			)

	def test_submission_does_not_create_posts_unreads_or_notifications(self):
		before = {
			dt: frappe.db.count(dt)
			for dt in ("GP Discussion", "GP Comment", "GP Poll", "GP Notification", "GP Unread Record")
		}
		doc = self.submission()
		for dt, count in before.items():
			self.assertEqual(frappe.db.count(dt), count)
		self.assertEqual(doc.status, "Pending")

	def test_private_attachments_follow_submission_access_and_cannot_be_republished(self):
		with self.as_user(self.member):
			file = frappe.get_doc(
				doctype="File", file_name="held.txt", content=b"Held bytes", is_private=1
			).save(ignore_permissions=True)
		with self.as_user(self.member):
			doc = frappe.get_doc(
				doctype="GP Submission",
				project=self.space.name,
				content=f'<a href="{file.file_url}">Attachment</a>',
				request_key=frappe.generate_hash(),
				status="Pending",
			).insert(ignore_permissions=True)
		file.reload()
		self.assertEqual(file.attached_to_name, doc.name)
		with self.as_user(self.outsider):
			with self.assertRaises(frappe.PermissionError):
				file.get_content()
			self.assertEqual(frappe.get_list("File", filters={"name": file.name}), [])
		with self.as_user(self.second_member):
			self.assertEqual(file.get_content(), b"Held bytes")
		with self.as_user(self.member):
			file.is_private = 0
			with self.assertRaises(frappe.PermissionError):
				file.save(ignore_permissions=True)
			file.reload()
			with self.assertRaises(frappe.PermissionError):
				file.delete(ignore_permissions=True)
			with self.assertRaises(frappe.PermissionError):
				file.create_attachment_copy("GP Draft", "other", ignore_permissions=True)

	def test_public_files_and_another_uploaders_files_are_rejected(self):
		for private, user in ((0, self.member), (1, self.outsider)):
			with self.as_user(user):
				file = frappe.get_doc(
					doctype="File", file_name=f"blocked-{private}.txt", content=b"Bytes", is_private=private
				).save(ignore_permissions=True)
			with (
				self.as_user(self.member),
				self.assertRaises((frappe.PermissionError, frappe.ValidationError)),
			):
				frappe.get_doc(
					doctype="GP Submission",
					project=self.space.name,
					content=f'<a href="{file.file_url}">File</a>',
					request_key=frappe.generate_hash(),
					status="Pending",
				).insert(ignore_permissions=True)

	def test_an_explicit_share_cannot_widen_the_submission_audience(self):
		doc = self.submission()
		frappe.share.add("GP Submission", doc.name, self.outsider.name, read=1, notify=0)
		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Submission", doc.name).check_permission("read")

	def test_parent_deletion_keeps_restricted_history_without_blocking_deletion(self):
		parent = create_discussion("Deleted parent", self.space)
		doc = self.submission(discussion=parent.name)
		frappe.delete_doc("GP Discussion", parent.name, ignore_permissions=True)
		self.assertTrue(frappe.db.exists("GP Submission", doc.name))
		with self.as_user(self.member):
			self.assertFalse(can_read_submission(doc))
			self.assertEqual(frappe.get_list("GP Submission", filters={"name": doc.name}, pluck="name"), [])
