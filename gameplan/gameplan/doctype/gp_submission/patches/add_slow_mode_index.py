from ..gp_submission import on_doctype_update


def execute():
	"""Install the discussion-author submission index on existing sites."""
	on_doctype_update()
