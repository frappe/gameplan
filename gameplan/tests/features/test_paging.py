import frappe

from gameplan.approvals import queue
from gameplan.paging import MAX_START, page_start
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community


class TestPaging(GameplanTestCase):
	def test_negative_and_text_offsets_start_at_the_top_and_deep_ones_are_refused(self):
		self.assertEqual((page_start(-5), page_start("40"), page_start(MAX_START)), (0, 40, MAX_START))
		with self.assertRaisesRegex(frappe.ValidationError, "too far back"):
			page_start(MAX_START + 1)

	def test_a_moderator_queue_refuses_a_deep_offset(self):
		community = create_community("Deep", admins=[self.member])
		with self.as_user(self.member), self.assertRaises(frappe.ValidationError):
			queue(community.name, start=MAX_START + 1)
