from ..gp_moderation_log import on_doctype_update


def execute():
	"""Install latest-log indexes on existing sites."""
	on_doctype_update()
