# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""The roles Gameplan assigns to its users, and the code that creates them.

These used to ship as a `Role` fixture. Fixture sync is not an upsert: `import_doc`
deletes the old row and re-inserts it, and a fresh insert has no "before save" doc, so
`has_value_changed("desk_access")` is always true. That made `Role.on_update` re-evaluate
every user holding a Gameplan role on *every* `bench migrate` — and on frappe v16 the
resulting user save crashes migrate outright, because `User.on_update` enqueues
`create_contact` with the lazily-loaded user document and the dynamically built
`LazyUser` class cannot be pickled (fixed upstream in frappe#41187, not on version-16).

So this module creates roles that are missing and otherwise **never writes to an existing
Role**. Two reasons, and the second is the important one:

- Writing re-triggers the crash above, from a hook that runs inside migrate. Since the
  failure aborts and rolls back migrate, the write never lands and the next migrate tries
  the exact same write — a permanent deadlock rather than a one-off error.
- `desk_access` on a live site is an operator's call, not ours. It decides whether members
  are System Users or Website Users, which controls desk access and Frappe Cloud billing.
  gameplan.frappe.cloud has run with `desk_access = 1` on Gameplan Member and Admin since
  someone set it deliberately; resetting it would silently demote ~80 accounts.
"""

import frappe

# Ascending order of privilege. A user may hold more than one; the last match wins.
GAMEPLAN_ROLES = ("Gameplan Guest", "Gameplan Member", "Gameplan Admin")


def sync_roles():
	"""Create any Gameplan role that does not exist yet. Never modify one that does.

	New roles are created without desk access, so Gameplan members are Website Users by
	default. This matters because frappe's `make_module_and_roles` auto-creates roles named
	in a doctype's permissions with `desk_access = 1` — getting in first is the only way to
	pick the default, and once a role exists its `desk_access` belongs to the operator.
	"""
	existing = set(frappe.get_all("Role", filters={"name": ("in", GAMEPLAN_ROLES)}, pluck="name"))

	for role_name in GAMEPLAN_ROLES:
		if role_name not in existing:
			frappe.get_doc(doctype="Role", role_name=role_name, desk_access=0).insert(ignore_permissions=True)
