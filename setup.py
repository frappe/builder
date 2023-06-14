import os
import atexit
import subprocess
from setuptools import find_packages, setup
from setuptools.command.develop import develop

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in website_builder/__init__.py
from website_builder import __version__ as version


def install_playwright():
	python_path = os.path.join("..", "..", "env", "bin", "python")
	print(subprocess.run(f"{python_path} -m playwright install chromium", shell=True))


class RunDevelopCommand(develop):
	def __init__(self, *args, **kwargs):
		super(RunDevelopCommand, self).__init__(*args, **kwargs)
		# This is a hack to ensure that the command is run
		# after all the dependencies are installed
		atexit.register(install_playwright)


setup(
	name="website_builder",
	version=version,
	author="Suraj Shetty",
	author_email="surajshetty3416@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
	cmdclass={
		"develop": RunDevelopCommand,
	},
)
