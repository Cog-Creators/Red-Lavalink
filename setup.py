import os.path
import re
from setuptools import setup

root_dir = os.path.abspath(os.path.dirname(__file__))
version_file = os.path.join(root_dir, "lavalink", "__init__.py")

with open(version_file) as fp:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", fp.read(), re.M)
    if not version_match:
        raise RuntimeError("Unable to find version string.")
    version = version_match.group(1)

setup(version=version)
