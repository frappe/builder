from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in website_builder/__init__.py
from website_builder import __version__ as version

setup(
	name="website_builder",
	version=version,
	description="Create beautiful websites with few clicks",
	author="Frappe",
	author_email="developers@frappe.io",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
