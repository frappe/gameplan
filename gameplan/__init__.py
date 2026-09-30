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


def is_anonymous(user=None):
	"""Return True if nobody is signed in.

	Not the same question as is_guest(). A Gameplan Guest is a signed-in outside
	collaborator who holds the Gameplan Guest role. Someone who is not signed in holds no
	Gameplan role at all, so is_guest() returns False for them.
	"""
	return (user or frappe.session.user) == "Guest"


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
