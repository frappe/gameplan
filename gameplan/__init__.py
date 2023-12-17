import importlib.metadata
import frappe

__version__ = importlib.metadata.version(__name__)

def is_guest():
	if frappe.session.user == 'Administrator':
		return False
	roles = frappe.get_roles()
	if 'Gameplan Member' in roles or 'Gameplan Admin' in roles:
		return False
	return 'Gameplan Guest' in roles

def refetch_resource(cache_key: str | list, user=None):
	frappe.publish_realtime(
		'refetch_resource',
		{'cache_key': cache_key},
		user=user or frappe.session.user,
		after_commit=True
	)
