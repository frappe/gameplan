# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Public HTML uses the same permissions and field cleaning as anonymous API reads."""

import re
from contextlib import contextmanager
from urllib.parse import quote, unquote, urlencode

import frappe
import nh3
from bs4 import BeautifulSoup
from frappe.query_builder.functions import Count
from frappe.utils import get_url

from gameplan.permissions import can_view_community, can_view_content, can_view_space
from gameplan.public_access import public_access_enabled
from gameplan.public_lists import public_list
from gameplan.visibility import is_anonymous_eligible_community, is_anonymous_eligible_space

PAGE_SIZE = 50
COMMUNITY_PATH = r"/g/community/([^/]+)"
SPACE_PATH = COMMUNITY_PATH + r"/space/([^/]+)"
DISCUSSION_ROUTE = re.compile(SPACE_PATH + r"/discussion/([^/]+)(?:/([^/]+))?/?$")


def get_public_page():
	request = getattr(frappe.local, "request", None)
	if not request:
		return None
	path = request.path.rstrip("/")
	if not public_access_enabled():
		if frappe.session.user == "Guest" and path.startswith("/g/community/"):
			frappe.throw("Page not found", frappe.DoesNotExistError)
		return None
	anonymous = frappe.session.user == "Guest"
	try:
		with public_viewer():
			page = page_number(request.args.get("page"))
			seo = resolve_page(path, page)
		if seo:
			page = seo.get("page", page)
			seo.page = page
			seo.path = page_path(seo.path, page)
			seo.url = get_url(seo.path)
			seo.title = f"{seo.title} — Gameplan" + (f" — Page {page}" if page > 1 else "")
			seo.description = text_preview(seo.get("description") or seo.title)
			seo.previous = page_path(seo.base_path, page - 1) if page > 1 else None
			seo.next = page_path(seo.base_path, page + 1) if seo.has_next else None
			seo.login = "/login?" + urlencode({"redirect-to": seo.path})
			if (
				path != unquote(seo.base_path)
				or request.args.get("page") == "1"
				or (page > 1 and not request.args.get("page"))
			):
				target = {key: request.args[key] for key in ("comment", "poll") if request.args.get(key)}
				frappe.flags.redirect_location = seo.path + (
					("&" if "?" in seo.path else "?") + urlencode(target) if target else ""
				)
				raise frappe.Redirect(http_status_code=301)
		return seo
	except (frappe.DoesNotExistError, frappe.PermissionError):
		if anonymous:
			frappe.throw("Page not found", frappe.DoesNotExistError)
		return None


@contextmanager
def public_viewer():
	# Isolate permission caches without changing the visitor's session or request arguments.
	values = {
		"session": frappe._dict(user="Guest", sid="Guest", data=frappe._dict()),
		"cache": {},
		"role_permissions": {},
		"user_perms": None,
		"new_doc_templates": {},
		"jenv_restricted": None,
		"jenv_unrestricted": None,
	}
	previous = {key: getattr(frappe.local, key, None) for key in values}
	try:
		for key, value in values.items():
			setattr(frappe.local, key, value)
		yield
	finally:
		for key, value in previous.items():
			setattr(frappe.local, key, value)


def page_number(value):
	if value is None:
		return 1
	if not value.isascii() or not value.isdecimal() or len(value) > 6 or int(value) < 1:
		frappe.throw("Page not found", frappe.DoesNotExistError)
	return int(value)


def page_path(path, page):
	return path + (f"?page={page}" if page > 1 else "")


def community_path(name):
	return f"/g/community/{quote(str(name), safe='')}/discussions"


def space_path(space):
	return (
		f"/g/community/{quote(str(space.team), safe='')}/space/{quote(str(space.name), safe='')}/discussions"
	)


def discussion_path(discussion):
	return (
		f"/g/community/{quote(str(discussion.team), safe='')}/space/"
		f"{quote(str(discussion.project), safe='')}/discussion/"
		f"{quote(str(discussion.name), safe='')}/{quote(discussion.slug, safe='')}"
	)


def resolve_page(path, page):
	if path == "/g":
		return community_directory(page)
	if match := re.fullmatch(r"/g/space/[^/]+/discussion/([^/]+)(?:/[^/]+)?", path):
		return discussion_page(match[1], page)
	if match := re.fullmatch(r"/g/space/([^/]+)/discussions", path):
		return feed_page(None, match[1], page)
	if match := DISCUSSION_ROUTE.fullmatch(path):
		return discussion_page(match[3], page)
	if match := re.fullmatch(SPACE_PATH + r"/discussions", path):
		return feed_page(match[1], match[2], page)
	if match := re.fullmatch(COMMUNITY_PATH + r"/discussions", path):
		return feed_page(match[1], None, page)
	return None


def read_public_doc(doctype, name):
	doc = frappe.get_doc(doctype, name)
	if doctype == "GP Team":
		allowed = can_view_community("Guest", doc) and is_anonymous_eligible_community(doc)
	elif doctype == "GP Project":
		allowed = can_view_space("Guest", doc) and is_anonymous_eligible_space(doc)
	else:
		allowed = can_view_content("Guest", doc)
	if not allowed:
		frappe.throw("Page not found", frappe.DoesNotExistError)
	return doc


def paginated_rows(doctype, fields, filters, order, page, allow_empty=False):
	rows = public_list(doctype, fields, filters, order, (page - 1) * PAGE_SIZE, PAGE_SIZE + 1)
	if page > 1 and not rows and not allow_empty:
		frappe.throw("Page not found", frappe.DoesNotExistError)
	return rows[:PAGE_SIZE], len(rows) > PAGE_SIZE


def community_directory(page):
	rows, has_next = paginated_rows("GP Team", ["name", "title", "readme"], {}, "title asc, name asc", page)
	for row in rows:
		row.path = community_path(row.name)
		row.excerpt = text_preview(row.readme)
	return page_data("Communities", "/g", rows, has_next)


def feed_page(community_id, space_id, page):
	space = read_public_doc("GP Project", space_id) if space_id else None
	community = read_public_doc("GP Team", space.team if space else community_id)
	filters = {"team": community.name}
	path = community_path(community.name)
	breadcrumbs = [frappe._dict(title=community.title, path=path)]
	title = community.title
	if space:
		filters = {"project": space.name}
		path = space_path(space)
		breadcrumbs = [frappe._dict(title=community.title, path=community_path(community.name))]
		title = space.title
	rows, has_next = paginated_rows(
		"GP Discussion",
		["name", "title", "content", "project", "team", "slug"],
		filters,
		"last_post_at desc, name desc",
		page,
	)
	for row in rows:
		row.path = discussion_path(row)
		row.excerpt = text_preview(row.content)
	seo = page_data(title, path, rows, has_next)
	seo.breadcrumbs = breadcrumbs
	seo.spaces = (
		public_list(
			"GP Project", ["name", "title", "team"], {"team": community.name}, "title asc", 0, PAGE_SIZE
		)
		if not space_id
		else []
	)
	for space in seo.spaces:
		space.path = space_path(space)
	return seo


def discussion_page(name, page):
	doc = read_public_doc("GP Discussion", name)
	space = read_public_doc("GP Project", doc.project)
	community = read_public_doc("GP Team", space.team)
	if not frappe.local.request.args.get("page"):
		page = linked_reply_page(doc.name, page)
	discussion = doc.as_dict()
	discussion.team = community.name
	comments, has_next = paginated_rows(
		"GP Comment",
		["name", "content", "owner", "creation", "deleted_at"],
		{"reference_doctype": "GP Discussion", "reference_name": doc.name},
		"creation asc, name asc",
		page,
		allow_empty=True,
	)
	polls, more_polls = paginated_rows(
		"GP Poll",
		["name", "title", "creation", {"options": ["title", "percentage"]}],
		{"discussion": doc.name},
		"creation asc, name asc",
		page,
		allow_empty=True,
	)
	if page > 1 and not comments and not polls:
		frappe.throw("Page not found", frappe.DoesNotExistError)
	has_next = has_next or more_polls
	seo = page_data(discussion.title, discussion_path(discussion), [], has_next)
	seo.page = page
	seo.polls = polls
	seo.discussion = discussion
	seo.discussion.content = public_html(discussion.content)
	seo.description = text_preview(discussion.content)
	seo.comments = comments
	for comment in comments:
		comment.content = public_html(comment.content) if not comment.deleted_at else ""
	seo.breadcrumbs = [
		frappe._dict(title=community.title, path=community_path(community.name)),
		frappe._dict(title=space.title, path=space_path(space)),
	]
	return seo


def linked_reply_page(discussion, default):
	for parameter, doctype, filters in (
		("comment", "GP Comment", {"reference_doctype": "GP Discussion", "reference_name": discussion}),
		("poll", "GP Poll", {"discussion": discussion}),
	):
		name = frappe.local.request.args.get(parameter)
		if not name or name == "first_post":
			continue
		rows = public_list(doctype, ["name", "creation"], {**filters, "name": name}, None, 0, 1)
		if not rows:
			continue
		row = rows[0]
		table = frappe.qb.DocType(doctype)
		position = (
			frappe.qb.get_query(
				doctype, fields=[Count(table.name).as_("total")], filters=filters, ignore_permissions=False
			)
			.where(
				(table.creation < row.creation)
				| ((table.creation == row.creation) & (table.name <= row.name))
			)
			.run(as_dict=True)[0]
			.total
		)
		return (position - 1) // PAGE_SIZE + 1
	return default


def page_data(title, path, rows, has_next):
	return frappe._dict(
		title=title,
		path=path,
		base_path=path,
		rows=rows,
		has_next=has_next,
		breadcrumbs=[],
		spaces=[],
		discussion=None,
		comments=[],
	)


def text_preview(content):
	return " ".join(BeautifulSoup(content or "", "html.parser").stripped_strings)[:160]


def public_html(content):
	# Standalone HTML must not admit document-level tags such as meta refresh.
	return nh3.clean(content or "", link_rel="ugc nofollow noopener noreferrer")
