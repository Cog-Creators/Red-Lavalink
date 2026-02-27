import os
import re
import sys
from typing import Any, Match

from packaging.version import Version

GITHUB_OUTPUT = os.environ["GITHUB_OUTPUT"]
GITHUB_STEP_SUMMARY = os.environ["GITHUB_STEP_SUMMARY"]
VERSION_RE = re.compile(r'^__version__ = "(?P<version>[^"]*)"$', re.MULTILINE)
PACKAGE_NAME = "lavalink"
PACKAGE_INIT = f"{PACKAGE_NAME}/__init__.py"


def set_output(name: str, value: Any) -> None:
    with open(GITHUB_OUTPUT, "a", encoding="utf-8") as fp:
        fp.write(f"{name}={value}\n")


def append_to_job_summary(text: str) -> None:
    with open(GITHUB_STEP_SUMMARY, "a", encoding="utf-8") as fp:
        fp.write(f"{text}\n")


if int(os.environ.get("JUST_RETURN_VERSION", 0)):
    with open(PACKAGE_INIT, encoding="utf-8") as fp:
        match = VERSION_RE.search(fp.read())
        if match is None:
            print("Couldn't find `__version__` line!", file=sys.stderr)
            sys.exit(1)
        version = Version(match.group("version"))
        set_output("version", version)
        set_output("is_prerelease", int(version.is_prerelease))
        sys.exit(0)


new_version = None


def repl(match: Match[str]) -> str:
    global new_version

    set_output("old_version", match.group("version"))

    new_version_spec = os.environ.get("NEW_VERSION_SPEC", "auto")
    if new_version_spec == "auto":
        old_version = Version(match.group("version"))
        # DEP-WARN: use copy.replace() in a few years when 3.13 becomes lower-bound
        new_version = old_version.__replace__(dev=None)
    else:
        new_version = Version(new_version_spec)

    if int(os.environ.get("DEV_BUMP", 0)):
        # DEP-WARN: use copy.replace() in a few years when 3.13 becomes lower-bound
        new_version = new_version.__replace__(
            release=new_version.release[:-1] + (new_version.release[-1] + 1,),
            dev=1,
        )

    return f'__version__ = "{new_version}"'


with open(PACKAGE_INIT, encoding="utf-8") as fp:
    new_contents, found = VERSION_RE.subn(repl, fp.read(), count=1)

if not found:
    print("Couldn't find `__version__` line!", file=sys.stderr)
    sys.exit(1)

with open(PACKAGE_INIT, "w", encoding="utf-8", newline="\n") as fp:
    fp.write(new_contents)

set_output("new_version", new_version)
print("New version set to:", new_version)
append_to_job_summary(f"-   New version set to **{new_version}**")
