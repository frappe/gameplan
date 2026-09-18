# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import os
import subprocess

import frappe
from frappe import _, safe_decode
from frappe.core.api.file import get_max_file_size
from frappe.utils import get_system_timezone
from frappe.utils.telemetry import capture

from gameplan.gameplan.doctype.gp_settings.gp_settings import get_offline_downloads_settings
from gameplan.roles import has_app_access

no_cache = 1


def get_context():
	login_as_demo_user_if_enabled()
	require_app_access()
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()
	context = frappe._dict()
	context.boot = get_boot()
	context.boot.csrf_token = csrf_token
	if frappe.session.user != "Guest":
		capture("active_site", "gameplan")
	return context


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw("This method is only meant for developer mode")
	return get_boot()


def get_boot():
	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"default_route": get_default_route(),
			"site_name": frappe.local.site,
			"read_only_mode": frappe.flags.read_only,
			"gameplan_frontend_sentry_dsn": frappe.conf.gameplan_frontend_sentry_dsn,
			"max_file_size": get_max_file_size(),
			"app_version": get_app_version(),
			"system_timezone": get_system_timezone(),
			"offline_downloads": get_offline_downloads_settings(),
		}
	)


def require_app_access():
	"""Deny /g to a signed-in user who holds no Gameplan role.

	Frappe renders a PermissionError from a www page as `NotPermittedPage`: HTTP 403,
	this message, and a way out. Which way out depends on the frappe version, so do not
	rely on it: version-16 always offers Login, develop offers Home to a signed-in user.
	Without this gate the SPA loads, every list call is denied, and the router mistakes
	the empty result for an empty site and shows onboarding.

	Guest falls through on purpose. Someone who has not signed in yet should be sent to
	/login by the SPA, not told they lack a role.
	"""
	if frappe.session.user == "Guest" or has_app_access():
		return

	frappe.throw(
		_("You do not have access to Gameplan. Ask an admin to invite you."),
		frappe.PermissionError,
	)


def on_login(login_manager):
	frappe.response["default_route"] = get_default_route()


def get_default_route():
	# Onboarding is only for brand-new sites with no data at all. A site with
	# projects-but-no-teams is fixed by the migration (creates Default); a site with
	# teams-but-no-projects is fixed by the GP Team after_insert hook (creates General).
	has_projects = bool(frappe.db.get_all("GP Project", limit=1))
	has_teams = bool(frappe.db.get_all("GP Team", limit=1))
	if not has_projects and not has_teams:
		return "/onboarding"
	return "/home"


APP_VERSION_CACHE_KEY = "gameplan_app_version"
# Long enough that a burst of page loads costs one read, short enough that a commit made
# while working shows up in the About dialog without clearing the cache by hand.
APP_VERSION_CACHE_TTL = 60


def get_app_version():
	"""Branch, commit and tag of the running checkout, for the About dialog.

	Cached, because `get_boot` runs on every `/g` render and reading this costs six
	git processes. A deploy restarts the workers, so the value cannot outlive the
	checkout it describes by more than the TTL.
	"""
	version = frappe.cache.get_value(APP_VERSION_CACHE_KEY)
	if version is None:
		version = read_app_version()
		frappe.cache.set_value(APP_VERSION_CACHE_KEY, version, expires_in_sec=APP_VERSION_CACHE_TTL)
	return version


def read_app_version():
	app = "gameplan"
	branch = run_git_command(f"cd ../apps/{app} && git rev-parse --abbrev-ref HEAD")
	commit = run_git_command(f"git -C ../apps/{app} rev-parse --short=7 HEAD")
	tag = run_git_command(f"git -C ../apps/{app} describe --tags --abbrev=0")
	dirty = run_git_command(f"git -C ../apps/{app} diff --quiet || echo 'dirty'") == "dirty"
	commit_date = run_git_command(f"git -C ../apps/{app} log -1 --format=%cd")
	commit_message = run_git_command(f"git -C ../apps/{app} log -1 --pretty=%B")

	return {
		"branch": branch,
		"commit": commit,
		"commit_date": commit_date,
		"commit_message": commit_message,
		"tag": tag,
		"dirty": dirty,
	}


def run_git_command(command):
	"""Output of `command`, or an empty string when git cannot answer.

	Two kinds of failure, told apart on purpose:

	A non-zero exit or an unreachable git binary is expected, not exceptional. A
	deployed checkout is often shallow and carries no tags, so `git describe` fails on
	every call. Logging those wrote an Error Log row per git call per page load and
	buried real tracebacks under thousands of "Git Command Error" rows. A blank field
	in the About dialog is the only signal they need.

	Anything else keeps its traceback, so a genuinely broken version read stays
	diagnosable. It is still swallowed rather than raised: this runs inside `get_boot`,
	and version info that cannot be read must not take `/g` down with it.
	"""
	try:
		with open(os.devnull, "wb") as null_stream:
			result = subprocess.check_output(command, shell=True, stdin=null_stream, stderr=null_stream)
		return safe_decode(result).strip()
	except (subprocess.CalledProcessError, OSError):
		return ""
	except Exception:
		frappe.log_error(title="Git Command Error")
		return ""


def login_as_demo_user_if_enabled():
	if not frappe.form_dict.demo:
		return

	from gameplan.demo.demo import demo_data_enabled

	if not demo_data_enabled():
		frappe.throw("Not found", frappe.DoesNotExistError)

	if frappe.session.user != "Guest":
		return

	from random import choice

	from gameplan.demo.demo import get_random_users

	# login as a random demo user
	users = get_random_users(10)
	if not users:
		frappe.throw("No demo users found")

	random_user = choice(users)
	frappe.local.login_manager.login_as(random_user)
