from zoneinfo import ZoneInfo

import frappe
from frappe.utils import escape_html, get_system_timezone


def notify(user, community, action, reason, expires_at=None):
	"""Queue an email explaining a committed restriction change in the recipient's timezone."""
	from datetime import datetime

	timezone = frappe.db.get_value("User", user, "time_zone") or get_system_timezone()
	if expires_at:
		expiry = datetime.fromisoformat(expires_at).astimezone(ZoneInfo(timezone))
		deadline = f"{expiry.strftime('%d %b %Y, %H:%M %z')} ({timezone})"
	else:
		deadline = "Until manually lifted"
	scope = (
		frappe.db.get_value("GP Team", community, "title")
		if community
		else "Entire Frappe site (all installed apps)"
	)
	lifted = action in ("Unban", "Lift Suspension")
	message = f"<p>{escape_html(action)}: {escape_html(scope or community)}</p><p>{escape_html(reason)}</p>"
	if not lifted:
		message += f"<p>Expires: {escape_html(deadline)}</p>"
	frappe.sendmail(recipients=[user], subject=f"Account moderation: {action}", message=message)
