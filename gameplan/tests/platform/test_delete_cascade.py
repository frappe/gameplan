# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

from gameplan.mixins.on_delete import delete_linked_records
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_space, grant_guest_access


class TestDeleteCascadeFlags(GameplanTestCase):
	def test_sibling_cascade_identifies_its_parent_doctype(self):
		community = create_community("Cascade Community", members=[self.member])
		space = create_space("Cascade Space", community)
		guest_access = grant_guest_access(self.guest, space)

		with patch("gameplan.mixins.on_delete.frappe.delete_doc") as delete_doc:
			delete_linked_records("User", self.guest.name, ["GP Guest Access"])

		delete_doc.assert_called_once_with(
			"GP Guest Access",
			guest_access.name,
			flags={"from_gameplan_delete_cascade": "User"},
		)
