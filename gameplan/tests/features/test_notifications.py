# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Notification behaviour: clearing scoped rows and marking everything read."""

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.api import mark_all_notifications_as_read
from gameplan.gameplan.doctype.gp_notification.gp_notification import GPNotification
from gameplan.tests.fixtures import create_community, create_discussion, create_member, create_space


def _make_notification(to_user, **kwargs):
	return frappe.get_doc(doctype="GP Notification", to_user=to_user, type="Mention", **kwargs).insert(
		ignore_permissions=True
	)


class TestNotifications(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_clear_notifications_handles_empty_link_values_for_autoincrement_names(self):
		user = create_member("test_notification_empty_link@example.com")
		team = create_community("Notification Empty Link Team")
		project = create_space("Notification Empty Link Space", team.name)
		discussion = create_discussion("Notification Empty Link Discussion", project.name)
		comment = frappe.get_doc(
			doctype="GP Comment",
			reference_doctype="GP Discussion",
			reference_name=discussion.name,
			content="Unrelated notification",
		).insert(ignore_permissions=True)
		matching = _make_notification(user.name, discussion=discussion.name, read=0)
		unrelated = _make_notification(user.name, discussion="", comment=comment.name, read=0)

		GPNotification.clear_notifications(discussion=discussion.name, user=user.name)

		self.assertEqual(frappe.db.get_value("GP Notification", matching.name, "read"), 1)
		self.assertEqual(frappe.db.get_value("GP Notification", unrelated.name, "read"), 0)

	def test_clear_notifications_marks_matching_rows_read(self):
		user = create_member("bulk_clear_user@example.com")
		team = create_community("Bulk Clear Team")
		project = create_space("Bulk Clear Space", team.name)
		discussion = create_discussion("Clear D1", project.name, content="x")
		matching = _make_notification(user.name, discussion=discussion.name, read=0)
		unrelated = _make_notification(user.name, read=0)

		frappe.get_doc("GP Notification", matching.name).clear_notifications(
			discussion=discussion.name, user=user.name
		)

		# Only the discussion-scoped row is cleared; the unrelated one stays unread.
		self.assertEqual(frappe.db.get_value("GP Notification", matching.name, "read"), 1)
		self.assertEqual(frappe.db.get_value("GP Notification", unrelated.name, "read"), 0)

	def test_mark_all_notifications_as_read(self):
		user = create_member("bulk_notif_user@example.com")
		_make_notification(user.name, read=0)
		_make_notification(user.name, read=0)

		frappe.set_user(user.name)
		mark_all_notifications_as_read()

		unread = frappe.db.count("GP Notification", {"to_user": user.name, "read": 0})
		self.assertEqual(unread, 0)
