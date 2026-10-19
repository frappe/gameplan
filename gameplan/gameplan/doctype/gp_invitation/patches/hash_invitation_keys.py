import frappe
from frappe.utils import sha256_hash


def execute():
	"""Store each invitation's key as its hash, which is what accept_invitation now looks up.

	Links already sent by email carry the plain key, so they keep working.
	"""
	invitations = frappe.get_all("GP Invitation", filters={"key": ["is", "set"]}, fields=["name", "key"])
	for invitation in invitations:
		frappe.db.set_value(
			"GP Invitation", invitation.name, "key", sha256_hash(invitation.key), update_modified=False
		)
