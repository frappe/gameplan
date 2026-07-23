# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""What a guest can reach.

A guest never joins a community; their access is exactly the spaces they were
explicitly granted. What a guest may DO inside a granted space is the guest
participation policy, specced in features/test_guest_participation.py.
"""

from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_space, grant_guest_access


class TestGuestAccess(GameplanTestCase):
	def test_guest_sees_only_explicitly_granted_spaces(self):
		community = create_community("Guest Space Community", members=[self.member])
		public_space = create_space("Guest Public Space", community)
		granted_space = create_space("Guest Granted Space", community, is_private=1)
		grant_guest_access(self.guest, granted_space)

		# A public space is still invisible: guests get grants, not community membership.
		self.assert_not_allowed(public_space, "read", self.guest)
		self.assert_allowed(granted_space, "read", self.guest)
