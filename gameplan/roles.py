# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""The roles Gameplan assigns to its users, and the code that keeps them in shape.

These used to ship as a `Role` fixture. Fixture sync is not an upsert: `import_doc`
deletes the old row and re-inserts it, and a fresh insert has no "before save" doc, so
`has_value_changed("desk_access")` is always true. That made `Role.on_update` re-evaluate
every user holding a Gameplan role on *every* `bench migrate`, re-saving some of them for
no reason — and on frappe v16 that re-save crashes migrate outright, because
`User.on_update` enqueues `create_contact` with the lazily-loaded user document and the
dynamically built `LazyUser` class cannot be pickled (fixed upstream in frappe#41187,
not yet on version-16).

Creating the roles from code keeps the same invariant with none of the churn: it writes
only when a role is missing or has drifted.
"""

import frappe

# Ascending order of privilege. A user may hold more than one; the last match wins.
GAMEPLAN_ROLES = ("Gameplan Guest", "Gameplan Member", "Gameplan Admin")


def sync_roles():
	"""Ensure the Gameplan roles exist and none of them grant desk access.

	Roles named in a doctype's permissions are auto-created by frappe's
	`make_module_and_roles` with `desk_access = 1`, which would make every Gameplan
	member a System User. Correcting drift goes through `Role.save()` rather than a
	direct `db.set_value` so frappe re-evaluates the affected users' `user_type`.
	"""
	desk_access_by_role = dict(
		frappe.get_all(
			"Role",
			filters={"name": ("in", GAMEPLAN_ROLES)},
			fields=["name", "desk_access"],
			as_list=True,
		)
	)

	for role_name in GAMEPLAN_ROLES:
		if role_name not in desk_access_by_role:
			frappe.get_doc(doctype="Role", role_name=role_name, desk_access=0).insert(ignore_permissions=True)
		elif desk_access_by_role[role_name]:
			role = frappe.get_doc("Role", role_name)
			role.desk_access = 0
			role.save(ignore_permissions=True)
