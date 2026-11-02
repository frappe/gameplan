from functools import reduce
from operator import and_

import frappe


def latest_logs(keys, actions):
	"""Select the last matching log per target without loading its history."""
	Log = frappe.qb.DocType("GP Moderation Log")
	Newer = Log.as_("newer_log")
	same_target = reduce(and_, (Newer[key] == Log[key] for key in keys))
	later = (Newer.creation > Log.creation) | ((Newer.creation == Log.creation) & (Newer.name > Log.name))
	return (
		frappe.qb.from_(Log)
		.left_join(Newer)
		.on(same_target & Newer.action.isin(actions) & later)
		.where(Log.action.isin(actions) & Newer.name.isnull())
	)
