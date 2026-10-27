import frappe

from gameplan.mcp import AGENT_INSTRUCTIONS, AGENT_INSTRUCTIONS_HEADING, sync_agent_instructions
from gameplan.tests.base import GameplanTestCase


class TestAgentInstructions(GameplanTestCase):
	def setUp(self):
		super().setUp()
		if not frappe.get_meta("System Settings").has_field("agent_instructions"):
			self.skipTest("This Frappe version has no MCP agent instructions")

	def set_instructions(self, value):
		frappe.db.set_single_value("System Settings", "agent_instructions", value)

	def get_instructions(self):
		return frappe.db.get_single_value("System Settings", "agent_instructions")

	def test_fills_empty_instructions(self):
		self.set_instructions("")
		sync_agent_instructions()
		self.assertEqual(self.get_instructions(), AGENT_INSTRUCTIONS)

	def test_replaces_outdated_gameplan_block_and_keeps_admin_text(self):
		outdated = f"{AGENT_INSTRUCTIONS_HEADING}\n- An old rule."
		self.set_instructions(f"Frappe CRM tracks sales.\n\n{outdated}\n\nAlways answer in English.")
		sync_agent_instructions()
		sync_agent_instructions()
		self.assertEqual(
			self.get_instructions(),
			f"Frappe CRM tracks sales.\n\n{AGENT_INSTRUCTIONS}\n\nAlways answer in English.",
		)
