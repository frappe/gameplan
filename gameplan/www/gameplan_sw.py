import frappe

no_cache = 1


def get_context(context):
	# The same script for everyone, so it goes out without a session cookie: Frappe sends none
	# with a public response. The browser checks it for updates in the background, and a check
	# begun before a login would otherwise put the previous user's session back when it ends.
	frappe.local.response_headers["Cache-Control"] = "public, no-cache"
