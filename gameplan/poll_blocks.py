# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""A poll written into a post's body: a reply, or a discussion's opening post.

The editor saves a new poll as `<div data-type="poll" data-poll-draft="{json}">`. When the
post is saved it creates the GP Poll and rewrites the block to `data-poll="<name>"`. Saving
the post without the block deletes the poll, which only the poll's owner may do.
"""

import json
import re

import frappe
from bs4 import BeautifulSoup
from frappe import _

POLL_BLOCK = re.compile(r'<div\b[^>]*\bdata-type="poll"[^>]*>\s*</div>')


def has_a_poll_that_stays(content, poll):
	"""Whether `content` keeps a poll: a new draft, or a block naming the post's own `poll`.

	A block pointing at another post's poll (one pasted from elsewhere) is dropped on save,
	so it does not count as content.
	"""
	block = POLL_BLOCK.search(content or "")
	if not block:
		return False
	attrs = BeautifulSoup(block.group(), "html.parser").div.attrs
	if "data-poll-draft" in attrs:
		return True
	return bool(poll) and attrs.get("data-poll") == str(poll)


def sync_poll_block(doc, poll, create, one_poll_message):
	"""Create, keep or delete `doc`'s poll so it matches the block in `doc.content`.

	`poll` is the post's stored poll, if any. `create(draft)` inserts a new poll from the
	block's draft and returns its name.
	"""
	blocks = POLL_BLOCK.findall(doc.content or "")
	if len(blocks) > 1:
		frappe.throw(one_poll_message)
	attrs = BeautifulSoup(blocks[0], "html.parser").div.attrs if blocks else {}

	if poll and attrs.get("data-poll") != str(poll):
		if not frappe.has_permission("GP Poll", "delete", poll):
			frappe.throw(_("Only the poll's owner can remove it"), frappe.PermissionError)
		frappe.delete_doc("GP Poll", poll)
		poll = None
	if not poll and "data-poll-draft" in attrs:
		poll = create(parse_draft(attrs["data-poll-draft"]))

	block = f'<div data-type="poll" data-poll="{poll}"></div>' if poll else ""
	content = POLL_BLOCK.sub(block, doc.content or "")
	if content != doc.content:
		doc.db_set("content", content, update_modified=False)


def parse_draft(raw):
	try:
		draft = json.loads(raw)
	except ValueError:
		frappe.throw(_("Invalid poll"))
	options = draft.get("options") if isinstance(draft, dict) else None
	if not isinstance(options, list) or not all(isinstance(option, dict) for option in options):
		frappe.throw(_("Invalid poll"))
	return draft


def insert_poll(draft, **values):
	"""Insert a GP Poll from a parsed block draft, with `values` saying where it lives."""
	return (
		frappe.get_doc(
			doctype="GP Poll",
			title=draft.get("title"),
			anonymous=draft.get("anonymous"),
			multiple_answers=draft.get("multiple_answers"),
			options=[{"title": option.get("title")} for option in draft["options"] if option.get("title")],
			**values,
		)
		.insert()
		.name
	)
