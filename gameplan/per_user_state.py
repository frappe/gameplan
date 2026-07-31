# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Row-level access control for the doctypes that hold per-user state.

GP Notification, GP Project Visit, GP Discussion Visit and GP Pinned Project each
store one row per user, and each grants Gameplan Member and Gameplan Guest read and
write with `if_owner` unset (GP Pinned Project also grants `delete`). Role permissions
alone therefore let any signed-in user read, enumerate, overwrite and — for pins —
delete anyone else's bell feed, visit history, read-state and sidebar through the
generic `/api/v2/document/<doctype>` API.

`if_owner` cannot express this rule. For GP Notification the row's `owner` is the
person who *triggered* it (the mentioner), while the row belongs to `to_user` — so
`if_owner` would hand the notification to the sender and hide it from the recipient.
The visit doctypes and GP Pinned Project have the mirror problem:
`GPUnreadRecord.create_project_visits`, the Discourse importer and the demo seeder
legitimately create rows *for* another user, whose `owner` is then the importing
session. The row's own user column is the only honest source of truth, so the rule is
expressed as a `permission_query_conditions` hook (list/report) plus a `has_permission`
hook (single-document read/write/create/delete), the same pair GP Bookmark uses.

`GPPinnedProject.get_list_query` scopes only one endpoint —
`gameplan.extends.client.get_list`, the SPA's default list URL. `frappe.get_list`,
`frappe.client.get_list` and `/api/v2/document/GP Pinned Project` never call it, and
none of them scoped anything before these hooks existed.

Server-side writers are unaffected: every one of them (`GPProject.track_visit`,
`GPProject.mark_all_as_read`, `GPProject.archive`, `GPDiscussion.track_visit`, the
mention and reaction mixins, `GPUnreadRecord`) writes with `ignore_permissions` or raw
query-builder statements, both of which skip these hooks.
"""

import frappe

from gameplan.permissions import criterion_sql, get_doc_value, is_delete_cascade

# The column naming the user a row belongs to, per doctype.
NOTIFICATION_USER_FIELD = "to_user"
VISIT_USER_FIELD = "user"
PIN_USER_FIELD = "user"


def _own_rows_only(doctype, fieldname, user):
	user = user or frappe.session.user
	table = frappe.qb.DocType(doctype)
	return criterion_sql(table[fieldname] == user)


def _belongs_to_user(doc, fieldname, user):
	user = user or frappe.session.user
	# Doctype-level checks arrive without a document (e.g. "may this user open the list
	# at all?"); those stay open and the query conditions above do the scoping.
	if not hasattr(doc, "doctype"):
		return True
	if is_delete_cascade(doc):
		# Deleting a discussion or a Space takes *everyone's* visit rows with it (see
		# GPDiscussion/GPProject.on_delete_cascade). The parent delete was already
		# authorised and the flag is unreachable over HTTP, so this row goes with it.
		return True
	return get_doc_value(doc, fieldname) == user


def notification_query_conditions(user=None, **kwargs):
	return _own_rows_only("GP Notification", NOTIFICATION_USER_FIELD, user)


def notification_has_permission(doc, ptype="read", user=None, **kwargs):
	"""A notification is addressed to exactly one person: only they may see or clear it.

	Deliberately no admin exception — nothing in Gameplan reads someone else's bell feed.
	"""
	return _belongs_to_user(doc, NOTIFICATION_USER_FIELD, user)


def project_visit_query_conditions(user=None, **kwargs):
	return _own_rows_only("GP Project Visit", VISIT_USER_FIELD, user)


def project_visit_has_permission(doc, ptype="read", user=None, **kwargs):
	"""A Space visit row is one user's own last-visit / mark-all-read watermark."""
	return _belongs_to_user(doc, VISIT_USER_FIELD, user)


def discussion_visit_query_conditions(user=None, **kwargs):
	return _own_rows_only("GP Discussion Visit", VISIT_USER_FIELD, user)


def discussion_visit_has_permission(doc, ptype="read", user=None, **kwargs):
	"""A discussion visit row is one user's own read-state for that discussion."""
	return _belongs_to_user(doc, VISIT_USER_FIELD, user)


def pinned_project_query_conditions(user=None, **kwargs):
	return _own_rows_only("GP Pinned Project", PIN_USER_FIELD, user)


def pinned_project_has_permission(doc, ptype="read", user=None, **kwargs):
	"""A pin is one user's own sidebar shortcut, so only they may see or drop it.

	`delete` matters most here: unpinning *is* deleting the row (there is no unpin
	endpoint), which is why the role grant has to stay and this hook has to scope it.
	"""
	if ptype == "create":
		# `Document.insert` runs the create check *before* `before_insert`, and
		# `before_insert` is where `user` gets stamped with the session user. Judging the
		# still-empty field here would deny every legitimate pin; the stamping is what
		# makes creating a pin for someone else impossible in the first place.
		return True
	return _belongs_to_user(doc, PIN_USER_FIELD, user)
