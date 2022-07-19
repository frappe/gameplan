from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in gameplan/__init__.py
from gameplan import __version__ as version

setup(
	name="gameplan",
	version=version,
	description="Team discussion and collaboration tool",
	author="Frappe Technologies Pvt Ltd",
	author_email="faris@frappe.io",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
