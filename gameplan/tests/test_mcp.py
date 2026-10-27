import frappe

from gameplan.mcp import AGENT_INSTRUCTIONS, add_agent_instructions
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
		add_agent_instructions()
		self.assertEqual(self.get_instructions(), AGENT_INSTRUCTIONS)

	def test_keeps_existing_instructions_and_adds_gameplan_once(self):
		self.set_instructions("Frappe CRM tracks sales.")
		add_agent_instructions()
		add_agent_instructions()
		self.assertEqual(self.get_instructions(), f"Frappe CRM tracks sales.\n\n{AGENT_INSTRUCTIONS}")
