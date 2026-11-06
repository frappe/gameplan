import frappe

from gameplan.patches.add_scale_indexes import execute
from gameplan.tests.base import GameplanTestCase

INDEXES = [
	("tabGP Member", "parent_user"),
	("tabGP Unread Record", "discussion_records"),
	("tabGP Comment", "thread_replies"),
	("tabGP Comment", "hidden_replies"),
	("tabGP Comment", "spam_removed_replies"),
	("tabGP Discussion", "author_discussions"),
	("tabGP Discussion", "hidden_discussions"),
	("tabGP Discussion", "spam_removed_discussions"),
	("tabGP Notification", "discussion_notifications"),
	("tabGP Notification", "comment_notifications"),
]


class TestScaleIndexes(GameplanTestCase):
	def test_the_patch_creates_every_index_and_can_run_twice(self):
		execute()
		execute()
		missing = [index for index in INDEXES if not frappe.db.has_index(*index)]
		self.assertEqual(missing, [])
