# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import inspect
import re
from functools import wraps
from html import unescape
from typing import NamedTuple
from urllib.parse import parse_qs, unquote, urlparse

import frappe
from bleach import clean
from bs4 import BeautifulSoup


class FileReference(NamedTuple):
	file_url: str
	file_name: str | None = None


def validate_url(url):
	result = urlparse(url)
	if not result.scheme:
		url = "https://" + url
		result = urlparse(url)
	return url if (result.scheme and result.netloc) else False


def extract_mentions(html):
	if not html:
		return []
	soup = BeautifulSoup(html, "html.parser")
	mentions = []
	for d in soup.find_all("span", attrs={"data-type": "mention"}):
		mentions.append(frappe._dict(full_name=d.get("data-label"), email=d.get("data-id")))
	return mentions


def extract_rich_quote_authors(html):
	if not html:
		return []
	soup = BeautifulSoup(html, "html.parser")
	authors = []
	seen = set()
	for tag in soup.find_all("blockquote", attrs={"data-author": True}):
		author = tag.get("data-author")
		if author and author not in seen:
			authors.append(author)
			seen.add(author)
	return authors


def extract_file_urls(html):
	"""Return distinct Frappe file paths referenced in HTML content.

	Looks at src/href of img/a/video/source tags and keeps only same-origin paths
	under /files/ or /private/files/. External (http/https/data) URLs are skipped.
	The path is unquoted so the editor's `?fid=<File.name>` query and %-encoding are
	dropped, matching how Frappe stores File.file_url (it unquotes on insert).
	"""
	return list({reference.file_url for reference in extract_file_references(html)})


def extract_file_references(html):
	"""Return local Frappe file references from HTML content.

	When the editor includes `?fid=<File.name>`, keep it so attachment repair can
	target the exact File row instead of every row that shares the same file_url.
	"""
	if not html:
		return []
	soup = BeautifulSoup(html, "html.parser")
	references = set()
	for tag in soup.find_all(["img", "a", "video", "source"]):
		raw = tag.get("src") or tag.get("href")
		reference = file_reference_from_url(raw)
		if reference:
			references.add(reference)
	return list(references)


def file_reference_from_url(url):
	"""Return a FileReference for a local Frappe file URL, or None for anything else.

	Also used for plain `Attach`/`Attach Image` values, which may hold an external
	URL (an Unsplash photo, say) that has no File row behind it.
	"""
	if not url:
		return None
	parsed = urlparse(url)
	if not is_same_origin_file_url(parsed):
		return None
	path = unquote(parsed.path)
	if not path.startswith(("/files/", "/private/files/")):
		return None
	return FileReference(path, parse_qs(parsed.query).get("fid", [None])[0])


def is_same_origin_file_url(parsed):
	if not parsed.scheme and not parsed.netloc:
		return True
	if parsed.scheme not in ("http", "https"):
		return False

	site_url = urlparse(frappe.utils.get_url())
	return parsed.netloc == site_url.netloc


def remove_empty_trailing_paragraphs(html):
	from bs4 import BeautifulSoup, NavigableString

	soup = BeautifulSoup(html, "html.parser")
	# Walk nodes in reverse document order, including text nodes, and peel off only
	# genuinely-trailing empty <br>/<p>. Text nodes must be considered: a <br> followed
	# by real text is a mid-content line break, not a stray trailing one, so stop at the
	# first non-whitespace text. (Element-only walks miss this and drop interior breaks.)
	for node in reversed(list(soup.descendants)):
		if isinstance(node, NavigableString):
			if node.strip():
				break
			continue
		if node.name in ("br", "p") and not node.get_text(strip=True):
			node.extract()
		else:
			# break on first non-empty element
			break
	return str(soup)


def validate_type(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		sig = inspect.signature(func)
		annotated_types = {
			k: v.annotation for k, v in sig.parameters.items() if v.annotation != inspect._empty
		}
		bound_args = sig.bind(*args, **kwargs)
		bound_args.apply_defaults()
		for arg_name, arg_value in bound_args.arguments.items():
			if arg_name in annotated_types:
				if arg_value is not None and not isinstance(arg_value, annotated_types[arg_name]):
					raise TypeError(
						f"{func.__name__}: Argument {arg_name} must be of type {annotated_types[arg_name]}"
					)
		return func(*args, **kwargs)

	return wrapper


def url_safe_slug(text):
	if not text:
		return text
	slug = re.sub(r"[^A-Za-z0-9\s-]+", "", text.lower())
	slug = slug.replace("\n", " ")
	slug = slug.split(" ")
	slug = [part for part in slug if part]
	slug = "-".join(slug)
	slug = re.sub("[-]+", "-", slug)
	return slug


def html_to_text(html, ignore=None):
	"""Strip HTML tags and unescape HTML entities"""

	text = clean(html or "", tags=ignore or [], strip=True)
	text = unescape(text)
	return text


def html_to_text_preview(html, preview_length=50):
	"""Convert HTML to text preview of 100 characters"""

	text = html_to_text(html)
	text = text.strip()[:preview_length]
	if len(text) == preview_length:
		text += "..."

	return text


def get_document_revisions(doctype, name, fieldname="content"):
	revisions = frappe.qb.get_query(
		"Version",
		fields=["data", "creation", "owner"],
		filters={
			"ref_doctype": doctype,
			"docname": name,
			"data": ["like", f'%["{fieldname}",%'],
		},
		order_by="creation desc",
	).run(as_dict=True)
	response = []
	for revision in revisions:
		data = frappe.parse_json(revision.data) if revision.data else {}
		changes = data.get("changed") or []
		change = next((change for change in changes if change[0] == fieldname), None)
		if not change:
			continue
		response.append(
			{
				"owner": revision.owner,
				"creation": revision.creation,
				"old_value": change[1] or "",
				"new_value": change[2] or "",
			}
		)
	return response
