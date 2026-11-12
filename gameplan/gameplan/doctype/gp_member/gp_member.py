# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe

from gameplan.mixins.parent_managed_child import ParentManagedChild


class GPMember(ParentManagedChild):
	pass


def on_doctype_update():
	# Is this user a member, admin or moderator of this Community or Space? Every moderation
	# check asks. The default index covers only the parent, so a Community with 50,000 members
	# read 50,000 rows for each answer.
	frappe.db.add_index("GP Member", ["parent", "parenttype", "user"], "parent_user")
	# Community staff lists filter on both flags; with them in the index MariaDB stops scanning
	# every member of a large Community (0.4 s with 20,000 members).
	frappe.db.add_index(
		"GP Member", ["parent", "parenttype", "is_admin", "is_moderator", "user"], "community_staff"
	)
