# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""The roles Gameplan assigns to its users, and the code that sets them up.

These used to ship as a `Role` fixture. Fixture sync is not an upsert: `import_doc`
deletes the old row and re-inserts it, and a fresh insert has no "before save" doc, so
`has_value_changed("desk_access")` is always true. That made `Role.on_update` re-evaluate
every user holding a Gameplan role on *every* `bench migrate` — and on frappe v16 the
resulting user save crashes migrate outright, because `User.on_update` enqueues
`create_contact` with the lazily-loaded user document and the dynamically built
`LazyUser` class cannot be pickled (fixed upstream in frappe#41187, not on version-16).

Hence two entry points, because install and migrate own different things:

- `setup_roles()` runs at install, where Gameplan defines what its roles mean. It forces
  `desk_access = 0` so members are Website Users. It has to *correct* the value rather
  than just create the roles: `install_app` syncs doctypes before calling `after_install`,
  and frappe's `make_module_and_roles` will already have created every role named in a
  doctype's permissions with `desk_access = 1`. Writing here is safe because
  `frappe.flags.in_install` makes `Role.on_update` return early.

- `sync_roles()` runs after migrate and only creates roles that went missing. It must
  never write to an existing Role. Beyond re-triggering the crash above, a failed write
  inside migrate is a *deadlock*: the exception rolls migrate back, so the write never
  lands and the next migrate retries it identically. And `desk_access` on a live site is
  the operator's call — it decides System User vs Website User, which governs desk access
  and Frappe Cloud billing. gameplan.frappe.cloud deliberately runs Gameplan Member and
  Gameplan Admin with `desk_access = 1`; resetting it would demote ~80 accounts.
"""

import frappe

# Ascending order of privilege. A user may hold more than one; the last match wins.
GAMEPLAN_ROLES = ("Gameplan Guest", "Gameplan Member", "Gameplan Admin")


def setup_roles():
	"""Install-time setup: the Gameplan roles exist and none of them grant desk access."""
	for role_name in GAMEPLAN_ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc(doctype="Role", role_name=role_name, desk_access=0).insert(ignore_permissions=True)
		elif frappe.db.get_value("Role", role_name, "desk_access"):
			role = frappe.get_doc("Role", role_name)
			role.desk_access = 0
			role.save(ignore_permissions=True)


def sync_roles():
	"""Post-migrate repair: create roles that went missing, and touch nothing else.

	Report — rather than fix — a role that grants desk access. Deleting a Gameplan role
	gets it recreated by `make_module_and_roles` with `desk_access = 1` during the same
	migrate's doctype sync, and this cannot silently correct that: the write would demote
	users, and if it raised it would roll migrate back and retry forever. Whether a
	Gameplan role grants desk access is the operator's call either way, so say what is
	true and let them decide.
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

	if granting_desk_access := sorted(
		role for role, desk_access in desk_access_by_role.items() if desk_access
	):
		print(
			f"Gameplan roles granting desk access: {', '.join(granting_desk_access)}. "
			"Users holding them are System Users. Set desk_access = 0 if that is not intended."
		)
