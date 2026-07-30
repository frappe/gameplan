import frappe

__version__ = "0.0.1"


def is_guest(user=None):
	if not user:
		user = frappe.session.user

	if user == "Administrator":
		return False
	roles = frappe.get_roles(user)
	if "Gameplan Member" in roles or "Gameplan Admin" in roles:
		return False
	return "Gameplan Guest" in roles


def is_admin(user=None):
	"""Return True if the user may manage members (roles, invites, removal).

	Administrator and the System Manager are always admins; otherwise the user
	must hold the Gameplan Admin role. Mirrors is_guest() so both gates resolve
	roles through the same (Redis-cached) frappe.get_roles path.
	"""
	if not user:
		user = frappe.session.user

	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	return "Gameplan Admin" in roles or "System Manager" in roles
