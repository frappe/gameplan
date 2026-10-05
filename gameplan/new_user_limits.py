# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Limits on what a stranger may post in a public space, after Discourse's trust level 0.

Anyone can create a Gameplan Guest account when signup is open, and a Gameplan Guest may
post in any space readable without signing in. Discourse lets such brand-new users take
part too, within limits that make spam and abuse slow and visible. These are its
defaults for trust level 0:

- 3 topics and 10 replies in the account's first day,
- 1 image, 2 links and 2 mentions per post, and no attachments,

plus a 24-hour window to edit one's own posts.

They apply to a Gameplan Guest acting in a space they reach only through public access:
not to members, and not to a guest in a space they were invited to. They are checked
against the person saving, on every route that saves (the app, the REST API, Desk),
through `validate`. The app only shows the error.
"""

from datetime import timedelta

import frappe
from bs4 import BeautifulSoup
from frappe.utils import get_datetime, now_datetime

import gameplan

FIRST_DAY = timedelta(hours=24)
EDIT_WINDOW = timedelta(hours=24)
MAX_DISCUSSIONS_IN_FIRST_DAY = 3
MAX_REPLIES_IN_FIRST_DAY = 10
MAX_IMAGES_PER_POST = 1
MAX_LINKS_PER_POST = 2
MAX_ATTACHMENTS_PER_POST = 0
MAX_MENTIONS_PER_POST = 2

# The doctypes a Gameplan Guest may create (permissions.GUEST_CREATABLE_DOCTYPES), and the
# fields whose change is an edit of the post. Reactions and votes are not edits.
POST_FIELDS = {
	"GP Discussion": ("title", "content"),
	"GP Comment": ("content",),
	"GP Poll": ("title",),
}
RICH_TEXT_FIELD = "content"
# A reply is anything posted into an existing discussion.
REPLY_DOCTYPES = ("GP Comment", "GP Poll")
EVERYONE_MENTION = "_everyone_"


class NewUserLimitError(frappe.ValidationError):
	pass


def check_new_user_limits(doc, method=None):
	"""`validate` for every doctype a Gameplan Guest may create."""
	user = frappe.session.user
	if not is_limited(user, doc):
		return
	if doc.is_new():
		check_first_day(user, doc)
	elif get_owner(doc) == user and post_changed(doc):
		check_edit_window(doc)
	if doc.is_new() or post_changed(doc):
		check_post(doc.get(RICH_TEXT_FIELD) if doc.meta.has_field(RICH_TEXT_FIELD) else None)


def is_limited(user, doc) -> bool:
	"""Whether `user` reaches `doc`'s space only because it is public."""
	from gameplan.permissions import (
		get_content_project,
		get_project_info,
		has_guest_access,
		is_publicly_readable_space,
	)

	if not gameplan.is_guest(user):
		return False
	project = get_content_project(doc)
	if not project or has_guest_access(user, project):
		return False
	project_info = get_project_info(project)
	return bool(project_info and is_publicly_readable_space(project_info))


def check_first_day(user, doc):
	created = frappe.db.get_value("User", user, "creation")
	if not created or now_datetime() - get_datetime(created) >= FIRST_DAY:
		return
	if doc.doctype == "GP Discussion":
		posted = frappe.db.count("GP Discussion", {"owner": user})
		limit, what = MAX_DISCUSSIONS_IN_FIRST_DAY, "discussions"
	else:
		posted = sum(frappe.db.count(doctype, {"owner": user}) for doctype in REPLY_DOCTYPES)
		limit, what = MAX_REPLIES_IN_FIRST_DAY, "replies"
	if posted >= limit:
		refuse(
			f"New accounts can post {limit} {what} on their first day. You can post more once your"
			" account is a day old."
		)


def check_edit_window(doc):
	if now_datetime() - get_datetime(doc.creation) > EDIT_WINDOW:
		refuse("Posts from new accounts can be edited for 24 hours after posting.")


def check_post(html):
	"""Refuse a post body that goes over any per-post limit."""
	counts = count_post_contents(html)
	if counts.everyone:
		refuse("New accounts cannot mention everyone.")
	for key, limit, singular, plural in (
		("images", MAX_IMAGES_PER_POST, "image", "images"),
		("links", MAX_LINKS_PER_POST, "link", "links"),
		("mentions", MAX_MENTIONS_PER_POST, "mention", "mentions"),
	):
		if counts[key] > limit:
			refuse(f"New accounts can add {limit} {singular if limit == 1 else plural} per post.")
	if counts.attachments > MAX_ATTACHMENTS_PER_POST:
		refuse("New accounts cannot attach files or videos.")


def count_post_contents(html) -> frappe._dict:
	"""How many images, links, attachments and mentions a post body carries.

	An uploaded image is an image; any other uploaded file, and any video, is an
	attachment. A custom emoji is neither. An embedded iframe counts as a link, as a
	Discourse onebox does.
	"""
	from gameplan.utils import file_reference_from_url

	counts = frappe._dict(images=0, links=0, attachments=0, mentions=0, everyone=False)
	if not html:
		return counts
	soup = BeautifulSoup(html, "html.parser")
	for img in soup.find_all("img"):
		if not img.has_attr("data-emoji"):
			counts.images += 1
	for link in soup.find_all("a", href=True):
		if file_reference_from_url(link["href"]):
			counts.attachments += 1
		else:
			counts.links += 1
	counts.links += len(soup.find_all("iframe"))
	counts.attachments += len(soup.find_all(["video", "audio"]))
	for mention in soup.find_all("span", attrs={"data-type": "mention"}):
		if mention.get("data-id") == EVERYONE_MENTION:
			counts.everyone = True
		else:
			counts.mentions += 1
	return counts


def post_changed(doc) -> bool:
	before = doc.get_doc_before_save()
	if not before:
		return True
	return any(doc.get(field) != before.get(field) for field in POST_FIELDS[doc.doctype])


def get_owner(doc):
	return doc.owner or frappe.db.get_value(doc.doctype, doc.name, "owner")


def refuse(message):
	frappe.throw(message, NewUserLimitError, title="New account limit")
