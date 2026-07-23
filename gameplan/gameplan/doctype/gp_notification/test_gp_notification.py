# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.gameplan.doctype.gp_notification.gp_notification import GPNotification
from gameplan.tests.fixtures import create_community, create_discussion, create_member, create_space


class TestGPNotification(FrappeTestCase):
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
		matching = frappe.get_doc(
			doctype="GP Notification",
			to_user=user.name,
			type="Mention",
			discussion=discussion.name,
			read=0,
		).insert(ignore_permissions=True)
		unrelated = frappe.get_doc(
			doctype="GP Notification",
			to_user=user.name,
			type="Mention",
			discussion="",
			comment=comment.name,
			read=0,
		).insert(ignore_permissions=True)

		GPNotification.clear_notifications(discussion=discussion.name, user=user.name)

		self.assertEqual(frappe.db.get_value("GP Notification", matching.name, "read"), 1)
		self.assertEqual(frappe.db.get_value("GP Notification", unrelated.name, "read"), 0)
