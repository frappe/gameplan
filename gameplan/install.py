# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def after_install():
	download_rembg_model()

def download_rembg_model():
	from rembg import new_session
	new_session()
