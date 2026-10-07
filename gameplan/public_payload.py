# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""What a person who is not signed in gets back when they read a public space.

Permissions decide *which* rows an anonymous visitor may read. This module decides *what
is in them*. Signed-in users never pass through here: every function below returns its
input untouched unless nobody is signed in.

It works from an allowlist. Every field of every doctype the Guest role can read is
classified below as public, an author, a child table, or private, and a field nobody has
classified is dropped. `TestPublicPayloadClassification` fails when a doctype gains a field
that is in none of the lists, so a new field is hidden from the public until someone
decides otherwise.

The parts that need care:

- People are identified by their profile handle (the `GP User Profile` name, as in
  `/g/people/<handle>`), never by email. That covers the author fields here, and any HTML
  attribute in a post body whose value is exactly a user id: @mention `data-id`s,
  rich-quote `data-author`s, and whatever stores a user id in an attribute next.
- Child tables have no permission rows of their own, so this is the only thing standing
  between an anonymous visitor and the people in them. Member lists and poll votes are
  dropped; reactions keep their emoji and lose who reacted, which leaves the totals.
"""

import re
from html import unescape
from urllib.parse import quote

import frappe
from pypika import Criterion

import gameplan

# Fields every row may carry, whatever its doctype. `doctype` is not a column; `as_dict`
# adds it.
STANDARD_PUBLIC_FIELDS = frozenset({"name", "creation", "modified", "idx", "docstatus", "doctype"})

# Per doctype: fields shown as they are.
PUBLIC_FIELDS = {
	"GP Team": {
		"title",
		"icon",
		"image",
		"cover_image",
		"cover_image_position",
		"readme",
		"archived_at",
		"visibility",
	},
	"GP Project": {
		"title",
		"description",
		"team",
		"icon",
		"readme",
		"discussions_count",
		"archived_at",
		"visibility",
		"is_anonymous_readable",
	},
	"GP Discussion": {
		"project",
		"team",
		"title",
		"content",
		"status",
		"slug",
		"last_post_at",
		"last_post_type",
		"last_post",
		"comments_count",
		"participants_count",
		"closed_at",
		"pinned_at",
		"pin_scope",
	},
	"GP Comment": {"content", "reference_doctype", "reference_name", "edited_at", "deleted_at"},
	"GP Poll": {"title", "multiple_answers", "anonymous", "discussion", "total_votes", "stopped_at"},
}

# Per doctype: fields that hold a user id. Shown as that user's profile handle.
AUTHOR_FIELDS = {
	"GP Team": {"owner"},
	"GP Project": {"owner"},
	"GP Discussion": {"owner", "last_post_by", "closed_by", "pinned_by"},
	"GP Comment": {"owner"},
	"GP Poll": {"owner"},
}

# Per doctype: child tables, and the child doctype each holds.
TABLE_FIELDS = {
	"GP Team": {"members": "GP Member"},
	"GP Project": {"members": "GP Member"},
	"GP Discussion": {"reactions": "GP Reaction", "tags": "GP Tag Link"},
	"GP Comment": {"reactions": "GP Reaction", "tags": "GP Tag Link"},
	"GP Poll": {"options": "GP Poll Option", "votes": "GP Poll Vote", "reactions": "GP Reaction"},
}

# Per child doctype: what each row keeps. A child doctype that is not here comes back as an
# empty list: who is a member, and who voted for what.
PUBLIC_CHILD_FIELDS = {
	"GP Reaction": {"name", "emoji"},
	"GP Tag Link": {"name", "tag"},
	"GP Poll Option": {"name", "idx", "title", "percentage", "votes"},
}

# Per doctype: fields deliberately left out, with the reason. Listed so that the
# classification test can tell a decided field from a forgotten one.
PRIVATE_FIELDS = {
	"GP Team": {
		"modified_by": "who last touched it, not who wrote it",
		"archived_by": "an admin action, not authorship",
		"is_private": "superseded by visibility; kept only for rollback",
		"visibility_set_by": "an admin action, not authorship",
		"visibility_set_at": "an admin action, not authorship",
	},
	"GP Project": {
		"modified_by": "who last touched it, not who wrote it",
		"archived_by": "an admin action, not authorship",
		"is_private": "superseded by visibility; kept only for rollback",
		"visibility_set_by": "an admin action, not authorship",
		"visibility_set_at": "an admin action, not authorship",
		"tasks_count": "tasks are never public",
	},
	"GP Discussion": {"modified_by": "who last touched it, not who wrote it"},
	"GP Comment": {"modified_by": "who last touched it, not who wrote it"},
	"GP Poll": {"modified_by": "who last touched it, not who wrote it"},
}

# Keys that are not fields but that a controller's `as_dict`, or the feed, adds to a row.
# Shown as they are; nested rows are cleaned separately below.
COMPUTED_FIELDS = {
	"GP Discussion": {
		# GPDiscussion.as_dict, all about the session user, who here is nobody
		"last_unread_comment",
		"last_unread_poll",
		"is_bookmarked",
		"views",
		# gp_discussion.api.get_discussions
		"project_title",
		"unread_count",
		"last_comment_content",
		"last_poll_title",
	},
}

# Keys that hold rows of another doctype, which are cleaned as that doctype.
NESTED_ROWS = {"GP Discussion": {"ongoing_polls": "GP Poll"}}

# Fields holding post bodies, whose HTML can carry user ids and file URLs in attributes.
RICH_TEXT_FIELDS = frozenset({"content", "readme", "description"})

# Per doctype: public fields holding a single file URL.
FILE_FIELDS = {"GP Team": {"image", "cover_image"}}

PRIVATE_FILES_PREFIX = "/private/files/"

# An HTML attribute: ` name="value"` or ` name='value'`.
ATTRIBUTE = re.compile(r"""(\s[\w:.-]+\s*=\s*)(["'])([^"']*)\2""")
EMAIL = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")


def public_doctypes():
	return PUBLIC_FIELDS.keys()


def is_public_field(doctype, fieldname) -> bool:
	"""Whether an anonymous visitor may read `fieldname` of `doctype`, as it is or as a handle."""
	return (
		fieldname in STANDARD_PUBLIC_FIELDS
		or fieldname in PUBLIC_FIELDS.get(doctype, ())
		or fieldname in AUTHOR_FIELDS.get(doctype, ())
	)


def is_filterable_field(doctype, fieldname) -> bool:
	"""Whether an anonymous visitor may filter or sort on `fieldname`.

	Not on an author field: filtering on `owner` would answer "did this email address post
	here?", which turns the filter into a way of checking a guessed address.
	"""
	return fieldname in STANDARD_PUBLIC_FIELDS or fieldname in PUBLIC_FIELDS.get(doctype, ())


def public_fieldnames(doctype) -> list[str]:
	"""The columns `*` stands for when an anonymous visitor lists `doctype`."""
	standard = sorted(STANDARD_PUBLIC_FIELDS - {"doctype"})
	return standard + sorted(PUBLIC_FIELDS[doctype]) + sorted(AUTHOR_FIELDS[doctype])


def for_viewer(doctype, row):
	"""`row` as the session user may see it: unchanged when signed in, cleaned when not."""
	if not gameplan.is_anonymous():
		return row
	return public_rows(doctype, [row])[0]


def rows_for_viewer(doctype, rows):
	"""`rows` as the session user may see them: unchanged when signed in, cleaned when not."""
	if not gameplan.is_anonymous():
		return rows
	return public_rows(doctype, rows)


def public_rows(doctype, rows):
	"""`rows` of `doctype` with everything an anonymous visitor may not see removed."""
	if doctype not in PUBLIC_FIELDS:
		frappe.throw(f"{doctype} is not readable without signing in", frappe.PermissionError)
	user_ids = set()
	for row in rows:
		collect_user_ids(doctype, row, user_ids)
	handles = handles_for(user_ids)
	files = public_file_urls(doctype, rows)
	return [public_row(doctype, row, handles, files.get(str(row.get("name")), {})) for row in rows]


def public_row(doctype, row, handles, files=None):
	"""One row, cleaned. `files` maps each private file URL in it to its public route."""
	files = files or {}
	cleaned = frappe._dict()
	for key, value in row.items():
		if key in AUTHOR_FIELDS[doctype]:
			cleaned[key] = handles.get(value)
		elif key in TABLE_FIELDS[doctype]:
			cleaned[key] = public_child_rows(TABLE_FIELDS[doctype][key], value)
		elif key in NESTED_ROWS.get(doctype, ()):
			nested = NESTED_ROWS[doctype][key]
			cleaned[key] = [public_row(nested, nested_row, handles) for nested_row in value or []]
		elif key in RICH_TEXT_FIELDS and key in PUBLIC_FIELDS[doctype]:
			cleaned[key] = replace_user_ids_in_html(value, handles, files)
		elif key in FILE_FIELDS.get(doctype, ()):
			cleaned[key] = files.get(value, value)
		elif key in STANDARD_PUBLIC_FIELDS or key in PUBLIC_FIELDS[doctype]:
			cleaned[key] = value
		elif key in COMPUTED_FIELDS.get(doctype, ()):
			cleaned[key] = value
	if doctype == "GP Comment" and cleaned.get("deleted_at"):
		cleaned.content = None
	return cleaned


def public_child_rows(child_doctype, rows):
	keep = PUBLIC_CHILD_FIELDS.get(child_doctype)
	if not keep or not rows:
		return []
	return [frappe._dict({key: value for key, value in dict(row).items() if key in keep}) for row in rows]


def collect_user_ids(doctype, row, user_ids):
	for key, value in row.items():
		if key in AUTHOR_FIELDS[doctype] and value:
			user_ids.add(value)
		elif key in RICH_TEXT_FIELDS and isinstance(value, str):
			user_ids.update(user_ids_in_html(value))
		elif key in NESTED_ROWS.get(doctype, ()):
			for nested_row in value or []:
				collect_user_ids(NESTED_ROWS[doctype][key], nested_row, user_ids)


def looks_like_user_id(value) -> bool:
	return value == "Administrator" or bool(EMAIL.match(value))


def user_ids_in_html(html):
	return {value for _, _, value in ATTRIBUTE.findall(html) if looks_like_user_id(value)}


def replace_user_ids_in_html(html, handles, files=None):
	"""Swap every attribute value in `html` that is a user id for that user's handle.

	A value that looks like an email address but belongs to nobody with a profile is
	emptied, not kept: it is still somebody's address. Addresses in the text itself are
	what the author chose to write, and are left alone. A private file URL in `files` is
	pointed at the public file route; any other stays as it is, and frappe refuses it to
	anyone not signed in.
	"""
	if not html or not isinstance(html, str) or "=" not in html:
		return html
	files = files or {}

	def replace(match):
		prefix, quote_char, value = match.groups()
		if value in files:
			return f"{prefix}{quote_char}{files[value]}{quote_char}"
		if not looks_like_user_id(value):
			return match.group(0)
		return f"{prefix}{quote_char}{handles.get(value) or ''}{quote_char}"

	return ATTRIBUTE.sub(replace, html)


def handles_for(user_ids) -> dict:
	"""Map each user id to its profile handle. A user without a profile gets no entry."""
	user_ids = [user for user in user_ids if user]
	if not user_ids:
		return {}
	profiles = frappe.get_all(
		"GP User Profile", filters={"user": ["in", user_ids]}, fields=["user", "name"], limit=0
	)
	return {profile.user: profile.name for profile in profiles}


# What an anonymous visitor may ask a list endpoint for. Plain field names only: no
# aliases, functions, table-qualified names or child-table paths, each of which would let
# a request name a column this module never sees.
IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")
ORDER_TERM = re.compile(r"^\s*([a-z_][a-z0-9_]*)(?:\s+(asc|desc))?\s*$", re.IGNORECASE)


def refuse(message):
	frappe.throw(message, frappe.PermissionError)


def public_list_fields(doctype, fields) -> list:
	"""The columns to select for an anonymous visitor who asked for `fields`.

	`*` stands for every public field. A child table may be asked for with the frappe-ui
	`{table: [fields]}` form; its rows are cleaned afterwards like any other.
	"""
	if doctype not in PUBLIC_FIELDS:
		refuse(f"{doctype} is not readable without signing in")
	fields = frappe.parse_json(fields) if isinstance(fields, str) else fields
	if not fields:
		return ["name"]
	if not isinstance(fields, list):
		fields = [fields]

	selected = []
	for field in fields:
		if field == "*":
			selected += public_fieldnames(doctype)
		elif isinstance(field, str) and IDENTIFIER.match(field) and is_public_field(doctype, field):
			selected.append(field)
		elif isinstance(field, dict) and len(field) == 1 and is_public_table_request(doctype, field):
			selected.append(field)
		else:
			refuse(f"{field!r} of {doctype} is not readable without signing in")
	return selected


def is_public_table_request(doctype, field) -> bool:
	table, child_fields = next(iter(field.items()))
	return (
		table in TABLE_FIELDS[doctype]
		and isinstance(child_fields, list)
		and all(isinstance(name, str) and IDENTIFIER.match(name) for name in child_fields)
	)


def check_public_filters(doctype, filters):
	"""Refuse filters an anonymous visitor may not use: anything but public, non-author fields."""
	filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
	if not filters:
		return
	for fieldname in filter_fieldnames(doctype, filters):
		if not (isinstance(fieldname, str) and is_filterable_field(doctype, fieldname)):
			refuse(f"Filtering {doctype} by {fieldname!r} is not allowed without signing in")


def filter_fieldnames(doctype, filters) -> list:
	if isinstance(filters, dict):
		return list(filters)
	if not isinstance(filters, list):
		refuse("Unrecognised filters")
	names = []
	for condition in filters:
		if isinstance(condition, dict):
			names += list(condition)
		elif isinstance(condition, list | tuple) and len(condition) == 4:
			if condition[0] != doctype:
				refuse("Filters on another doctype are not allowed without signing in")
			names.append(condition[1])
		elif isinstance(condition, list | tuple) and len(condition) in (2, 3):
			names.append(condition[0])
		else:
			refuse("Unrecognised filters")
	return names


def check_public_order_by(doctype, order_by):
	"""Refuse sorting on anything but public, non-author fields.

	Sorting by an author field would leak the order of email addresses one comparison at a
	time.
	"""
	if not order_by:
		return
	for term in str(order_by).split(","):
		match = ORDER_TERM.match(term)
		if not match or not is_filterable_field(doctype, match.group(1)):
			refuse(f"Sorting {doctype} by {term.strip()!r} is not allowed without signing in")


# How many profiles one get_public_user_info call may ask for.
MAX_PUBLIC_PROFILES = 100


def public_profiles(handles) -> list[dict]:
	"""Name and avatar for each of `handles` whose user wrote something the public can read.

	Somebody's profile is public once they author a discussion, comment or poll in a space
	readable without signing in, or close or pin such a discussion: their handle is already
	on the page. Anyone else's handle answers nothing, so this cannot be used to walk the
	member directory. Nothing at all while public access is switched off.
	"""
	from gameplan.public_access import public_access_enabled

	handles = [handle for handle in (handles or []) if isinstance(handle, str) and handle]
	if not handles or not public_access_enabled():
		return []
	profiles = frappe.get_all(
		"GP User Profile",
		filters={"name": ["in", handles[:MAX_PUBLIC_PROFILES]], "enabled": 1},
		fields=[
			"name",
			"user",
			"full_name",
			"image",
			"image_background_color",
			"is_image_background_removed",
		],
		limit=0,
	)
	authors = public_authors([profile.user for profile in profiles])
	return [
		{
			"handle": profile.name,
			"full_name": profile.full_name,
			"image": profile.image,
			"image_background_color": profile.image_background_color,
			"is_image_background_removed": profile.is_image_background_removed,
		}
		for profile in profiles
		if profile.user in authors
	]


def public_authors(users) -> set:
	"""Which of `users` appear as an author on something readable without signing in."""
	if not users:
		return set()
	Project = frappe.qb.DocType("GP Project")
	Discussion = frappe.qb.DocType("GP Discussion")
	Comment = frappe.qb.DocType("GP Comment")
	Poll = frappe.qb.DocType("GP Poll")

	public_spaces = frappe.qb.from_(Project).select(Project.name).where(Project.is_anonymous_readable == 1)
	public_discussions = (
		frappe.qb.from_(Discussion).select(Discussion.name).where(Discussion.project.isin(public_spaces))
	)

	found = set()
	columns = (Discussion.owner, Discussion.last_post_by, Discussion.closed_by, Discussion.pinned_by)
	rows = (
		frappe.qb.from_(Discussion)
		.select(*columns)
		.distinct()
		.where(Discussion.project.isin(public_spaces))
		.where(Criterion.any(column.isin(users) for column in columns))
	).run()
	found.update(user for row in rows for user in row if user in users)
	found.update(
		frappe.qb.from_(Comment)
		.select(Comment.owner)
		.distinct()
		.where(Comment.reference_doctype == "GP Discussion")
		.where(Comment.reference_name.isin(public_discussions))
		.where(Comment.owner.isin(users))
		.run(pluck=True)
	)
	found.update(
		frappe.qb.from_(Poll)
		.select(Poll.owner)
		.distinct()
		.where(Poll.discussion.isin(public_discussions))
		.where(Poll.owner.isin(users))
		.run(pluck=True)
	)
	return found


def public_file_url(file_name) -> str:
	"""Where someone who is not signed in loads a private File (see gameplan.api.public_file)."""
	return f"/api/method/gameplan.api.public_file?fid={quote(str(file_name))}"


def public_file_urls(doctype, rows) -> dict:
	"""For each row, map every private file URL in it to the public file route.

	Only for a File attached to that very row: the route serves a File because the reader
	may read what it is attached to, so pointing a post at a File attached elsewhere would
	only produce a broken image. A URL that names its File (`?fid=`) is matched by name,
	any other by URL. Keyed by the row's name, then by the URL exactly as it appears.
	"""
	from gameplan.utils import file_reference_from_url

	references = {}
	for row in rows:
		if row.get("name") is None:
			continue
		for value in file_values(doctype, row):
			if PRIVATE_FILES_PREFIX not in value:
				continue
			reference = file_reference_from_url(unescape(value))
			if reference and reference.file_url.startswith(PRIVATE_FILES_PREFIX):
				references.setdefault(str(row.get("name")), {})[value] = reference
	if not references:
		return {}

	attached = frappe.get_all(
		"File",
		filters={
			"is_private": 1,
			"attached_to_doctype": doctype,
			"attached_to_name": ["in", list(references)],
		},
		fields=["name", "file_url", "attached_to_name"],
		limit=0,
	)
	by_name = {file.name: file for file in attached}
	by_url = {(str(file.attached_to_name), file.file_url): file.name for file in attached}

	urls = {}
	for row_name, values in references.items():
		for value, reference in values.items():
			named = by_name.get(reference.file_name)
			if named and str(named.attached_to_name) == row_name and named.file_url == reference.file_url:
				file_name = named.name
			else:
				file_name = by_url.get((row_name, reference.file_url))
			if file_name:
				urls.setdefault(row_name, {})[value] = public_file_url(file_name)
	return urls


def file_values(doctype, row):
	for key, value in row.items():
		if not isinstance(value, str):
			continue
		if key in RICH_TEXT_FIELDS and key in PUBLIC_FIELDS[doctype]:
			yield from (attribute for _, _, attribute in ATTRIBUTE.findall(value))
		elif key in FILE_FIELDS.get(doctype, ()):
			yield value
