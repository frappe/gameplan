# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors

from urllib.parse import urlparse

from bleach import clean
from bleach.css_sanitizer import CSSSanitizer
from bleach_allowlist import bleach_allowlist
from frappe.utils.html_utils import (
	acceptable_attributes,
	acceptable_elements,
	mathml_elements,
	svg_attributes,
	svg_elements,
)

ALLOWED_IFRAME_DOMAINS = [
	"youtube.com",
	"www.youtube.com",
	"youtu.be",
	"vimeo.com",
	"player.vimeo.com",
	"codepen.io",
	"codesandbox.io",
	"figma.com",
	"www.figma.com",
	"embed.figma.com",
	"docs.google.com",
	"drive.google.com",
	"notion.so",
	"www.notion.so",
]


def is_allowed_iframe_domain(src_url):
	"""Check if iframe src URL is from an allowed domain."""
	if not src_url:
		return False

	try:
		parsed_url = urlparse(src_url)
		domain = parsed_url.netloc.lower()
		return any(allowed_domain in domain for allowed_domain in ALLOWED_IFRAME_DOMAINS)
	except Exception:
		return False


def iframe_attribute_filter(tag, name, value):
	"""Custom attribute filter for iframe tags."""
	# Always allow these safe attributes
	safe_attrs = ["src", "width", "height", "title", "frameborder", "allowfullscreen", "loading"]

	if name in safe_attrs:
		# Special validation for src attribute
		if name == "src":
			return is_allowed_iframe_domain(value)
		return True

	# Allow data- attributes for iframe functionality
	if name.startswith("data-"):
		return True

	return False


def sanitize_content(html):
	"""
	Sanitize HTML tags, attributes and style to prevent XSS attacks
	Based on bleach clean, bleach whitelist and html5lib's Sanitizer defaults

	Does not sanitize JSON unless explicitly specified, as it could lead to future problems
	"""

	if not isinstance(html, str):
		return html

	tags = (
		list(acceptable_elements)
		+ list(svg_elements)
		+ list(mathml_elements)
		+ ["html", "head", "meta", "link", "body", "style", "o:p", "iframe"]
	)

	def attributes_filter(tag, name, value):
		if name.startswith("data-"):
			return True
		# TipTap stores resized table column widths as a comma-separated
		# `colwidth` attribute on cells; it is the authoritative source on
		# reparse, so preserve it to keep custom column widths after save.
		if name == "colwidth" and tag in ("td", "th"):
			return True
		return name in acceptable_attributes

	attributes = {"*": attributes_filter, "svg": svg_attributes, "iframe": iframe_attribute_filter}
	css_sanitizer = CSSSanitizer(allowed_css_properties=bleach_allowlist.all_styles)

	# returns html with escaped tags, escaped orphan >, <, etc.
	escaped_html = clean(
		html,
		tags=tags,
		attributes=attributes,
		css_sanitizer=css_sanitizer,
		strip_comments=False,
		protocols={"cid", "http", "https", "mailto"},
	)

	return escaped_html
