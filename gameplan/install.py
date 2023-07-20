# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe

def before_install():
	check_frappe_version()

def after_install():
	download_rembg_model()

def check_frappe_version():
	from semantic_version import Version
	from frappe import __version__ as frappe_version

	if Version(frappe_version) < Version('15.0.0'):
		raise SystemExit('Gameplan requires Frappe Framework version 15 or above')

def download_rembg_model():
	from rembg import new_session
	new_session()
