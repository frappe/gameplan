# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import os
import subprocess

import frappe
from frappe import safe_decode
from frappe.utils import get_system_timezone
from frappe.utils.telemetry import capture

no_cache = 1


def get_context():
	login_as_demo_user_if_enabled()
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
			"app_version": get_app_version(),
			"system_timezone": get_system_timezone(),
		}
	)


def on_login(login_manager):
	frappe.response["default_route"] = get_default_route()


def get_default_route():
	if not frappe.db.get_all("GP Project", limit=1):
		return "/onboarding"
	else:
		return "/home"


def get_app_version():
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
	try:
		with open(os.devnull, "wb") as null_stream:
			result = subprocess.check_output(command, shell=True, stdin=null_stream, stderr=null_stream)
		return safe_decode(result).strip()
	except Exception:
		frappe.log_error(
			title="Git Command Error",
		)
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

	from gameplan.demo.discussions_comments import get_random_users

	# login as a random demo user
	users = get_random_users(10)
	if not users:
		frappe.throw("No demo users found")

	random_user = choice(users)
	frappe.local.login_manager.login_as(random_user)
