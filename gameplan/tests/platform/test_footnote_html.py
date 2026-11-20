# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""The stored HTML contract for editor footnotes.

A footnote is saved as a marker in the text, `<sup data-type="footnote-reference"
data-id="…">1</sup>`, and a note in one list after the last block, `<ol
data-type="footnotes"><li data-type="footnote" data-id="…"><p>…</p></li></ol>`.
The editor pairs a marker with its note through `data-id`, so a dropped `data-id`
or `data-type` fails silently: the marker loses its note and the editor makes a
new, empty one on the next edit.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_comment, create_community, create_discussion, create_space
from gameplan.utils.sanitizer import sanitize_content

FOOTNOTES = (
	'<p>Ship on Friday<sup data-id="a1" data-type="footnote-reference">1</sup> '
	'after review<sup data-id="b2" data-type="footnote-reference">2</sup></p>'
	'<ol data-type="footnotes">'
	'<li data-id="a1" data-type="footnote"><p>Unless it is a <strong>holiday</strong>.</p></li>'
	'<li data-id="b2" data-type="footnote"><p>Two approvals.</p></li>'
	"</ol>"
)


class TestFootnoteSanitization(FrappeTestCase):
	def test_footnotes_survive_unchanged(self):
		self.assertEqual(sanitize_content(FOOTNOTES), FOOTNOTES)

	def test_script_inside_a_note_is_still_neutralized(self):
		html = (
			'<ol data-type="footnotes"><li data-id="a1" data-type="footnote">'
			"<p>t<script>alert(1)</script></p></li></ol>"
		)
		self.assertNotIn("<script>", sanitize_content(html))

	def test_event_handler_on_a_marker_is_stripped(self):
		html = '<p>x<sup data-id="a1" data-type="footnote-reference" onclick="alert(1)">1</sup></p>'
		self.assertNotIn("onclick", sanitize_content(html))


class TestFootnoteRoundTrip(GameplanTestCase):
	def setUp(self):
		super().setUp()
		community = create_community("Footnote Community")
		self.space = create_space("Footnote Space", community)

	def test_discussion_keeps_its_footnotes(self):
		discussion = create_discussion("With footnotes", self.space, content=FOOTNOTES)
		self.assertEqual(frappe.db.get_value("GP Discussion", discussion.name, "content"), FOOTNOTES)

	def test_comment_keeps_its_footnotes(self):
		discussion = create_discussion("With a footnoted reply", self.space)
		comment = create_comment(discussion, content=FOOTNOTES)
		self.assertEqual(frappe.db.get_value("GP Comment", comment.name, "content"), FOOTNOTES)
