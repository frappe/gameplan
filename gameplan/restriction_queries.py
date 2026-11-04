import frappe
from frappe.utils import cint

from gameplan.permissions import is_global_admin
from gameplan.restrictions import active_condition, iso_expiry


def require_scope(community=""):
	from gameplan.community_bans import can_moderate_community

	if not (can_moderate_community(community) if community else is_global_admin(frappe.session.user)):
		frappe.throw("You cannot view these restrictions", frappe.PermissionError)


def active_rows(community="", start=0, after=""):
	Restriction = frappe.qb.DocType("GP User Restriction")
	User = frappe.qb.DocType("User")
	query = (
		frappe.qb.from_(Restriction)
		.join(User)
		.on(User.name == Restriction.user)
		.select(
			Restriction.user,
			Restriction.reason,
			Restriction.expires_at,
			Restriction.modified,
			User.full_name,
			User.user_image,
		)
		.where((Restriction.community == community) & active_condition(Restriction))
	)
	if after:
		query = query.where(Restriction.user > after)
	rows = query.orderby(Restriction.user).offset(max(0, cint(start))).limit(41).run(as_dict=True)
	for row in rows:
		row.expires_at = iso_expiry(row.expires_at)
		row.modified = str(row.modified)
	return rows


@frappe.whitelist(methods=["GET", "POST"])
def account_suspensions(after: str = ""):
	"""List a cursor-paged set of active whole-site suspensions for global admins."""
	require_scope()
	rows = active_rows(after=after)
	return {
		"items": rows[:40],
		"has_more": len(rows) > 40,
		"next_cursor": rows[39].user if len(rows) > 40 else "",
	}


@frappe.whitelist(methods=["GET", "POST"])
def candidates(query: str = "", after: str = ""):
	"""Find eligible account-suspension targets in indexed, cursor-paged user results."""
	require_scope()
	query = (query or "").strip()
	if len(query) > 100:
		frappe.throw("Search text must be at most 100 characters")
	if len(query) == 1:
		return {"items": [], "has_more": False, "next_cursor": ""}
	User, Role, Restriction = [frappe.qb.DocType(dt) for dt in ("User", "Has Role", "GP User Restriction")]
	admins = (
		frappe.qb.from_(Role)
		.select(Role.parent)
		.where((Role.parenttype == "User") & Role.role.isin(["Gameplan Admin", "System Manager"]))
	)
	suspended = (
		frappe.qb.from_(Restriction)
		.select(Restriction.user)
		.where((Restriction.community == "") & active_condition(Restriction))
	)
	users = (
		frappe.qb.from_(User)
		.select(User.name, User.full_name, User.user_image)
		.where(User.name.notin(["Administrator", "Guest", frappe.session.user]))
		.where(User.name.notin(admins))
		.where(User.name.notin(suspended))
	)
	if query:
		prefix = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
		users = users.where(User.name.like(prefix) | User.full_name.like(prefix))
	if after:
		users = users.where(User.name > after)
	rows = users.orderby(User.name).limit(21).run(as_dict=True)
	return {
		"items": rows[:20],
		"has_more": len(rows) > 20,
		"next_cursor": rows[19].name if len(rows) > 20 else "",
	}


@frappe.whitelist(methods=["GET", "POST"])
def account_history(user: str, before: str = ""):
	"""Read one user's site-suspension history; accessible only to global admins."""
	require_scope()
	Log = frappe.qb.DocType("GP Moderation Log")
	query = (
		frappe.qb.from_(Log)
		.select(
			Log.name, Log.action, Log.owner, Log.creation, Log.reason, Log.previous_expires_at, Log.expires_at
		)
		.where(
			(Log.user == user)
			& (Log.community == "")
			& Log.action.isin(["Suspend", "Suspension Changed", "Lift Suspension", "Restriction Expired"])
		)
	)
	if before:
		cursor = frappe.db.get_value("GP Moderation Log", before, ["creation", "name"], as_dict=True)
		if not cursor:
			frappe.throw("Refresh the history list")
		query = query.where(
			(Log.creation < cursor.creation) | ((Log.creation == cursor.creation) & (Log.name < cursor.name))
		)
	rows = (
		query.orderby(Log.creation, order=frappe.qb.desc)
		.orderby(Log.name, order=frappe.qb.desc)
		.limit(41)
		.run(as_dict=True)
	)
	for row in rows:
		row.expires_at = iso_expiry(row.expires_at)
		row.previous_expires_at = iso_expiry(row.previous_expires_at)

	return {
		"items": rows[:40],
		"has_more": len(rows) > 40,
		"next_cursor": rows[39].name if len(rows) > 40 else "",
	}


@frappe.whitelist(methods=["GET", "POST"])
def my_bans():
	"""Return the caller's active Community ban reasons and exact deadlines."""
	if frappe.session.user == "Guest" or is_global_admin(frappe.session.user):
		return []
	Restriction = frappe.qb.DocType("GP User Restriction")
	rows = (
		frappe.qb.from_(Restriction)
		.select(Restriction.community, Restriction.reason, Restriction.expires_at)
		.where(
			(Restriction.user == frappe.session.user)
			& (Restriction.community != "")
			& active_condition(Restriction)
		)
		.run(as_dict=True)
	)
	for row in rows:
		row.expires_at = iso_expiry(row.expires_at)
	return rows
