# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""The stored HTML contract for editor collapsible sections.

A collapsible section is saved as `<details open><summary>title</summary><div
data-type="collapsible-content">…</div></details>`. Every part of that shape has
to survive sanitization and a real save, because each one fails silently if it
does not: a dropped `<summary>` loses the title, a dropped `open` reopens every
collapsed section on reload, and a dropped `data-type` leaves the body outside
the node so the section can no longer close.

The tags come from frappe's `acceptable_elements`, so these tests also pin a
dependency contract: if a future frappe drops `details`, `summary` or the `open`
attribute, this fails here instead of quietly mangling saved documents.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_space
from gameplan.utils.sanitizer import sanitize_content

OPEN_SECTION = (
	"<details open><summary>Deploy steps</summary>"
	'<div data-type="collapsible-content"><p>ssh in</p></div></details>'
)

CLOSED_SECTION = (
	"<details><summary>Deploy steps</summary>"
	'<div data-type="collapsible-content"><p>ssh in</p></div></details>'
)


class TestCollapsibleSanitization(FrappeTestCase):
	def test_open_section_survives_unchanged(self):
		self.assertEqual(sanitize_content(OPEN_SECTION), OPEN_SECTION)

	def test_closed_section_keeps_its_collapsed_state(self):
		# The absence of `open` is the closed state, so an added attribute is as
		# wrong as a dropped one.
		self.assertEqual(sanitize_content(CLOSED_SECTION), CLOSED_SECTION)

	def test_title_marks_are_kept(self):
		html = (
			"<details open><summary>Deploy <strong>now</strong></summary>"
			'<div data-type="collapsible-content"><p>ssh in</p></div></details>'
		)
		self.assertEqual(sanitize_content(html), html)

	def test_nested_section_survives(self):
		html = (
			"<details open><summary>Outer</summary>"
			f'<div data-type="collapsible-content">{OPEN_SECTION}</div></details>'
		)
		self.assertEqual(sanitize_content(html), html)

	def test_script_inside_a_title_is_still_neutralized(self):
		# Allowing the tag must not open a hole inside it.
		out = sanitize_content("<details open><summary>t<script>alert(1)</script></summary></details>")
		self.assertNotIn("<script>", out)

	def test_event_handler_on_a_section_is_stripped(self):
		out = sanitize_content('<details open onclick="alert(1)"><summary>t</summary></details>')
		self.assertNotIn("onclick", out)


class TestCollapsibleRoundTrip(GameplanTestCase):
	def setUp(self):
		super().setUp()
		community = create_community("Collapsible Community")
		self.space = create_space("Collapsible Space", community)

	def _reloaded_content(self, discussion):
		return frappe.db.get_value("GP Discussion", discussion.name, "content")

	def test_discussion_keeps_an_open_section(self):
		discussion = create_discussion("With a section", self.space, content=OPEN_SECTION)
		self.assertEqual(self._reloaded_content(discussion), OPEN_SECTION)

	def test_discussion_keeps_a_closed_section(self):
		discussion = create_discussion("With a closed section", self.space, content=CLOSED_SECTION)
		self.assertEqual(self._reloaded_content(discussion), CLOSED_SECTION)

	def test_editing_a_discussion_keeps_the_section(self):
		# validate() and before_save() both sanitize, so a second save is a second
		# pass over already-sanitized content — it must be a fixed point.
		discussion = create_discussion("Edited", self.space, content=OPEN_SECTION)
		discussion.content = CLOSED_SECTION
		discussion.save(ignore_permissions=True)
		self.assertEqual(self._reloaded_content(discussion), CLOSED_SECTION)
