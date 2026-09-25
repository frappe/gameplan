# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


def before_install():
	check_frappe_version()


def after_install():
	from gameplan.roles import setup_roles

	setup_roles()
	download_rembg_model()
	enqueue_search_index_build()


def check_frappe_version():
	from frappe import __version__
	from semantic_version import Version

	frappe_version = Version(__version__)
	if (frappe_version.major or 0) < 16:
		raise SystemExit("Gameplan requires Frappe Framework version 16 or above")


def enqueue_search_index_build():
	# Frappe builds the index only after a migrate, or every 3 hours from the scheduler.
	# Until then search fails on a new site, so start the build now.
	from gameplan.search_sqlite import enqueue_index_build

	enqueue_index_build()


def download_rembg_model():
	try:
		from rembg import new_session

		new_session()
	except ImportError:
		# rembg is optional dependency, skip if not installed
		pass
