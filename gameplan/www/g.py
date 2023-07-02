# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe

no_cache = 1


def get_context():
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()
	_context = _get_context()
	_context.csrf_token = csrf_token
	return _context

@frappe.whitelist(methods=['POST'])
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw('This method is only meant for developer mode')
	return _get_context()

def _get_context():
	return frappe._dict({
		'frappe_version': frappe.__version__,
		'default_route': get_default_route()
	})

def on_login(login_manager):
	frappe.response['default_route'] = get_default_route()

def get_default_route():
	if not frappe.db.get_all('GP Team', limit=1):
		return '/onboarding'
	else:
		return '/home'
