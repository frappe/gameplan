# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors

import frappe

# Project-linked doctypes carrying a denormalized `team` field. The field is
# fetched from `project.team`, but `fetch_from` is new — existing rows were never
# re-saved, so they can carry a null/empty `team` and become invisible in every
# community feed.
PROJECT_LINKED_DOCTYPES = [
	"GP Discussion",
	"GP Task",
	"GP Page",
	"GP Draft",
	"GP Notification",
	"GP Project Visit",
	"GP Pinned Project",
	"GP Guest Access",
	"GP Followed Project",
]


def execute():
	assign_orphaned_spaces_to_default()
	backfill_denormalized_team()


def assign_orphaned_spaces_to_default():
	"""Existing sites only: move spaces with no community into a `Default` community."""
	orphaned_spaces = frappe.db.get_all(
		"GP Project",
		filters={"team": ["in", ["", None]]},
		pluck="name",
	)
	if not orphaned_spaces:
		# Fully-categorized site: do not create `Default`.
		return

	default_team = ensure_default_team()
	frappe.db.set_value(
		"GP Project",
		{"name": ["in", orphaned_spaces]},
		"team",
		default_team,
		update_modified=False,
	)


def ensure_default_team():
	existing = frappe.db.exists("GP Team", {"title": "Default"})
	if existing:
		return existing

	team = frappe.new_doc("GP Team")
	team.title = "Default"
	# Suppress the General auto-create hook: the orphaned spaces are assigned to
	# Default right after, so it must not land with a stray General space first.
	team.flags.skip_general_space = True
	team.insert(ignore_permissions=True)
	return team.name


def backfill_denormalized_team():
	"""Run unconditionally: a fully-categorized site can still have null-`team` rows."""
	for doctype in PROJECT_LINKED_DOCTYPES:
		table = f"tab{doctype}"
		# Correlated-subquery form (instead of UPDATE ... JOIN) so the patch runs on
		# both MariaDB and SQLite; the EXISTS guard limits the update to rows whose
		# project actually carries a team, matching the original INNER JOIN. The table
		# name comes from PROJECT_LINKED_DOCTYPES, and SQL cannot take it as a parameter.
		frappe.db.sql(  # nosemgrep: frappe-sql-format-injection
			f"""
			UPDATE `{table}`
			SET team = (
				SELECT project.team FROM `tabGP Project` AS project
				WHERE project.name = `{table}`.project
			)
			WHERE (team IS NULL OR team = '')
				AND EXISTS (
					SELECT 1 FROM `tabGP Project` AS project
					WHERE project.name = `{table}`.project
						AND project.team IS NOT NULL AND project.team != ''
				)
			"""
		)
