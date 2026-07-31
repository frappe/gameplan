# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Per-user state is private to its user.

Four doctypes hold state that belongs to exactly one person:

- **GP Notification** — the bell feed. `to_user` owns the row; `owner` is whoever
  *triggered* it (the mentioner), so ownership and readership differ here.
- **GP Project Visit** — per-user last-visit / "mark all read" watermark for a Space.
- **GP Discussion Visit** — per-user last-visit for a discussion.
- **GP Pinned Project** — the Spaces one user has pinned to their own sidebar, and
  the order they sit in.

All four grant Gameplan Member and Gameplan Guest read, write and (for pins) delete
with `if_owner` unset, so role permissions alone let any signed-in user reach any other
user's row through the generic `/api/v2/document/<doctype>` API. The invariant pinned
here is: you can read, list, write and delete **your own** rows and nobody else's —
while every server-side writer (a mention creating a notification *for* someone,
`track_visit`, `mark_all_as_read`, the unread-record backfill, `GPProject.archive`
clearing the whole site's pins) keeps working, because those run with
`ignore_permissions` and must not be caught by the fix.

The list assertions go through `frappe.qb.get_query(..., ignore_permissions=False)`
because that is literally what `frappe/api/v2.py::document_list` runs. `if_owner` on
the role row would not cover this doctype set at all: for GP Notification the owner is
the sender, not the recipient, and the demo seeder inserts visit and pin rows *for*
another user while running as Administrator.
"""

import frappe

from gameplan import per_user_state
from gameplan.api import mark_all_notifications_as_read
from gameplan.gameplan.doctype.gp_notification.gp_notification import GPNotification
from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_space


def list_as_client(doctype, **filters):
	"""Enumerate `doctype` exactly the way `/api/v2/document/<doctype>` does."""
	return frappe.qb.get_query(
		doctype,
		fields=["name"],
		filters=filters,
		ignore_permissions=False,
	).run(pluck="name")


class PerUserStateTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Acme", members=[self.member, self.second_member])
		self.space = create_space("Engineering", self.community)
		self.discussion = create_discussion("Roadmap", self.space, owner=self.member)


class TestNotificationPrivacy(PerUserStateTestCase):
	def setUp(self):
		super().setUp()
		# Inserted as the second member so `owner` is deliberately NOT `to_user`: this is
		# the real shape of a mention notification, and the reason `if_owner` cannot work.
		with self.as_user(self.second_member):
			self.notification = frappe.get_doc(
				doctype="GP Notification",
				to_user=self.member.name,
				type="Mention",
				message="Second Member mentioned you",
				discussion=self.discussion.name,
			).insert(ignore_permissions=True)

	def test_recipient_can_read_own_notification(self):
		self.assert_allowed(self.notification, "read", self.member)

	def test_recipient_can_list_own_notification(self):
		with self.as_user(self.member):
			self.assertIn(self.notification.name, list_as_client("GP Notification"))

	def test_recipient_can_mark_own_notification_read(self):
		with self.as_user(self.member):
			doc = frappe.get_doc("GP Notification", self.notification.name)
			doc.read = 1
			doc.save()
		self.assertEqual(frappe.db.get_value("GP Notification", self.notification.name, "read"), 1)

	def test_sender_cannot_read_notification_they_triggered(self):
		# The mentioner created the row, so `owner` is theirs — but the notification is
		# addressed to someone else and must stay out of their bell feed.
		self.assert_not_allowed(self.notification, "read", self.second_member)

	def test_other_user_cannot_read_notification(self):
		self.assert_not_allowed(self.notification, "read", self.outsider)

	def test_other_user_cannot_list_notification(self):
		with self.as_user(self.outsider):
			self.assertNotIn(self.notification.name, list_as_client("GP Notification"))

	def test_other_user_cannot_mark_notification_read(self):
		with self.as_user(self.outsider):
			doc = frappe.get_doc("GP Notification", self.notification.name)
			doc.read = 1
			with self.assertRaises(frappe.PermissionError):
				doc.save()
		self.assertEqual(frappe.db.get_value("GP Notification", self.notification.name, "read"), 0)

	def test_user_cannot_create_notification_addressed_to_someone_else(self):
		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				doctype="GP Notification",
				to_user=self.member.name,
				type="Mention",
				message="Forged",
			).insert()

	def test_mention_still_creates_notification_for_the_mentioned_user(self):
		mention = (
			f'<p>Hi <span data-type="mention" data-id="{self.second_member.name}" '
			'data-label="Second Member">@Second Member</span></p>'
		)
		with self.as_user(self.member):
			create_discussion("Mentioning", self.space, content=mention)
		self.assertTrue(
			frappe.db.exists("GP Notification", {"to_user": self.second_member.name, "type": "Mention"})
		)

	def test_clear_notifications_still_marks_own_rows_read(self):
		with self.as_user(self.member):
			GPNotification.clear_notifications(discussion=self.discussion.name)
		self.assertEqual(frappe.db.get_value("GP Notification", self.notification.name, "read"), 1)

	def test_mark_all_notifications_as_read_still_works(self):
		with self.as_user(self.member):
			mark_all_notifications_as_read()
		self.assertEqual(frappe.db.get_value("GP Notification", self.notification.name, "read"), 1)


class TestProjectVisitPrivacy(PerUserStateTestCase):
	def setUp(self):
		super().setUp()
		self.visit = frappe.get_doc(
			doctype="GP Project Visit",
			user=self.member.name,
			project=self.space.name,
			last_visit=frappe.utils.now(),
		).insert(ignore_permissions=True)

	def test_owner_can_read_own_visit(self):
		self.assert_allowed(self.visit, "read", self.member)

	def test_owner_can_list_own_visit(self):
		with self.as_user(self.member):
			self.assertIn(self.visit.name, list_as_client("GP Project Visit"))

	def test_other_member_cannot_read_visit(self):
		self.assert_not_allowed(self.visit, "read", self.second_member)

	def test_other_member_cannot_list_visit(self):
		with self.as_user(self.second_member):
			self.assertNotIn(self.visit.name, list_as_client("GP Project Visit"))

	def test_other_member_cannot_rewrite_visit(self):
		with self.as_user(self.second_member):
			doc = frappe.get_doc("GP Project Visit", self.visit.name)
			doc.mark_all_read_at = frappe.utils.now()
			with self.assertRaises(frappe.PermissionError):
				doc.save()
		self.assertIsNone(
			frappe.db.get_value("GP Project Visit", self.visit.name, "mark_all_read_at"),
		)

	def test_user_cannot_create_visit_for_someone_else(self):
		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				doctype="GP Project Visit",
				user=self.outsider.name,
				project=self.space.name,
				last_visit=frappe.utils.now(),
			).insert()

	def test_track_visit_still_records_the_session_user(self):
		with self.as_user(self.second_member):
			frappe.get_doc("GP Project", self.space.name).track_visit()
		self.assertTrue(
			frappe.db.exists(
				"GP Project Visit", {"user": self.second_member.name, "project": self.space.name}
			)
		)

	def test_mark_all_as_read_still_writes_the_watermark(self):
		with self.as_user(self.second_member):
			frappe.get_doc("GP Project", self.space.name).mark_all_as_read()
		self.assertIsNotNone(
			frappe.db.get_value(
				"GP Project Visit",
				{"user": self.second_member.name, "project": self.space.name},
				"mark_all_read_at",
			)
		)

	def test_deleting_a_space_still_takes_every_users_visit_row(self):
		# A cascade delete legitimately removes other people's rows: the parent delete is
		# authorised once and its children go with it.
		with self.as_user(self.admin):
			frappe.delete_doc("GP Project", self.space.name)
		self.assertFalse(frappe.db.exists("GP Project Visit", self.visit.name))

	def test_unread_record_backfill_still_creates_visits_for_a_user(self):
		# Runs as Administrator on behalf of another user — a legitimate cross-user writer.
		now = frappe.utils.now()
		GPUnreadRecord.create_project_visits([self.space.name], self.outsider.name, now, now)
		self.assertTrue(
			frappe.db.exists("GP Project Visit", {"user": self.outsider.name, "project": self.space.name})
		)


class TestDiscussionVisitPrivacy(PerUserStateTestCase):
	def setUp(self):
		super().setUp()
		self.visit = frappe.get_doc(
			doctype="GP Discussion Visit",
			user=self.member.name,
			discussion=self.discussion.name,
			last_visit=frappe.utils.now(),
		).insert(ignore_permissions=True)

	def test_owner_can_read_own_visit(self):
		self.assert_allowed(self.visit, "read", self.member)

	def test_owner_can_list_own_visit(self):
		with self.as_user(self.member):
			self.assertIn(self.visit.name, list_as_client("GP Discussion Visit"))

	def test_other_member_cannot_read_visit(self):
		self.assert_not_allowed(self.visit, "read", self.second_member)

	def test_other_member_cannot_list_visit(self):
		with self.as_user(self.second_member):
			self.assertNotIn(self.visit.name, list_as_client("GP Discussion Visit"))

	def test_other_member_cannot_rewrite_visit(self):
		original = frappe.db.get_value("GP Discussion Visit", self.visit.name, "last_visit")
		with self.as_user(self.second_member):
			doc = frappe.get_doc("GP Discussion Visit", self.visit.name)
			doc.last_visit = "2000-01-01 00:00:00"
			with self.assertRaises(frappe.PermissionError):
				doc.save()
		self.assertEqual(frappe.db.get_value("GP Discussion Visit", self.visit.name, "last_visit"), original)

	def test_user_cannot_create_visit_for_someone_else(self):
		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				doctype="GP Discussion Visit",
				user=self.outsider.name,
				discussion=self.discussion.name,
				last_visit=frappe.utils.now(),
			).insert()

	def test_deleting_a_discussion_still_takes_every_readers_visit_row(self):
		# The discussion owner deletes their thread; this visit row belongs to someone
		# else, and the cascade must still be allowed to remove it.
		other = frappe.get_doc(
			doctype="GP Discussion Visit",
			user=self.second_member.name,
			discussion=self.discussion.name,
			last_visit=frappe.utils.now(),
		).insert(ignore_permissions=True)

		with self.as_user(self.member):
			frappe.delete_doc("GP Discussion", self.discussion.name)

		self.assertFalse(frappe.db.exists("GP Discussion Visit", other.name))

	def test_track_visit_still_records_the_session_user(self):
		with self.as_user(self.second_member):
			frappe.get_doc("GP Discussion", self.discussion.name).track_visit()
		self.assertTrue(
			frappe.db.exists(
				"GP Discussion Visit",
				{"user": self.second_member.name, "discussion": self.discussion.name},
			)
		)


class TestPinnedProjectPrivacy(PerUserStateTestCase):
	"""A pin is one person's own sidebar shortcut to a Space.

	Unlike the visit doctypes this one also grants `delete` to Gameplan Member and
	Gameplan Guest, and delete is how unpinning works — there is no unpin endpoint, the
	SPA removes the row through the generic document API. So the delete grant has to
	stay, and the hook is the only thing standing between it and someone else's sidebar.
	"""

	def setUp(self):
		super().setUp()
		self.pin = self.pin_as(self.member)

	def pin_as(self, user):
		"""Pin `self.space` as `user`.

		`GPPinnedProject.before_insert` stamps `user` with the session user, so who is
		logged in decides whose pin this is — there is no field to pass.
		"""
		with self.as_user(user):
			return frappe.get_doc(doctype="GP Pinned Project", project=self.space.name).insert(
				ignore_permissions=True
			)

	def test_owner_can_read_own_pin(self):
		self.assert_allowed(self.pin, "read", self.member)

	def test_owner_can_list_own_pin(self):
		with self.as_user(self.member):
			self.assertIn(self.pin.name, list_as_client("GP Pinned Project"))

	def test_owner_can_reorder_own_pin(self):
		with self.as_user(self.member):
			doc = frappe.get_doc("GP Pinned Project", self.pin.name)
			doc.order = 5
			doc.save()
		self.assertEqual(frappe.db.get_value("GP Pinned Project", self.pin.name, "order"), 5)

	def test_owner_can_unpin_by_deleting_own_pin(self):
		with self.as_user(self.member):
			frappe.delete_doc("GP Pinned Project", self.pin.name)
		self.assertFalse(frappe.db.exists("GP Pinned Project", self.pin.name))

	def test_other_member_cannot_read_pin(self):
		self.assert_not_allowed(self.pin, "read", self.second_member)

	def test_other_member_cannot_list_pin(self):
		with self.as_user(self.second_member):
			self.assertNotIn(self.pin.name, list_as_client("GP Pinned Project"))

	def test_other_member_cannot_reorder_pin(self):
		with self.as_user(self.second_member):
			doc = frappe.get_doc("GP Pinned Project", self.pin.name)
			doc.order = 99
			with self.assertRaises(frappe.PermissionError):
				doc.save()
		self.assertEqual(frappe.db.get_value("GP Pinned Project", self.pin.name, "order"), 1)

	def test_other_member_cannot_unpin_someone_elses_pin(self):
		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("GP Pinned Project", self.pin.name)
		self.assertTrue(frappe.db.exists("GP Pinned Project", self.pin.name))

	def test_guest_cannot_read_pin(self):
		self.assert_not_allowed(self.pin, "read", self.guest)

	def test_guest_cannot_list_pin(self):
		with self.as_user(self.guest):
			self.assertNotIn(self.pin.name, list_as_client("GP Pinned Project"))

	def test_guest_cannot_unpin_someone_elses_pin(self):
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("GP Pinned Project", self.pin.name)
		self.assertTrue(frappe.db.exists("GP Pinned Project", self.pin.name))

	def test_pinning_a_space_still_works_without_ignore_permissions(self):
		"""The create check runs *before* `before_insert`, i.e. before `user` is stamped.

		A create rule that judged the unstamped row would deny every legitimate pin, so
		this is the regression guard on the carve-out in `pinned_project_has_permission`.
		"""
		with self.as_user(self.second_member):
			pin = frappe.get_doc(doctype="GP Pinned Project", project=self.space.name).insert()
		self.assertEqual(pin.user, self.second_member.name)

	def test_archiving_a_space_still_clears_every_users_pin(self):
		other_pin = self.pin_as(self.second_member)

		with self.as_user(self.admin):
			frappe.get_doc("GP Project", self.space.name).archive()

		self.assertFalse(frappe.db.exists("GP Pinned Project", self.pin.name))
		self.assertFalse(frappe.db.exists("GP Pinned Project", other_pin.name))

	def test_deleting_a_space_still_takes_every_users_pin(self):
		other_pin = self.pin_as(self.second_member)

		with self.as_user(self.admin):
			frappe.delete_doc("GP Project", self.space.name)

		self.assertFalse(frappe.db.exists("GP Pinned Project", self.pin.name))
		self.assertFalse(frappe.db.exists("GP Pinned Project", other_pin.name))


class TestPerUserStateHooksAreRegistered(PerUserStateTestCase):
	"""The doctypes' role rows are open by design; the hooks are what closes them."""

	DOCTYPES = ["GP Notification", "GP Project Visit", "GP Discussion Visit", "GP Pinned Project"]

	def test_every_per_user_doctype_has_a_query_conditions_hook(self):
		hooks = frappe.get_hooks("permission_query_conditions")
		for doctype in self.DOCTYPES:
			self.assertTrue(hooks.get(doctype), f"{doctype} has no permission_query_conditions hook")

	def test_every_per_user_doctype_has_a_has_permission_hook(self):
		hooks = frappe.get_hooks("has_permission")
		for doctype in self.DOCTYPES:
			self.assertTrue(hooks.get(doctype), f"{doctype} has no has_permission hook")

	def test_has_permission_hooks_return_a_hard_false_for_another_users_row(self):
		"""`assertIs` on purpose: a hook that returned `None` would read as "no opinion"
		to some callers and as a denial to `assertFalse`, hiding a return-none regression."""
		visit = frappe.get_doc(
			doctype="GP Project Visit",
			user=self.member.name,
			project=self.space.name,
			last_visit=frappe.utils.now(),
		).insert(ignore_permissions=True)

		self.assertIs(
			per_user_state.project_visit_has_permission(visit, "read", self.second_member.name), False
		)
		self.assertIs(per_user_state.project_visit_has_permission(visit, "read", self.member.name), True)
