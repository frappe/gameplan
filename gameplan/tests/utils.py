# Copyright (c) 2024, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Shared helpers for creating test fixtures (users, teams, projects, etc.)."""

import frappe

from gameplan.tests.fixtures import create_user as create_user
from gameplan.visibility import VISIBILITY_GENERAL


def create_member(email="test_member@example.com", first_name="Member"):
	return create_user(email, first_name, "Gameplan Member")


def create_guest(email="test_guest@example.com", first_name="Guest"):
	return create_user(email, first_name, "Gameplan Guest")


def create_team(title="Test Team"):
	if frappe.db.exists("GP Team", {"title": title}):
		return frappe.get_doc("GP Team", {"title": title})
	return frappe.get_doc(doctype="GP Team", title=title).insert(ignore_permissions=True)


def create_project(title, team, visibility=VISIBILITY_GENERAL):
	return frappe.get_doc(doctype="GP Project", title=title, team=team, visibility=visibility).insert(
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
