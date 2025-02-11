#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Helper fine to run tasks on all plugins."""

import functools
import shlex
import shutil
from pathlib import Path
from typing import Callable, Optional

import nox
import nox.command
import tomli
from nox.logger import logger

nox.options.default_venv_backend = "uv|venv"
nox.options.reuse_venv = "yes"
nox.options.stop_on_first_error = True

THIS_DIR = Path(__file__).parent


def get_projects() -> list[str]:
    data = tomli.loads(THIS_DIR.joinpath("pyproject.toml").read_text(encoding="utf-8"))
    projects = data["tool"]["release-tools"]["clr"]["package_directories"]
    logger.info(f"Projects found: {', '.join(projects) }")
    return projects


def get_requirements(pyproject: Path) -> list[str]:
    data = tomli.loads(pyproject.read_text(encoding="utf-8"))
    if not data.get("project"):
        return []
    dynamic = data["project"].get("dynamic")
    if dynamic and "dependencies" in dynamic:
        req_file_name = data["tool"]["setuptools"]["dynamic"]["dependencies"]["file"]
        req_file = pyproject.parent.joinpath(req_file_name[0])
        return shlex.split(req_file.read_text(encoding="utf-8"), comments=True)

    return data["project"].get("dependencies")


def get_dev_requirements(pyproject: Path) -> list[str]:
    requirements_dev = pyproject.parent.joinpath("requirements_dev.txt")
    if requirements_dev.exists():
        return shlex.split(
            requirements_dev.read_text(encoding="utf-8"),
            comments=True,
        )
    return []


def collect_dependencies(include_dev_deps: bool = False) -> list[str]:
    logger.info(f"Collecting: {include_dev_deps }")
    requirements: list[str] = []
    project_files = [THIS_DIR.joinpath(p, "pyproject.toml") for p in get_projects()]
    for project in project_files:
        logger.info(f"Processing: {project}")
        requirements.extend(get_requirements(project))
        if include_dev_deps:
            logger.info(f"Including development dependencies")
            requirements.extend(get_dev_requirements(project))
    requirements = list(set(requirements))
    requirements = list(filter(lambda x: not x.startswith("spsdk"), requirements))
    return requirements


def get_args_index(args: list[str], search: str) -> Optional[int]:
    if search not in args:
        return None
    return args.index(search)


def get_install_command(session: nox.Session) -> Callable[..., None]:
    install_fcn = (
        functools.partial(session.run, "uv", "pip", "install", "--upgrade")
        if session.venv_backend == "none"
        else session.install
    )
    return install_fcn


def remove_posargs(session: nox.Session, *args: str) -> None:
    for arg in args:
        arg_index = get_args_index(session.posargs, arg)
        if arg_index is not None:
            session.posargs.pop(arg_index)
            session.posargs.pop(arg_index)


@nox.session(default=False)
def venv(session: nox.Session) -> None:
    """Setup venv with all plugins and SPSDK. To use custom SPSDK use `--spsdk <repo-path>`."""
    install_fcn = get_install_command(session=session)

    spsdk_index = get_args_index(session.posargs, "--spsdk")
    if spsdk_index is not None:
        logger.info(f"--spsdk found on index {spsdk_index}")
        spsdk_path = session.posargs[spsdk_index + 1]
        if not Path(spsdk_path).exists():
            session.error(f"SPSDK Path {spsdk_path} doesn't exist")
        with session.chdir(spsdk_path):
            install_fcn(".[all]")
        remove_posargs(session, "--spsdk")
    else:
        # install spsdk from Nexus, use --prerelease to get the latest version
        # latest version that is not yet released publicly
        install_fcn("spsdk[all]", "--prerelease", "allow")
    dependencies = collect_dependencies(include_dev_deps=True)
    with session.chdir("codecheck"):
        install_fcn(".")
    install_fcn(*dependencies)

    for project in get_projects():
        if project == "codecheck":
            continue
        with session.chdir(project):
            install_fcn(".", "--no-deps")


@nox.session
def codecheck(session: nox.Session) -> None:
    """Run codecheck on all plugins. Session accepts same options as `codecheck`."""
    venv(session=session)
    remove_posargs(session, "--repository")

    failed = []
    for project in get_projects():
        with session.chdir(project):
            try:
                output_idx = get_args_index(session.posargs, "--output")
                if output_idx is None:
                    output_idx = get_args_index(session.posargs, "-o")
                if output_idx is not None:
                    report_dir = session.posargs[output_idx + 1]
                    # remove --output from posargs
                    session.posargs.pop(output_idx)
                    session.posargs.pop(output_idx)
                else:
                    report_dir = "reports"
                if session.python:
                    report_dir += f"-{session.python}"
                session.run("codecheck", *session.posargs, "-o", report_dir)
            except nox.command.CommandFailed:
                failed.append(project)
                session.warn(f"Codecheck for {project} failed!")
    if failed:
        session.error(f"Codecheck ended with errors for: {', '.join(failed)}")


@nox.session
def build(session: nox.Session) -> None:
    """Build Python packages."""
    print(session.posargs)
    install_fnc = get_install_command(session=session)
    install_fnc("build", "twine")
    for project in get_projects():
        with session.chdir(project):
            if Path("dist").exists():
                shutil.rmtree("dist")
            session.run("python", "-m", "build", "--sdist", "--installer", "uv")
            session.run("twine", "check", "--strict", "dist/*")


@nox.session
def upload(session: nox.Session) -> None:
    """Use twine to upload all built packages. To use custom pypi repo use `--repository <repo-name>`."""
    print(session.posargs)
    repository_index = get_args_index(session.posargs, "--repository")
    extra_args = []
    if repository_index is not None:
        extra_args.extend(["--repository", session.posargs[repository_index + 1]])
    install_fnc = get_install_command(session=session)
    install_fnc("twine")
    for project in get_projects():
        with session.chdir(project):
            session.run("twine", "upload", "dist/*", *extra_args)


@nox.session(default=False)
def bump(session: nox.Session) -> None:
    """Bump version on each package. Use `major`, `minor`, or `patch` to indicate version bump."""
    install_fnc = get_install_command(session=session)
    install_fnc("bump-my-version", "GitPython")
    if len(session.posargs) != 1:
        session.error(
            "Invalid input. Need one parameter indicating bump `major`, `minor`, or `patch`"
        )
    bump = session.posargs[0]
    if bump not in ["major", "minor", "patch"]:
        session.error(
            "Invalid input. Need one parameter indicating bump `major`, `minor`, or `patch`"
        )

    import git

    repo = git.Repo()

    changed_files: list[str] = []
    changed_files.extend(repo.untracked_files)
    changed_files.extend([item.a_path for item in repo.index.diff("HEAD")])
    changed_files.extend([item.a_path for item in repo.index.diff(None)])

    for project in get_projects():
        with session.chdir(project):
            # check if there are any changed files here
            changes_detected = any(f.startswith(project) for f in changed_files)
            if not changes_detected:
                logger.info(f"No changes detected in {project}")
                continue
            session.run("bump-my-version", "bump", bump, "--allow-dirty")
