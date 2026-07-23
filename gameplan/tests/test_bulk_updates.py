# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Characterization tests for the bulk-update perf refactors (B4, B5).

These lock the observable behavior of endpoints that were rewritten from N+1
get_doc/save loops into single qb.update statements. They must pass both before
and after the refactor — the point is that the faster path produces identical
results.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.api import mark_all_notifications_as_read
from gameplan.tests.fixtures import create_community, create_member, create_space


def _make_notification(to_user, read=0):
	return frappe.get_doc(doctype="GP Notification", to_user=to_user, type="Mention", read=read).insert(
		ignore_permissions=True
	)


class TestBulkUpdates(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_mark_all_notifications_as_read(self):
		user = create_member("bulk_notif_user@example.com")
		_make_notification(user.name, read=0)
		_make_notification(user.name, read=0)

		frappe.set_user(user.name)
		mark_all_notifications_as_read()

		unread = frappe.db.count("GP Notification", {"to_user": user.name, "read": 0})
		self.assertEqual(unread, 0)

	def test_clear_notifications_marks_matching_rows_read(self):
		user = create_member("bulk_clear_user@example.com")
		team = create_community("Bulk Clear Team")
		project = create_space("Bulk Clear Space", team.name)
		discussion = frappe.get_doc(
			doctype="GP Discussion", title="Clear D1", project=project.name, content="x"
		).insert(ignore_permissions=True)
		matching = frappe.get_doc(
			doctype="GP Notification",
			to_user=user.name,
			type="Mention",
			discussion=discussion.name,
			read=0,
		).insert(ignore_permissions=True)
		unrelated = _make_notification(user.name, read=0)

		frappe.get_doc("GP Notification", matching.name).clear_notifications(
			discussion=discussion.name, user=user.name
		)

		# Only the discussion-scoped row is cleared; the unrelated one stays unread.
		self.assertEqual(frappe.db.get_value("GP Notification", matching.name, "read"), 1)
		self.assertEqual(frappe.db.get_value("GP Notification", unrelated.name, "read"), 0)

	def test_move_to_team_repoints_discussions_and_tasks(self):
		source = create_community("Bulk Source Team")
		target = create_community("Bulk Target Team")
		project = create_space("Bulk Move Space", source.name)
		discussion = frappe.get_doc(
			doctype="GP Discussion", title="D1", project=project.name, content="x"
		).insert(ignore_permissions=True)
		task = frappe.get_doc(doctype="GP Task", title="T1", project=project.name).insert(
			ignore_permissions=True
		)

		# Inserting child docs bumps the project's modified timestamp via counter
		# hooks; reload so move_to_team's save sees the latest (as a fresh API call would).
		project.reload()
		project.move_to_team(target.name)

		self.assertEqual(frappe.db.get_value("GP Project", project.name, "team"), target.name)
		self.assertEqual(frappe.db.get_value("GP Discussion", discussion.name, "team"), target.name)
		self.assertEqual(frappe.db.get_value("GP Task", task.name, "team"), target.name)
