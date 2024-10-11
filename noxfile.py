#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Helper fine to run tasks on all plugins."""

import functools
import shlex
from pathlib import Path
from typing import Optional

import nox
import tomli
from nox.logger import logger

nox.options.default_venv_backend = "uv|venv"
nox.options.reuse_venv = "yes"

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


def collect_dependencies() -> list[str]:
    requirements: list[str] = []
    project_files = [THIS_DIR.joinpath(p, "pyproject.toml") for p in get_projects()]
    for project in project_files:
        logger.info(f"Processing: {project}")
        requirements.extend(get_requirements(project))
    requirements = list(set(requirements))
    requirements = list(filter(lambda x: not x.startswith("spsdk"), requirements))
    return requirements


def get_args_index(args: list[str], search: str) -> Optional[int]:
    if search not in args:
        return None
    return args.index(search)


@nox.session(default=False)
def venv(session: nox.Session) -> None:
    """Setup venv with all plugins and SPSDK. To update current venv use --no-venv."""

    install_fcn = (
        functools.partial(session.run, "uv", "pip", "install")
        if session.venv_backend == "none"
        else session.install
    )

    spsdk_index = get_args_index(session.posargs, "--spsdk")
    if spsdk_index is not None:
        logger.info(f"--spsdk found on index {spsdk_index}")
        spsdk_path = session.posargs[spsdk_index + 1]
        if not Path(spsdk_path).exists():
            session.error(f"SPSDK Path {spsdk_path} doesn't exist")
        with session.chdir(spsdk_path):
            install_fcn(".[all]")

        # remove --spsdk <path> from posargs, as they will be passed down to codecheck
        session.posargs.pop(spsdk_index)
        session.posargs.pop(spsdk_index)
    else:
        # install spsdk from Nexus, use --prerelease to get the latest version
        # latest version that is not yet released publicly
        install_fcn("spsdk[all]", "--prerelease", "allow")

    dependencies = collect_dependencies()
    install_fcn(*dependencies)
    with session.chdir("codecheck"):
        install_fcn(".")
    for project in get_projects():
        with session.chdir(project):
            install_fcn(".", "--no-deps")


@nox.session
def codecheck(session: nox.Session) -> None:
    """Run codecheck on all plugins."""
    venv(session=session)
    failed = []
    for project in get_projects():
        with session.chdir(project):
            try:
                output_idx = get_args_index(session.posargs, "--output")
                if not output_idx:
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
            except:
                failed.append(project)
                session.warn(f"Codecheck for {project} failed!")
    if failed:
        session.error(f"Codecheck ended with errors for: {', '.join(failed)}")
