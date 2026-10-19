import frappe
from frappe.utils import sha256_hash

SHA256_HEX_LENGTH = 64


def execute():
	"""Store each invitation's key as its hash, which is what accept_invitation now looks up.

	Links already sent by email carry the plain key, so they keep working. Plain keys were
	12 characters long, so a 64-character key is already a hash and is left as it is. This
	makes a second run change nothing.
	"""
	invitations = frappe.get_all("GP Invitation", filters={"key": ["is", "set"]}, fields=["name", "key"])
	for invitation in invitations:
		if len(invitation.key) == SHA256_HEX_LENGTH:
			continue
		frappe.db.set_value(
			"GP Invitation", invitation.name, "key", sha256_hash(invitation.key), update_modified=False
		)
