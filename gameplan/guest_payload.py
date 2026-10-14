# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Use profile handles for other accounts, without changing a Guest's own identity."""

import re

import frappe

import gameplan
from gameplan.public_payload import (
	EMAIL,
	RICH_TEXT_FIELDS,
	handles_for,
	looks_like_user_id,
	replace_user_ids_in_html,
	user_ids_in_html,
)

ACCOUNT_EMAIL = re.compile(EMAIL.pattern.removeprefix("^").removesuffix("$"))
AUTHORED_FIELDS = RICH_TEXT_FIELDS | {"title", "bio"}
ERROR_TEXT_FIELDS = {"_server_messages", "_error_message", "message", "error"}


def for_guest(payload):
	if not gameplan.is_guest():
		return payload
	user_ids = set()

	def collect(value, field=None):
		if isinstance(value, dict):
			for key, item in value.items():
				collect(key)
				collect(item, key)
		elif isinstance(value, list | tuple):
			for item in value:
				collect(item, field)
		elif isinstance(value, str):
			if field in AUTHORED_FIELDS:
				user_ids.update(user_ids_in_html(value))
			elif field in ERROR_TEXT_FIELDS:
				user_ids.update(ACCOUNT_EMAIL.findall(value))
			elif looks_like_user_id(value):
				user_ids.add(value)

	collect(payload)
	handles = handles_for(user_ids - {frappe.session.user})
	handles[frappe.session.user] = frappe.session.user

	def clean(value, field=None):
		if isinstance(value, dict):
			return frappe._dict({clean(key): clean(item, key) for key, item in value.items()})
		if isinstance(value, list | tuple):
			return [clean(item, field) for item in value]
		if isinstance(value, str):
			if field in AUTHORED_FIELDS:
				return replace_user_ids_in_html(value, handles)
			if looks_like_user_id(value):
				return handles.get(value, "")
			if field in ERROR_TEXT_FIELDS:
				return ACCOUNT_EMAIL.sub(lambda match: handles.get(match.group(), ""), value)
		return value

	return clean(payload)


def hide_guest_identity_data(response):
	"""Cover generic REST reads as well as app APIs through Frappe's response hook."""
	if not gameplan.is_guest() or not response.is_json:
		return
	try:
		payload = response.get_json()
		# Debug tracebacks can contain account IDs inside arbitrary strings.
		if isinstance(payload, dict):
			for key in ("exc", "exception"):
				payload.pop(key, None)
		response.set_data(frappe.as_json(for_guest(payload)))
	except Exception:
		# Frappe logs hook errors and continues: never leave the uncleaned body in place.
		response.status_code = 500
		response.set_data(frappe.as_json({"message": "Unable to load account-safe data."}))
		frappe.log_error(title="Gameplan Guest payload")


def users_for_handles(identities):
	"""Resolve submitted mentions in one query; existing account IDs still work."""
	handles = [
		identity
		for identity in identities
		if identity and identity != "_everyone_" and not looks_like_user_id(identity)
	]
	if not handles:
		return {}
	return {
		profile.name: profile.user
		for profile in frappe.get_all(
			"GP User Profile", filters={"name": ["in", handles]}, fields=["name", "user"], limit=0
		)
	}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def can_view_presence():
	"""Gameplan uses document updates, not Frappe's email-based viewer feed."""
	return not gameplan.is_anonymous() and not gameplan.is_guest()
