import frappe


def execute():
	"""The digest is weekly only for now. Keep people who chose Fortnightly or Monthly
	subscribed by moving them to Weekly instead of turning their digest off."""
	profile = frappe.qb.DocType("GP User Profile")
	(
		frappe.qb.update(profile)
		.set(profile.email_digest_frequency, "Weekly")
		.where(profile.email_digest_frequency.isin(["Fortnightly", "Monthly"]))
	).run()
