# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe

no_cache = 1


def get_context(context):
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()
	context.csrf_token = csrf_token
	context.default_route = get_default_route()

def on_login(login_manager):
	frappe.response['default_route'] = get_default_route()

def get_default_route():
	if not frappe.db.get_all('Team', limit=1):
		return '/onboarding'
	else:
		return '/home'
