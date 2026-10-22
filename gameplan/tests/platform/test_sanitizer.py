# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""What sanitize_content keeps and removes from user-written HTML."""

from frappe.tests.utils import FrappeTestCase

from gameplan.utils.sanitizer import sanitize_content
from gameplan.utils.utils import html_to_text


class TestSanitizeContent(FrappeTestCase):
	def test_editor_content_survives(self):
		# Written the way nh3 serializes it, so a second save changes nothing
		html = (
			'<p data-id="1">Hi <a href="https://frappe.io/" rel="noopener noreferrer">link</a> '
			'<span style="color:red">red</span></p>'
			'<table><tbody><tr><td colwidth="120">a</td><th colwidth="80">b</th></tr></tbody></table>'
		)
		self.assertEqual(sanitize_content(html), html)

	def test_scripts_and_event_handlers_are_removed(self):
		out = sanitize_content('<p onclick="alert(1)">hi<script>alert(2)</script></p>')
		self.assertEqual(out, "<p>hi</p>")

	def test_unsafe_url_schemes_are_removed(self):
		out = sanitize_content('<a href="javascript:alert(1)">x</a><img src="data:image/png;base64,AA">')
		self.assertNotIn("javascript:", out)
		self.assertNotIn("data:", out)

	def test_unknown_style_properties_are_removed(self):
		out = sanitize_content('<p style="color: red; behavior: url(x.htc)">x</p>')
		self.assertIn("color", out)
		self.assertNotIn("behavior", out)

	def test_iframes_are_kept_only_from_allowed_domains(self):
		youtube = sanitize_content(
			'<iframe src="https://www.youtube.com/embed/abc" onload="alert(1)" allowfullscreen></iframe>'
		)
		self.assertIn('src="https://www.youtube.com/embed/abc"', youtube)
		self.assertIn("allowfullscreen", youtube)
		self.assertNotIn("onload", youtube)

		other = sanitize_content('<iframe src="https://evil.example/page"></iframe>')
		self.assertNotIn("evil.example", other)

	def test_html_to_text_strips_tags_and_unescapes(self):
		self.assertEqual(html_to_text("<p>Tom &amp; <b>Jerry</b></p>"), "Tom & Jerry")
