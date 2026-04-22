import frappe


def execute():
	frappe.db.sql(
		"""
		update `tabGP Comment` comment
		inner join (
			select docname, max(creation) as edited_at
			from `tabVersion`
			where ref_doctype = 'GP Comment'
				and data like %s
			group by docname
		) revisions on revisions.docname = comment.name
		set comment.edited_at = revisions.edited_at
		where comment.edited_at is null
		""",
		# Version.data stores changed fields as JSON arrays like ["content", old, new].
		('%["content",%',),
	)
