# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors

from urllib.parse import urlparse

import nh3
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


IFRAME_ATTRIBUTES = {"src", "width", "height", "title", "frameborder", "allowfullscreen", "loading"}


def attribute_filter(tag, name, value):
	"""Drop iframe sources outside the allowed domains. Returns the value to keep, or None."""
	if tag == "iframe" and name == "src" and not is_allowed_iframe_domain(value):
		return None
	return value


def sanitize_content(html):
	"""
	Sanitize HTML tags, attributes and style to prevent XSS attacks
	Based on nh3 clean, bleach allowlist and html5lib's Sanitizer defaults

	Does not sanitize JSON unless explicitly specified, as it could lead to future problems
	"""

	if not isinstance(html, str):
		return html

	tags = (
		acceptable_elements.union(svg_elements)
		.union(mathml_elements)
		.union(["html", "head", "meta", "link", "body", "o:p", "iframe"])
	)

	attributes = {
		"*": acceptable_attributes,
		"svg": svg_attributes,
		"iframe": IFRAME_ATTRIBUTES,
		# TipTap stores resized table column widths as a comma-separated
		# `colwidth` attribute on cells; it is the authoritative source on
		# reparse, so preserve it to keep custom column widths after save.
		"td": {"colwidth"},
		"th": {"colwidth"},
	}

	# returns sanitized HTML with unsafe tags and attributes removed
	return nh3.clean(
		html,
		tags=tags,
		attributes=attributes,
		attribute_filter=attribute_filter,
		generic_attribute_prefixes={"data-"},
		strip_comments=False,
		filter_style_properties=set(bleach_allowlist.all_styles),
		url_schemes={"cid", "http", "https", "mailto"},
	)
