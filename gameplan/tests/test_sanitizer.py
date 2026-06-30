# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Tests for sanitize_content image handling.

Regression for silent image loss: the editor inserts an image with a transient
`blob:`/`data:` preview src while the upload is in flight and swaps in the real
`/private/files/...` URL when it completes. If content is saved before that swap,
`clean()` strips the preview src (blob:/data: are not allowed protocols), leaving
a broken, invisible `<img>`. sanitize_content should drop such srcless images
while preserving images that have a real src.
"""

from frappe.tests.utils import FrappeTestCase

from gameplan.utils.sanitizer import sanitize_content


class TestSanitizeContentImages(FrappeTestCase):
	def test_keeps_private_file_image(self):
		html = '<p><img src="/private/files/photo.png" width="300" height="109"></p>'
		out = sanitize_content(html)
		self.assertIn('src="/private/files/photo.png"', out)

	def test_keeps_https_image(self):
		html = '<img src="https://example.com/a.png">'
		self.assertIn('src="https://example.com/a.png"', sanitize_content(html))

	def test_drops_blob_preview_image(self):
		# preview src is stripped by clean(); the now-srcless <img> must be removed
		html = '<p><img src="blob:http://localhost:8000/abc-123" width="300" height="109"></p>'
		out = sanitize_content(html)
		self.assertNotIn("<img", out)

	def test_drops_data_uri_image(self):
		html = '<p><img src="data:image/png;base64,iVBORw0" width="300"></p>'
		self.assertNotIn("<img", sanitize_content(html))

	def test_does_not_drop_image_with_data_src_lookalike_attr(self):
		# `data-src` must not be mistaken for a real `src`; this image has no src
		# and should be removed, but the negative lookahead must still match it.
		html = '<img data-src="/private/files/x.png" width="10">'
		self.assertNotIn("<img", sanitize_content(html))
