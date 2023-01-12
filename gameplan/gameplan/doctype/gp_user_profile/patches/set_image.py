# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	UserProfile = frappe.qb.DocType('GP User Profile')
	User = frappe.qb.DocType('User')
	query = (
		frappe.qb.update(UserProfile)
			.set(UserProfile.image, User.user_image)
			.left_join(User).on(UserProfile.user == User.name)
			.where(User.user_image.isnotnull())
	)
	query.run()
