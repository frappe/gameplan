# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors

from ..gp_project_visit import add_indexes


def execute():
	"""Add (user, project) index GP Project Visit"""
	add_indexes()
