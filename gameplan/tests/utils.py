# Copyright (c) 2024, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Shared helpers for creating test fixtures (users, teams, projects, etc.)."""

import frappe


def create_user(email, first_name, role):
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


def create_member(email="test_member@example.com", first_name="Member"):
	return create_user(email, first_name, "Gameplan Member")


def create_guest(email="test_guest@example.com", first_name="Guest"):
	return create_user(email, first_name, "Gameplan Guest")


def create_team(title="Test Team"):
	if frappe.db.exists("GP Team", {"title": title}):
		return frappe.get_doc("GP Team", {"title": title})
	return frappe.get_doc(doctype="GP Team", title=title).insert(ignore_permissions=True)


def create_project(title, team, is_private=0):
	return frappe.get_doc(doctype="GP Project", title=title, team=team, is_private=is_private).insert(
		ignore_permissions=True
	)


def create_discussion(title, project, content="Test content"):
	return frappe.get_doc(doctype="GP Discussion", title=title, project=project, content=content).insert(
		ignore_permissions=True
	)


def grant_guest_access(user, project):
	if frappe.db.exists("GP Guest Access", {"user": user, "project": project}):
		return frappe.get_doc("GP Guest Access", {"user": user, "project": project})
	return frappe.get_doc(doctype="GP Guest Access", user=user, project=project).insert(
		ignore_permissions=True
	)
