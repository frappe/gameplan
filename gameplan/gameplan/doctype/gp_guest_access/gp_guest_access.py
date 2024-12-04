# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

from gameplan.mixins.on_delete import delete_linked_records


class GPGuestAccess(Document):
	pass


def on_user_delete(doc, method):
	delete_linked_records("User", doc.name, ["GP Guest Access"])
