
__version__ = '0.0.1'

def is_guest():
	import frappe

	if frappe.session.user == 'Administrator':
		return False
	return 'Gameplan Guest' in frappe.get_roles()
