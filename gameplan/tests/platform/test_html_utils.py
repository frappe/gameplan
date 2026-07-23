# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Tests for remove_empty_trailing_paragraphs.

Regression for a WYSIWYG mismatch: single line breaks (<br>) typed in the editor
were dropped on save, gluing adjacent lines together (e.g. "demo.<br>TLDR" rendered
as "demo.TLDR"). The cause was walking element tags only (find_all(True)), which is
blind to text nodes, so a <br> followed by plain text looked "trailing" and got
extracted. The function should only remove genuinely-trailing empty <br>/<p>.
"""

from frappe.tests.utils import FrappeTestCase

from gameplan.utils.utils import remove_empty_trailing_paragraphs


class TestRemoveEmptyTrailingParagraphs(FrappeTestCase):
	def test_preserves_hardbreaks_followed_by_text(self):
		# the exact shape from the bug report: <br>s after the last child element
		# (the link) must survive because real text follows them
		html = "<p>and the <a href='#'>dtln-rs demo</a>.<br>TLDR: less choppy.<br>Let's give this a spin.</p>"
		out = remove_empty_trailing_paragraphs(html)
		self.assertEqual(out.count("<br"), 2, f"hard breaks were stripped: {out}")
		self.assertNotIn("demo</a>.TLDR", out)

	def test_removes_trailing_empty_paragraph(self):
		html = "<p>hello</p><p></p>"
		self.assertEqual(remove_empty_trailing_paragraphs(html), "<p>hello</p>")

	def test_removes_trailing_empty_br(self):
		html = "<p>hello</p><br>"
		self.assertEqual(remove_empty_trailing_paragraphs(html), "<p>hello</p>")

	def test_removes_multiple_trailing_empties(self):
		html = "<p>hello</p><p></p><br><p></p>"
		self.assertEqual(remove_empty_trailing_paragraphs(html), "<p>hello</p>")

	def test_keeps_content_when_no_trailing_empties(self):
		html = "<p>hello</p><p>world</p>"
		self.assertEqual(remove_empty_trailing_paragraphs(html), "<p>hello</p><p>world</p>")

	def test_trailing_br_inside_paragraph_after_text_is_kept(self):
		# a <br> that is the last node but sits after text in the same paragraph is
		# part of the visible content layout, not a stray trailing empty block
		html = "<p>line one<br>line two</p>"
		out = remove_empty_trailing_paragraphs(html)
		self.assertEqual(out.count("<br"), 1, f"interior break stripped: {out}")
