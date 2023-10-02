from . import __version__ as app_version

app_name = "gameplan"
app_title = "Gameplan"
app_publisher = "Frappe Technologies Pvt Ltd"
app_description = "Team discussion and collaboration tool"
app_email = "faris@frappe.io"
app_license = "AGPLv3"
app_icon_url = "/assets/gameplan/manifest/favicon-180.png"
app_icon_title = "Gameplan"
app_icon_route = "/g"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/gameplan/css/gameplan.css"
# app_include_js = "/assets/gameplan/js/gameplan.js"

# include js, css files in header of web template
# web_include_css = "/assets/gameplan/css/gameplan.css"
# web_include_js = "/assets/gameplan/js/gameplan.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "gameplan/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Fixtures

fixtures = [
	{"dt": "Role", "filters": [["role_name", "like", "Gameplan %"]]},
]

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

website_route_rules = [
	{"from_route": "/g/<path:app_path>", "to_route": "g"},
]

website_redirects = [
	{"source": r"/teams(/.*)?", "target": r"/g\1"},
]

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "gameplan.utils.jinja_methods",
# 	"filters": "gameplan.utils.jinja_filters"
# }

# Installation
# ------------

before_install = "gameplan.install.before_install"
after_install = "gameplan.install.after_install"

after_migrate = ["gameplan.search.build_index_in_background"]

# Uninstallation
# ------------

# before_uninstall = "gameplan.uninstall.before_uninstall"
# after_uninstall = "gameplan.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "gameplan.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"*": {
		"on_trash": "gameplan.mixins.on_delete.on_trash",
	},
	"User": {
		"after_insert": "gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.create_user_profile",
		"on_trash": [
			"gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.delete_user_profile",
			"gameplan.gameplan.doctype.gp_guest_access.gp_guest_access.on_user_delete",
		],
		"on_update": "gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.on_user_update"
	}
}

on_login = 'gameplan.www.g.on_login'

# Scheduled Tasks
# ---------------

scheduler_events = {
	"all": [
		"gameplan.search.build_index_if_not_exists"
	],
	"hourly": [
		"gameplan.gameplan.doctype.gp_invitation.gp_invitation.expire_invitations"
	],
}

# scheduler_events = {
# 	"all": [
# 		"gameplan.tasks.all"
# 	],
# 	"daily": [
# 		"gameplan.tasks.daily"
# 	],
# 	"hourly": [
# 		"gameplan.tasks.hourly"
# 	],
# 	"weekly": [
# 		"gameplan.tasks.weekly"
# 	],
# 	"monthly": [
# 		"gameplan.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "gameplan.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.client.get_list": "gameplan.extends.client.get_list"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "gameplan.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"gameplan.auth.validate"
# ]

# Translation
# --------------------------------

# Make link fields search translated document names for these DocTypes
# Recommended only for DocTypes which have limited documents with untranslated names
# For example: Role, Gender, etc.
# translated_search_doctypes = []
