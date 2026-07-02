import frappe
from frappe.utils import cint

PUBLIC_WEB_VISIBILITY = "Public Web"


def is_enabled():
	return cint(frappe.conf.get("gameplan_public_web_enabled")) == 1


def is_anonymous_user(user=None):
	return (user or frappe.session.user) == "Guest"


def can_anonymous_read():
	return is_anonymous_user() and is_enabled()


def is_public_web_space(project):
	if not project:
		return False
	if getattr(project, "visibility", None) == PUBLIC_WEB_VISIBILITY:
		return is_enabled()
	return False
