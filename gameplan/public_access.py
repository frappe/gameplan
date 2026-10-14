# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Public access switch, request guards and bounded pagination."""

import time

import frappe
from frappe.utils import cint

from gameplan.public_payload import public_doctypes

PUBLIC_ACCESS_CONFIG_KEY = "gameplan_public_access_enabled"
MAX_ROWS = 1000


def public_pagination(start, limit):
	"""Bound every public list and feed to the same page-size contract."""
	return max(cint(start), 0), max(1, min(cint(limit) or 20, MAX_ROWS))


def public_access_enabled() -> bool:
	"""Read the site switch live; demo mode stays closed because it auto-signs visitors in."""
	from gameplan.demo.demo import demo_data_enabled

	if demo_data_enabled():
		return False
	return bool(cint(frappe.conf.get(PUBLIC_ACCESS_CONFIG_KEY)))


def refuse_generic_routes_for_anonymous():
	"""Block generic Gameplan routes whose payloads bypass field and identity cleaning.

	Allow v2 single-document reads and methods; lists use the public wrappers.
	"""
	import frappe.api.v2

	route = anonymous_api_route()
	if not route:
		return
	endpoint, arguments = route
	doctype = arguments.get("doctype")
	allowed = (frappe.api.v2.read_doc, frappe.api.v2.execute_doc_method, frappe.api.v2.handle_rpc_call)
	if doctype in public_doctypes() and endpoint not in allowed:
		frappe.throw("Not permitted", frappe.PermissionError)


ANONYMOUS_RATE_LIMITS = {
	"gameplan.api.search_sqlite": 30,
	"gameplan.api.get_search_filter_options": 30,
	"gameplan.gameplan.doctype.gp_discussion.api.get_discussions": 60,
	"gameplan.public_lists.communities": 60,
	"gameplan.public_lists.spaces": 60,
	"gameplan.public_lists.comments": 120,
	"gameplan.public_lists.polls": 120,
	"gameplan.api.get_public_user_info": 60,
	"gameplan.api.public_file": 600,
	"document": 120,
}
RATE_LIMIT_WINDOW_SECONDS = 60


def limit_anonymous_request_rate():
	"""Limit public reads per site, IP and endpoint in fixed one-minute Redis windows."""
	route = anonymous_api_route()
	if not route:
		return
	key = rate_limit_key(*route)
	limit = ANONYMOUS_RATE_LIMITS.get(key)
	if not limit:
		return

	window = int(time.time() // RATE_LIMIT_WINDOW_SECONDS)
	# make_key prefixes the site, so sites on one bench never share a bucket.
	cache_key = frappe.cache.make_key(f"gameplan:public-rate:{key}:{frappe.local.request_ip}:{window}")
	count = frappe.cache.incrby(cache_key, 1)
	if count == 1:
		frappe.cache.expire(cache_key, RATE_LIMIT_WINDOW_SECONDS * 2)
	if count > limit:
		frappe.throw("Too many requests. Please wait a minute, or sign in.", frappe.RateLimitExceededError)


def rate_limit_key(endpoint, arguments):
	"""Which ANONYMOUS_RATE_LIMITS entry a routed request counts against."""
	import frappe.api.v2

	if endpoint is frappe.api.v2.read_doc:
		return "document"
	method = arguments.get("method") or ""
	return method.split("/")[0]


def anonymous_api_route():
	"""Resolve an anonymous API route; leave unknown routes to Frappe's 404/405 response."""
	import gameplan

	request = getattr(frappe.local, "request", None)
	if not gameplan.is_anonymous() or not request or not request.path.startswith("/api/"):
		return None

	from frappe.api import API_URL_MAP
	from werkzeug.exceptions import HTTPException

	try:
		return API_URL_MAP.bind_to_environ(request.environ).match()
	except HTTPException:
		return None  # not a route; frappe answers it with a 404 or 405


@frappe.whitelist(allow_guest=True)
def realtime_has_permission(doctype: str, name: str = "", ptype: str = "read"):
	"""Deny anonymous Gameplan rooms and Guest doctype rooms, which expose viewer/editor IDs.

	Guests retain permission-checked document updates; the socket handler blocks presence.
	"""
	import gameplan

	if gameplan.is_anonymous() and doctype in public_doctypes():
		frappe.throw("Not permitted", frappe.PermissionError)
	if gameplan.is_guest() and not name:
		# Doctype rooms broadcast list_update.user (the editor's account email).
		frappe.throw("Not permitted", frappe.PermissionError)
	frappe.has_permission(doctype, doc=name, ptype=ptype, throw=True)
	return True


def audit_public_access():
	"""Keep the existing operator command available."""
	from gameplan.public_access_audit import audit_public_access as audit

	return audit()
