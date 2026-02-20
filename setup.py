import os.path
import re
from setuptools import setup


def _get_version() -> str:
    project_root = os.path.abspath(os.path.dirname(__file__))
    version_file = os.path.join(project_root, "lavalink", "__init__.py")
    with open(version_file) as fp:
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", fp.read(), re.M)

    if not version_match:
        raise RuntimeError("Unable to find version string.")
    raw_version = version_match.group(1)

    if not raw_version.endswith(".dev1"):
        return raw_version

    methods = [
        _get_version_from_git_repo,
        _get_version_from_sdist_pkg_info,
        _get_version_from_git_archive,
    ]
    exceptions = []
    for method in methods:
        try:
            version = method(project_root, raw_version)
        except Exception as exc:
            exceptions.append(exc)
        else:
            break
    else:
        import traceback

        for exc in exceptions:
            traceback.print_exception(None, exc, exc.__traceback__)
            exc.__traceback__ = None

        version = raw_version

    return version


def _get_version_from_git_repo(project_root: str, raw_version: str) -> str:
    # we only want to do this for editable installs
    if not os.path.exists(os.path.join(project_root, ".git")):
        raise RuntimeError("not a git repository")

    import subprocess

    output = subprocess.check_output(
        ("git", "describe", "--tags", "--long", "--dirty"),
        stderr=subprocess.DEVNULL,
        cwd=project_root,
    )
    _, count, commit, *dirty = output.decode("utf-8").strip().split("-", 3)
    dirty_suffix = f".{dirty[0]}" if dirty else ""
    return f"{raw_version[:-1]}{count}+{commit}{dirty_suffix}"


def _get_version_from_git_archive(project_root: str, raw_version: str) -> str:
    with open(os.path.join(project_root, ".git_archive_info.txt"), encoding="utf-8") as fp:
        commit, describe_name = fp.read().splitlines()
        if not describe_name:
            raise RuntimeError("git archive's describe didn't output anything")
        if "%(describe" in describe_name:
            # either git-archive was generated with Git < 2.35 or this is not a git-archive
            raise RuntimeError("git archive did not support describe output")
        _, _, suffix = describe_name.partition("-")
        if suffix:
            count, _, _ = suffix.partition("-")
        else:
            count = "0"
        return f"{raw_version[:-1]}{count}+g{commit}"


def _get_version_from_sdist_pkg_info(project_root: str, raw_version: str) -> str:
    pkg_info_path = os.path.join(project_root, "PKG-INFO")
    if not os.path.exists(pkg_info_path):
        raise RuntimeError("not an sdist")

    import email

    with open(pkg_info_path, encoding="utf-8") as fp:
        return email.message_from_file(fp)["Version"]


setup(version=_get_version())
