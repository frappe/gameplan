import frappe


def execute():
	# The column defaults cover rows created after the fields exist; profiles that were
	# already there get the same starting values written explicitly, so "never opened
	# settings" means the same thing for every user.
	profile = frappe.qb.DocType("GP User Profile")
	(
		frappe.qb.update(profile)
		.set(profile.notification_level, "Mentions only")
		.where(profile.notification_level.isnull() | (profile.notification_level == ""))
	).run()
	(
		frappe.qb.update(profile)
		.set(profile.watch_own_discussions, 0)
		.where(profile.watch_own_discussions.isnull())
	).run()
	(
		frappe.qb.update(profile).set(profile.notify_reactions, 1).where(profile.notify_reactions.isnull())
	).run()
	(
		frappe.qb.update(profile).set(profile.notify_poll_votes, 1).where(profile.notify_poll_votes.isnull())
	).run()
