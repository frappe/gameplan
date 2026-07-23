# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Canonical builders for backend tests.

Product language: Community = GP Team, Space = GP Project (see AGENTS.md).
Builders accept either a doc or a name wherever a linked record is expected.
"""

import frappe
from frappe.model.document import Document


def _name(doc_or_name):
	"""Unwrap a Document to its name; pass any bare identifier straight through.

	Not an `isinstance(str)` check: several Gameplan doctypes (GP Project,
	GP Discussion) autoname to integers, so a valid name is not always a string.
	"""
	return doc_or_name.name if isinstance(doc_or_name, Document) else doc_or_name


def create_user(email, first_name, role=None):
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	if role and role not in frappe.get_roles(email):
		user.add_roles(role)
	return user


def create_admin(email="admin@example.com", first_name="Admin"):
	return create_user(email, first_name, "Gameplan Admin")


def create_member(email="member@example.com", first_name="Member"):
	return create_user(email, first_name, "Gameplan Member")


def create_guest(email="guest@example.com", first_name="Guest"):
	return create_user(email, first_name, "Gameplan Guest")


def create_community(title="Test Community", *, is_private=0, members=(), admins=()):
	doc = frappe.get_doc(doctype="GP Team", title=title, is_private=is_private)
	for user in members:
		doc.append("members", {"user": _name(user)})
	for user in admins:
		doc.append("members", {"user": _name(user), "is_admin": 1})
	return doc.insert(ignore_permissions=True)


def create_space(title, community, *, is_private=0, members=()):
	doc = frappe.get_doc(doctype="GP Project", title=title, team=_name(community), is_private=is_private)
	for user in members:
		doc.append("members", {"user": _name(user)})
	return doc.insert(ignore_permissions=True)


def create_discussion(title, space, *, content="Test content", owner=None):
	doc = frappe.get_doc(doctype="GP Discussion", title=title, project=_name(space), content=content)
	doc.insert(ignore_permissions=True)
	if owner:
		set_owner(doc, owner)
	return doc


def create_comment(discussion, *, content="Test comment", owner=None):
	doc = frappe.get_doc(
		doctype="GP Comment",
		reference_doctype="GP Discussion",
		reference_name=_name(discussion),
		content=content,
	)
	doc.insert(ignore_permissions=True)
	if owner:
		set_owner(doc, owner)
	return doc


def create_task(title, space=None, *, owner=None):
	doc = frappe.get_doc(doctype="GP Task", title=title, project=space and _name(space))
	doc.insert(ignore_permissions=True)
	if owner:
		set_owner(doc, owner)
	return doc


def create_page(title, space=None, *, content="Test content", owner=None):
	doc = frappe.get_doc(doctype="GP Page", title=title, project=space and _name(space), content=content)
	doc.insert(ignore_permissions=True)
	if owner:
		set_owner(doc, owner)
	return doc


def grant_guest_access(user, space):
	filters = {"user": _name(user), "project": _name(space)}
	if frappe.db.exists("GP Guest Access", filters):
		return frappe.get_doc("GP Guest Access", filters)
	return frappe.get_doc(doctype="GP Guest Access", **filters).insert(ignore_permissions=True)


def set_owner(doc, user):
	"""Re-own a doc after insert. Inserts always run as the session user, so tests
	that need content owned by a specific persona rewrite the owner directly."""
	frappe.db.set_value(doc.doctype, doc.name, "owner", _name(user), update_modified=False)
	doc.reload()
	return doc
