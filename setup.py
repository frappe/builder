from setuptools import find_packages, setup

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in builder/__init__.py
from builder import __version__ as version

setup(
	name="builder",
	version=version,
	author="Suraj Shetty",
	author_email="suraj@frappe.io",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
)
