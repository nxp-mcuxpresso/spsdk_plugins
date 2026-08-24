#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Helper fine to run tasks on all plugins."""

import functools
import re
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
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


@dataclass(frozen=True)
class CodecheckResult:
    """Collected codecheck result for one plugin project."""

    project: str
    report_dir: str
    failed: bool
    failed_checks: tuple[str, ...] = ()


class CodecheckHtmlReportParser(HTMLParser):
    """Extract failed checker names from codecheck HTML report."""

    def __init__(self) -> None:
        super().__init__()
        self.failed_checks: list[str] = []
        self._in_table_row = False
        self._in_cell = False
        self._current_row_class = ""
        self._current_row_cells: list[str] = []
        self._current_cell_data: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._in_table_row = True
            self._current_row_class = dict(attrs).get("class") or ""
            self._current_row_cells = []
        elif tag == "td" and self._in_table_row:
            self._in_cell = True
            self._current_cell_data = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell_data.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._in_cell:
            self._in_cell = False
            self._current_row_cells.append("".join(self._current_cell_data).strip())
        elif tag == "tr" and self._in_table_row:
            if self._current_row_class == "status-failure" and len(self._current_row_cells) >= 3:
                checker_name = self._current_row_cells[1]
                result = self._current_row_cells[2]
                if "FAILED" in result:
                    self.failed_checks.append(checker_name)
            self._in_table_row = False
            self._current_row_class = ""
            self._current_row_cells = []


def get_failed_checks(project: str, report_dir: str) -> tuple[str, ...]:
    """Read failed checker names from codecheck HTML report if available."""
    report_path = THIS_DIR / project / report_dir / "codecheck_report.html"
    if not report_path.exists():
        return ()
    parser = CodecheckHtmlReportParser()
    parser.feed(report_path.read_text(encoding="utf-8"))
    return tuple(parser.failed_checks)


def get_projects() -> list[str]:
    data = tomli.loads(THIS_DIR.joinpath("pyproject.toml").read_text(encoding="utf-8"))
    projects = data["tool"]["release-tools"]["sub_projects"]
    logger.info(f"Projects found: {', '.join(projects) }")
    return projects


def _read_requirements_file(requirements_file: Path) -> list[str]:
    """Read one requirement per line while preserving environment markers."""
    requirements = []
    multiline_requirement = ""
    for raw_line in requirements_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if " #" in line:
            line = line.split(" #", maxsplit=1)[0].rstrip()
        if not line:
            continue
        if line.endswith("\\"):
            multiline_requirement += f"{line[:-1].rstrip()} "
            continue
        requirement = f"{multiline_requirement}{line}".strip()
        multiline_requirement = ""
        requirements.append(requirement)
    if multiline_requirement:
        requirements.append(multiline_requirement.strip())
    return requirements


def get_requirements(pyproject: Path) -> list[str]:
    data = tomli.loads(pyproject.read_text(encoding="utf-8"))
    if not data.get("project"):
        return []
    dynamic = data["project"].get("dynamic")
    if dynamic and "dependencies" in dynamic:
        req_file_name = data["tool"]["setuptools"]["dynamic"]["dependencies"]["file"]
        req_file = pyproject.parent.joinpath(req_file_name[0])
        return _read_requirements_file(req_file)

    return data["project"].get("dependencies")


def get_dev_requirements(pyproject: Path) -> list[str]:
    requirements_dev = pyproject.parent.joinpath("requirements_dev.txt")
    if requirements_dev.exists():
        return _read_requirements_file(requirements_dev)
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
    filtered = []
    for requirement in requirements:
        requirement_name = _get_requirement_name(requirement)
        if requirement_name.startswith("spsdk") or requirement_name == "nxp-codecheck":
            continue
        filtered.append(requirement)
    return filtered


def get_args_index(args: list[str], search: str) -> Optional[int]:
    if search not in args:
        return None
    return args.index(search)


def _normalize_package_name(package_name: str) -> str:
    """Normalize package name for safe requirement-name comparisons."""
    return package_name.lower().replace("_", "-")


def _get_requirement_name(requirement: str) -> str:
    """Extract normalized package name from a requirement string."""
    requirement_no_marker = requirement.split(";", maxsplit=1)[0].strip()
    name = re.split(r"[<>=!~\[\]\s]", requirement_no_marker, maxsplit=1)[0]
    return _normalize_package_name(name)


def get_spsdk_core_requirements(spsdk_path: Path) -> list[str]:
    """Read SPSDK requirements while excluding all spsdk* packages."""
    requirements_file = spsdk_path / "requirements.txt"
    if not requirements_file.exists():
        return []
    requirements = _read_requirements_file(requirements_file)
    return [
        requirement
        for requirement in requirements
        if not _get_requirement_name(requirement).startswith("spsdk")
    ]


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


def get_codecheck_report_dir(session: nox.Session) -> str:
    """Resolve the codecheck report directory once for the whole nox session."""
    output_idx = get_args_index(session.posargs, "--output")
    if output_idx is None:
        output_idx = get_args_index(session.posargs, "-o")
    if output_idx is None:
        report_dir = "reports"
    else:
        report_dir = session.posargs[output_idx + 1]
        remove_posargs(session, "--output", "-o")
    if session.python:
        return f"{report_dir}-{session.python}"
    return report_dir


def create_codecheck_summary(
    session: nox.Session,
    report_dir: str,
    results: list[CodecheckResult],
) -> Path:
    """Create a Jenkins-friendly JUnit summary for plugin and checker failures."""
    summary_dir = THIS_DIR / "reports-summary"
    summary_dir.mkdir(exist_ok=True)
    python_label = session.python or "default"
    summary_path = summary_dir / f"junit-codecheck-{python_label}.xml"
    tests = 0
    failures = 0
    testsuite = ET.Element(
        "testsuite",
        attrib={
            "name": f"codecheck-{python_label}",
            "errors": "0",
        },
    )
    for result in results:
        if result.failed_checks:
            for checker in result.failed_checks:
                tests += 1
                failures += 1
                testcase = ET.SubElement(
                    testsuite,
                    "testcase",
                    attrib={
                        "classname": f"codecheck-{python_label}.{result.project}",
                        "name": checker,
                    },
                )
                ET.SubElement(testcase, "system-out").text = (
                    f"Project: {result.project}\n"
                    f"Checker: {checker}\n"
                    f"Report directory: {result.report_dir}\n"
                    f"Configured output name: {report_dir}\n"
                    "See archived codecheck HTML/text reports for details."
                )
                ET.SubElement(
                    testcase,
                    "failure",
                    attrib={"message": f"{result.project} failed {checker}"},
                ).text = (
                    f"Plugin {result.project} failed checker {checker}.\n"
                    f"Inspect archived reports under {result.report_dir}."
                )
            continue

        tests += 1
        testcase = ET.SubElement(
            testsuite,
            "testcase",
            attrib={
                "classname": f"codecheck-{python_label}.{result.project}",
                "name": "all checks passed" if not result.failed else "codecheck failed",
            },
        )
        ET.SubElement(testcase, "system-out").text = (
            f"Project: {result.project}\n"
            f"Report directory: {result.report_dir}\n"
            f"Configured output name: {report_dir}\n"
            "See archived codecheck reports for details."
        )
        if result.failed:
            failures += 1
            ET.SubElement(
                testcase,
                "failure",
                attrib={"message": f"Codecheck failed for {result.project}"},
            ).text = (
                f"Plugin {result.project} failed repository codecheck.\n"
                "Checker-level details were not available in the generated HTML report.\n"
                f"Inspect archived reports under {result.report_dir}."
            )
    testsuite.set("tests", str(tests))
    testsuite.set("failures", str(failures))
    testsuite.set("skipped", "0")
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(summary_path, encoding="utf-8", xml_declaration=True)
    return summary_path


@nox.session(default=False)
def venv(session: nox.Session) -> None:
    """Setup venv with all plugins and SPSDK core. Requires `--spsdk <repo-path>`."""
    install_fcn = get_install_command(session=session)

    spsdk_index = get_args_index(session.posargs, "--spsdk")
    if spsdk_index is None:
        session.error("Missing required --spsdk <repo-path> argument for deterministic install")
    logger.info(f"--spsdk found on index {spsdk_index}")
    spsdk_path = session.posargs[spsdk_index + 1]
    if not Path(spsdk_path).exists():
        session.error(f"SPSDK Path {spsdk_path} doesn't exist")
    with session.chdir(spsdk_path):
        install_fcn(".", "--no-deps")
        core_requirements = get_spsdk_core_requirements(Path("."))
        if core_requirements:
            install_fcn(*core_requirements)
    remove_posargs(session, "--spsdk")
    for project in get_projects():
        with session.chdir(project):
            install_fcn(".", "--no-deps")
    dependencies = collect_dependencies(include_dev_deps=True)
    install_fcn("nxp-codecheck")
    install_fcn(*dependencies)


@nox.session
def codecheck(session: nox.Session) -> None:
    """Run codecheck on all plugins. Session accepts same options as `codecheck`."""
    venv(session=session)
    remove_posargs(session, "--repository")
    report_dir = get_codecheck_report_dir(session)

    failed = []
    results = []
    for project in get_projects():
        with session.chdir(project):
            try:
                session.run("codecheck", *session.posargs, "-o", report_dir)
                results.append(
                    CodecheckResult(
                        project=project,
                        report_dir=str(Path(project, report_dir).as_posix()),
                        failed=False,
                    )
                )
            except nox.command.CommandFailed:
                failed.append(project)
                session.warn(f"Codecheck for {project} failed!")
                results.append(
                    CodecheckResult(
                        project=project,
                        report_dir=str(Path(project, report_dir).as_posix()),
                        failed=True,
                        failed_checks=get_failed_checks(project=project, report_dir=report_dir),
                    )
                )
    summary_path = create_codecheck_summary(session=session, report_dir=report_dir, results=results)
    logger.info(f"Codecheck JUnit summary written to: {summary_path}")
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
