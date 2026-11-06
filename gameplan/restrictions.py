"""Current restriction state; moderation history is evidence, not an authorization index."""

import hashlib
from datetime import datetime, timedelta, timezone

import frappe
from frappe.utils import cint, get_datetime
from frappe.utils.caching import request_cache

from gameplan.permissions import is_global_admin


def utc_now():
	# Deadlines are UTC instants, independent of the site's mutable timezone and DST folds.
	return datetime.now(timezone.utc).replace(tzinfo=None)


def restriction_name(user, community=""):
	return hashlib.sha256(f"{community or ''}\0{user}".encode()).hexdigest()


def state(user, community=""):
	return frappe.db.get_value(
		"GP User Restriction",
		restriction_name(user, community),
		["name", "user", "community", "active", "expires_at", "reason", "modified"],
		as_dict=True,
	)


@request_cache
def current_state(user, community=""):
	return state(user, community)


def active(row):
	return bool(row and row.active and (not row.expires_at or get_datetime(row.expires_at) > utc_now()))


def active_condition(table):
	return (table.active == 1) & (table.expires_at.isnull() | (table.expires_at > utc_now()))


def is_suspended(user):
	return active(current_state(user))


def require_not_suspended(login_manager=None):
	"""Reject active site suspensions for password, session, API-key and OAuth authentication."""
	user = login_manager.user if login_manager else frappe.session.user
	if user and user != "Guest" and is_suspended(user):
		frappe.throw(
			"Your account is suspended. Check your suspension email for details.", frappe.AuthenticationError
		)


def expiry_from_iso(value):
	if not value:
		return None
	try:
		parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
		if parsed.tzinfo is None:
			raise ValueError
		result = parsed.astimezone(timezone.utc).replace(tzinfo=None)
	except (AttributeError, TypeError, ValueError, OverflowError):
		frappe.throw("Expiry must include a valid timezone")
	if result <= utc_now():
		frappe.throw("Choose an expiry in the future")
	return result


def iso_expiry(value):
	return get_datetime(value).replace(tzinfo=timezone.utc).isoformat() if value else None


@frappe.whitelist(methods=["POST"])
def set_restriction(
	user: str,
	enabled: int,
	reason: str,
	community: str = "",
	expires_at: str = "",
	expected_modified: str | None = None,
	duration_seconds: int | None = None,
):
	"""Set, change or lift an audited Community ban or whole-site account suspension."""
	from gameplan.community_bans import can_moderate_community

	community = community or ""
	if cint(enabled) not in (0, 1):
		frappe.throw("Choose whether to set or lift the restriction")
	if not (can_moderate_community(community) if community else is_global_admin(frappe.session.user)):
		frappe.throw("You cannot manage this restriction", frappe.PermissionError)
	if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
		frappe.throw("Enter a reason of at most 500 characters")
	if community:
		# Lock the Community row only: loading the document would read every member.
		if not frappe.db.get_value("GP Team", community, "name", for_update=True):
			raise frappe.DoesNotExistError(f"GP Team {community} not found")
		if not can_moderate_community(community, for_update=True):
			frappe.throw("You cannot manage this restriction", frappe.PermissionError)
	if not frappe.db.get_value("User", user, "name", for_update=True) or user == "Guest":
		frappe.throw("Choose an existing user")
	if user == frappe.session.user or user == "Administrator":
		frappe.throw("You cannot restrict this account")
	if cint(enabled) and (
		is_global_admin(user) or (community and can_moderate_community(community, user, for_update=True))
	):
		frappe.throw("Remove the applicable staff role before restricting this user")
	previous = state(user, community)
	if expected_modified is not None:
		changed = (
			active(previous)
			if expected_modified == ""
			else str(previous.modified if previous else "") != expected_modified
		)
		if changed:
			frappe.throw(
				"This restriction changed. Refresh before trying again.", frappe.TimestampMismatchError
			)
	expiry = expiry_from_iso(expires_at) if cint(enabled) else None
	if cint(enabled) and duration_seconds is not None:
		if cint(duration_seconds) not in (0, 3600, 86400, 604800, 2592000) or expires_at:
			frappe.throw("Choose a supported duration or a custom expiry")
		expiry = utc_now() + timedelta(seconds=cint(duration_seconds)) if cint(duration_seconds) else None
	if previous and previous.active and not active(previous):
		write_expiry(previous)
		previous.active = 0
	if not cint(enabled) and not active(previous):
		return
	if (
		cint(enabled)
		and active(previous)
		and (get_datetime(previous.expires_at) if previous.expires_at else None) == expiry
		and previous.reason == reason.strip()
	):
		return
	before = previous.expires_at if previous else None
	was_active = active(previous)
	doc = (
		frappe.get_doc("GP User Restriction", previous.name)
		if previous
		else frappe.new_doc("GP User Restriction")
	)
	doc.update(
		dict(
			name=restriction_name(user, community),
			user=user,
			community=community,
			active=cint(bool(cint(enabled))),
			expires_at=expiry,
			reason=reason.strip(),
		)
	)
	old_flag = frappe.flags.restriction_action
	try:
		frappe.flags.restriction_action = True
		doc.save(ignore_permissions=True)
	finally:
		frappe.flags.restriction_action = old_flag
	action = (
		("Ban Changed" if was_active else "Ban")
		if community
		else ("Suspension Changed" if was_active else "Suspend")
	)
	if not cint(enabled):
		action = "Unban" if community else "Lift Suspension"
	frappe.local.request_cache.clear()
	log_action(doc, action, before)
	from gameplan.restriction_notifications import notify

	frappe.enqueue(
		notify,
		queue="short",
		enqueue_after_commit=True,
		user=user,
		community=community,
		action=action,
		reason=reason.strip(),
		expires_at=iso_expiry(expiry),
	)
	if not community and cint(enabled):
		frappe.realtime.publish_realtime(
			"gameplan:account_suspended", {"user": user}, user=user, after_commit=True
		)
		frappe.enqueue(revoke_sessions, queue="short", enqueue_after_commit=True, user=user)
	from gameplan.realtime import RESTRICTIONS_CHANGED

	frappe.realtime.publish_realtime(RESTRICTIONS_CHANGED, user=user, after_commit=True)
	return {"modified": str(doc.modified), "expires_at": iso_expiry(expiry)}


def log_action(doc, action, previous_expiry=None):
	frappe.get_doc(
		doctype="GP Moderation Log",
		community=doc.community,
		user=doc.user,
		action=action,
		reason=doc.reason,
		previous_expires_at=previous_expiry,
		expires_at=doc.expires_at,
	).insert(ignore_permissions=True)


def write_expiry(row):
	row.reason = "Restriction expired"
	log_action(row, "Restriction Expired", row.expires_at)
	frappe.db.set_value("GP User Restriction", row.name, "active", 0)
	frappe.local.request_cache.clear()


def expire_due():
	"""Record up to 100 due expiries; authorization never waits for this job."""
	# `<=` on a date also matches an empty one, so permanent restrictions must be left out
	# explicitly: 100 of them sorted first and the job never reached an expiring one.
	rows = frappe.get_all(
		"GP User Restriction",
		filters=[["active", "=", 1], ["expires_at", "is", "set"], ["expires_at", "<=", utc_now()]],
		fields=["name", "user"],
		order_by="expires_at asc, name asc",
		limit=100,
	)
	for row in rows:
		if not frappe.db.get_value("User", row.user, "name", for_update=True):
			continue
		current = frappe.get_doc("GP User Restriction", row.name)
		if current.active and current.expires_at and not active(current):
			write_expiry(current)
	if len(rows) == 100:
		frappe.enqueue(expire_due, queue="long", enqueue_after_commit=True)


def revoke_sessions(user):
	from frappe.sessions import clear_sessions, get_sessions_to_clear

	if not active(state(user)):
		return
	# Frappe commits per session and caps cleanup at 100; only run after durable suspension.
	clear_sessions(user=user, force=True)
	if get_sessions_to_clear(user=user, force=True):
		frappe.enqueue(revoke_sessions, queue="short", enqueue_after_commit=True, user=user)


def clear_state(doc, method=None):
	field = "user" if doc.doctype == "User" else "community"
	frappe.db.delete("GP User Restriction", {field: doc.name})
	frappe.local.request_cache.clear()
