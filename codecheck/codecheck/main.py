#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2021-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""This Python script runs the development checks on Python project."""

import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union, cast

import click
import colorama
import prettytable
import tomli
from typing_extensions import Self
from yaml import safe_load

from codecheck import __version__ as codecheck_version
from codecheck import gitcov
from codecheck.checker_copyright_year import CopyrightChecker
from codecheck.checker_py_headers import fix_py_headers_in_files
from codecheck.task_scheduler import PrettyProcessRunner, TaskInfo, TaskList, TaskResult

# pylint: disable=unused-argument,too-many-lines

log = logging.getLogger(__name__)
colorama.init()


CPU_CNT = os.cpu_count() or 1
CODECHECK_FOLDER = os.path.dirname(os.path.abspath(__file__))


def load_defaults() -> Dict[str, Dict]:
    """Load codecheck configuration.

    The configuration should be store in project TOML file, or is loaded defaults.

    :return: Codecheck configuration.
    """
    default_config_path = os.path.join(os.path.dirname(__file__), "default_cfg.yaml")
    with open(default_config_path, "r", encoding="utf-8") as f:
        cfg_content = f.read()
    return cast(Dict[str, Dict], safe_load(cfg_content))


def check_list() -> List[str]:
    """Get current configured checks.

    :return: List of checker names
    """
    cfg = load_defaults()
    return list(cfg["checkers"].keys())


CHECK_LIST = check_list()


@dataclass
class CodeCheckConfig:
    """CodeCheck configuration class."""

    git_parent_branch: str = "origin/master"
    output_directory: str = "reports"
    default_check_paths: List[str] = field(default_factory=list)
    jupyter_check_paths: List[str] = field(default_factory=list)
    checkers: TaskList = field(default_factory=TaskList)

    @classmethod
    def _get_checker_name(cls, checker: Union[str, dict]) -> str:
        if isinstance(checker, str):
            name = checker.upper()
        if isinstance(checker, dict):
            name = checker.get("name")  # type: ignore[assignment]
            if name is None:
                # new format
                if len(checker.keys()) != 1:
                    raise ValueError(
                        "When checker is configured via a dictionary, checker's name must be the single key"
                    )
                name = (list(checker.keys())[0]).upper()
        if name not in CHECK_LIST:
            raise ValueError(f"Invalid checker name: '{name}'")
        return name

    # pylint: disable=too-many-locals
    @classmethod
    def load_from_config(cls, cfg: Dict[str, Any]) -> Self:
        """Load the CodeCheck Configuration from stored dictionary.

        :param cfg: Dictionary with configuration
        :return: _description_
        """
        git_parent_branch = cfg.get("git_parent_branch", "origin/master")
        output_directory = cfg.get("output_directory", "reports")
        default_check_paths = cfg.get("default_check_paths", ["."])
        jupyter_check_paths = cfg.get("jupyter_check_paths", [])
        checkers = TaskList()
        defaults = load_defaults()["checkers"]

        # Load checkers as a TaskInfo List
        for checker in cast(List[Union[str, Dict[str, Any]]], cfg.get("checkers", [])):

            checker_name = cls._get_checker_name(checker=checker)
            checker_defaults: dict = defaults[checker_name]
            _, checker_config = checker.popitem() if isinstance(checker, dict) else ("", {})
            assert isinstance(checker_defaults, dict)

            method = globals()[checker_defaults["method"]]
            fixer_name = checker_defaults.get("fixer")
            fixer = globals()[fixer_name] if fixer_name else None
            jupyter_notebook_checker = checker_defaults.get("jupyter_notebook_checker", False)

            check_paths = jupyter_check_paths if jupyter_notebook_checker else default_check_paths
            if isinstance(checker, dict):
                check_paths = checker.get("check_paths", check_paths)
            if isinstance(checker_config, dict):
                check_paths = checker_config.get("check_paths", check_paths)
            if not check_paths:
                continue

            user_args = checker_defaults.get("args", [])
            if isinstance(checker_config, dict):
                user_args = checker_config.get("args", user_args)

            user_kwargs = checker_defaults.get("kwargs", {})
            if isinstance(checker_config, dict):
                user_kwargs = checker_config.get("kwargs", user_kwargs)

            kwargs = {"output": output_directory, "check_paths": check_paths}

            info_only = checker_defaults.get("info_only", False)
            if isinstance(checker_config, dict):
                info_only = checker_config.pop("info_only", info_only)

            timeout = checker_defaults.get("timeout", 100)
            if isinstance(checker_config, dict):
                timeout = checker_config.pop("timeout", timeout)

            checkers.append(
                TaskInfo(
                    name=checker_name,
                    method=method,
                    dependencies=checker_defaults.get("dependencies", []),
                    conflicts=checker_defaults.get("conflicts", []),
                    inherit_failure=checker_defaults.get("inherit_failure", True),
                    info_only=info_only,
                    fixer=fixer,
                    user_args=user_args,
                    user_kwargs=user_kwargs,
                    timeout=timeout,
                    **kwargs,
                )
            )
        return cls(
            git_parent_branch=git_parent_branch,
            output_directory=output_directory,
            default_check_paths=default_check_paths,
            jupyter_check_paths=jupyter_check_paths,
            checkers=checkers,
        )

    @classmethod
    def load_from_toml(cls) -> Self:
        """Load the CodeCheck Configuration from project TOML.

        :return: _description_
        """
        pyproject_toml_path = os.path.join(os.getcwd(), "pyproject.toml")
        if os.path.exists(pyproject_toml_path):
            with open(pyproject_toml_path, "rb") as f:
                toml = tomli.load(f)
                if toml.get("tool") and toml["tool"].get("nxp_codecheck"):
                    return cls.load_from_config(toml["tool"]["nxp_codecheck"])
        return cls()


def print_results(tasks: List[TaskInfo]) -> None:
    """Print Code Check results in table."""
    table = prettytable.PrettyTable(["#", "Test", "Result", "Exec Time", "Error count", "Log"])
    table.align = "l"
    table.header = True
    table.border = True
    table.hrules = prettytable.HEADER
    table.vrules = prettytable.NONE

    for i, task in enumerate(tasks, start=1):
        assert task.result

        table.add_row(
            [
                colorama.Fore.YELLOW + str(i),
                colorama.Fore.WHITE + task.name,
                task.status_str(),
                colorama.Fore.WHITE + task.get_exec_time(),
                colorama.Fore.CYAN + str(task.result.error_count),
                colorama.Fore.BLUE + task.result.output_log,
            ]
        )
    click.echo(table)
    click.echo(colorama.Style.RESET_ALL)


def check_results(tasks: List[TaskInfo], output: str = "reports") -> int:
    """Print Code Check results in table."""
    ret = 0

    for task in tasks:
        err_cnt = task.result.error_count if task.result else -1
        output_log: List[str] = []
        if task.exception:
            sanity_name = task.name.replace(" ", "_").replace("'", "_")
            exc_log = os.path.join(output, f"{sanity_name}_exc.txt")
            with open(exc_log, "w", encoding="utf-8") as f:
                f.write(str(task.exception))
            output_log.append(exc_log)

        # The info only tasks are not counted to overall results
        if not task.info_only and (task.result is None or err_cnt != 0):
            ret = 1

        if task.result:
            res_log = task.result.output_log
            output_log.append(res_log)
            task.result.output_log = " , ".join(output_log)
        else:
            task.result = TaskResult(error_count=1, output_log=" , ".join(output_log))

    return ret


def _serialize_args_kwargs(
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    kw_separator: str = "=",
    kw_prefix: str = "--",
) -> str:
    """Serialize arguments and keyword arguments."""
    args_s = " ".join(user_args) if user_args else ""
    kwargs_s = (
        " ".join([f"{kw_prefix}{key}{kw_separator}{value}" for key, value in user_kwargs.items()])
        if user_kwargs
        else ""
    )
    return f"{args_s} {kwargs_s}"


# pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-positional-arguments
def check_pytest(
    output: str,
    check_paths: List[str],
    disable_xdist: bool = False,
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Get the code coverage."""
    output_folder = os.path.join(output, "htmlcov")
    output_xml = os.path.join(output, "coverage.xml")
    output_log = os.path.join(output, "coverage.txt")
    junit_report = os.path.join(output, "tests.xml")
    coverage_file = os.path.join(output, ".coverage")

    if os.path.isdir(output_folder):
        shutil.rmtree(output_folder, ignore_errors=True)

    if kwargs:
        disable_xdist |= bool(kwargs.get("disable_xdist", False))
    if user_kwargs:
        disable_xdist |= bool(user_kwargs.pop("disable_xdist", False))

    parallel = "" if disable_xdist else f"-n {CPU_CNT//2 or 1}"
    cov_path = check_paths[0]

    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")

    cmd = (
        f'pytest {parallel} {user_args_s} --cov "{cov_path}" --cov-branch --junit-xml "{junit_report}"'
        f' --cov-report term --cov-report html:"{output_folder}" --cov-report xml:"{output_xml}"'
    )
    with open(output_log, "w", encoding="utf-8") as f:
        if len(check_paths) > 1:
            f.write(f"Only first path ({cov_path}) has been used to code coverage")
            f.flush()
        res = subprocess.call(
            shlex.split(cmd),
            stdout=f,
            stderr=f,
            env=dict(os.environ, COVERAGE_FILE=coverage_file),
            timeout=timeout,
        )

    return TaskResult(error_count=res, output_log=output_log)


def check_gitcov(
    output: str,
    timeout: int = 100,
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Get the code coverage."""
    output_log = os.path.join(output, "gitcov.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    with open(output_log, "w", encoding="utf-8") as f:
        res = subprocess.call(
            shlex.split(
                f"'{sys.executable}' '{CODECHECK_FOLDER}/gitcov.py' {user_args_s} "
                f"--coverage-report '{os.path.join(output, 'coverage.xml')}'"
            ),
            stdout=f,
            stderr=f,
            timeout=timeout,
        )

    return TaskResult(error_count=res, output_log=output_log)


def check_dependencies(
    output: str,
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Check the dependencies and their licenses."""
    output_log = os.path.join(output, "dependencies.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    with open(output_log, "w", encoding="utf-8") as f:
        res = subprocess.call(
            shlex.split(
                f"'{sys.executable}' '{CODECHECK_FOLDER}/checker_dependencies.py' {user_args_s}"
            ),
            stdout=f,
            stderr=f,
            timeout=timeout,
        )

    return TaskResult(error_count=res, output_log=output_log)


def fix_dependencies(timeout: int = 100, **kwargs: Dict[str, Any]) -> None:
    """Check the dependencies and their licenses."""
    subprocess.call(
        shlex.split(f"'{sys.executable}' '{CODECHECK_FOLDER}/checker_dependencies.py' fix"),
        stdout=None,
        stderr=None,
        timeout=timeout,
    )


def check_pydocstyle(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Check the dependencies and their licenses."""
    output_log = os.path.join(output, "pydocstyle.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=check_paths)
    res = 0
    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            res += subprocess.call(
                shlex.split(f"pydocstyle {user_args_s} {path_slice}"),
                stdout=f,
                stderr=f,
                timeout=timeout,
            )

    with open(output_log, "r", encoding="utf-8") as f:
        err_cnt = re.findall(r":\d+ in", f.read())
        if err_cnt:
            res = len(err_cnt)

    return TaskResult(error_count=res, output_log=output_log)


def check_mypy(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Check the project against mypy tool."""
    output_log = os.path.join(output, "mypy.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=check_paths)
    res = 0
    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            res += subprocess.call(
                shlex.split(f"mypy {user_args_s} {path_slice}"), stdout=f, stderr=f, timeout=timeout
            )

    with open(output_log, "r", encoding="utf-8") as f:
        err_cnt: list[str] = re.findall(r"Found \d+ error", f.read())
        if err_cnt:
            res = int(err_cnt[0].replace("Found ", "").replace(" error", ""))

    return TaskResult(error_count=res, output_log=output_log)


def check_pylint_all(
    output: str,
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Call pylint with given configuration and output log."""
    output_log = os.path.join(output, "pylint_docs.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    with open(output_log, "w", encoding="utf-8") as f:
        subprocess.call(
            shlex.split(f"pylint {user_args_s} -j {CPU_CNT//2 or 1}"),
            stdout=f,
            stderr=f,
            timeout=timeout,
        )

    with open(output_log, "r", encoding="utf-8") as f:
        err_cnt = re.findall(r": [IRCWEF]\d{4}:", f.read())

    return TaskResult(error_count=len(err_cnt), output_log=output_log)


def check_pylint(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Check Pylint log for errors."""
    output_log = os.path.join(output, "pylint.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=check_paths)

    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            subprocess.call(
                shlex.split(f"pylint {user_args_s} {path_slice} -j {CPU_CNT//2 or 1}"),
                stdout=f,
                stderr=f,
                timeout=timeout,
            )

    with open(output_log, "r", encoding="utf-8") as f:
        err_cnt = re.findall(r": [IRCWEF]\d{4}:", f.read())

    return TaskResult(error_count=len(err_cnt), output_log=output_log)


def check_radon(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Check the project against radon rules."""
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    file_suffix = user_args_s.replace(" ", "-").replace("---", "-")
    output_log = os.path.join(output, f"radon-{file_suffix}.txt")
    path_slices = splice_changed_files(changed_files=check_paths)
    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            subprocess.call(
                shlex.split(f"radon {user_args_s} {path_slice}"),
                stdout=f,
                stderr=f,
                timeout=timeout,
            )

    with open(output_log, "r", encoding="utf-8") as f:
        err_cnt = re.findall(r"[ABCDEF] \(\d{1,3}\)", f.read())

    return TaskResult(error_count=len(err_cnt), output_log=output_log)


def check_black(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Check the project against black formatter rules."""
    output_log = os.path.join(output, "black.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=check_paths)
    res = 0
    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            res += subprocess.call(
                shlex.split(f"black {user_args_s} {path_slice}"),
                stdout=f,
                stderr=f,
                timeout=timeout,
            )

    return TaskResult(error_count=res, output_log=output_log)


def fix_black(check_paths: List[str], timeout: int = 100, **kwargs: Dict[str, Any]) -> None:
    """Check the project against black formatter rules."""
    path_slices = splice_changed_files(changed_files=check_paths)
    for path_slice in path_slices:
        subprocess.call(
            shlex.split(f"black {path_slice}"), stdout=None, stderr=None, timeout=timeout
        )


def check_black_nb(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Check the project against black formatter rules."""
    output_log = os.path.join(output, "black_nb.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=check_paths)
    res = 0
    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            res += subprocess.call(
                shlex.split(f"nbqa black --nbqa-diff {path_slice} {user_args_s}"),
                stdout=f,
                stderr=f,
                timeout=timeout,
            )

    return TaskResult(error_count=res, output_log=output_log)


def fix_black_nb(check_paths: List[str], timeout: int = 100, **kwargs: Dict[str, Any]) -> None:
    """Check the project against black formatter rules."""
    path_slices = splice_changed_files(changed_files=check_paths)
    for path_slice in path_slices:
        subprocess.call(
            shlex.split(f"nbqa black {path_slice}"), stdout=None, stderr=None, timeout=timeout
        )


def check_isort(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Check the project against isort imports formatter rules."""
    output_log = os.path.join(output, "isort.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=check_paths)
    res = 0
    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            res += subprocess.call(
                shlex.split(f"isort {user_args_s} -c {path_slice}"),
                stdout=f,
                stderr=f,
                timeout=timeout,
            )
    if res:
        with open(output_log, "r", encoding="utf-8") as f:
            res = len(f.read().splitlines())

    return TaskResult(error_count=res, output_log=output_log)


def fix_isort(check_paths: List[str], timeout: int = 100, **kwargs: Dict[str, Any]) -> None:
    """Check the project against isort imports formatter rules."""
    path_slices = splice_changed_files(changed_files=check_paths)
    for path_slice in path_slices:
        subprocess.call(
            shlex.split(f"isort {path_slice}"), stdout=None, stderr=None, timeout=timeout
        )


def check_isort_nb(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Check the project against isort imports formatter rules."""
    output_log = os.path.join(output, "isort_nb.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=check_paths)
    res = 0
    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            res += subprocess.call(
                shlex.split(f"nbqa isort --nbqa-diff {user_args_s} {path_slice}"),
                stdout=f,
                stderr=f,
                timeout=timeout,
            )

    if res:
        with open(output_log, "r", encoding="utf-8") as f:
            res = len(f.read().splitlines())

    return TaskResult(error_count=res, output_log=output_log)


def fix_isort_nb(
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> None:
    """Check the project against isort imports formatter rules."""
    path_slices = splice_changed_files(changed_files=check_paths)
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    for path_slice in path_slices:
        subprocess.call(
            shlex.split(f"nbqa isort {path_slice} {user_args_s}"),
            stdout=None,
            stderr=None,
            timeout=timeout,
        )


def check_copyright_year(
    output: str,
    changed_files: Sequence[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Check the project against copy right year rules."""
    output_log = os.path.join(output, "copyright_year.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=changed_files)
    res = 0
    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            res += subprocess.call(
                shlex.split(
                    f'"{sys.executable}" "{CODECHECK_FOLDER}/checker_copyright_year.py" {user_args_s} {path_slice}'
                ),
                stdout=f,
                stderr=f,
                timeout=timeout,
            )
    if res:
        with open(output_log, "r", encoding="utf-8") as f:
            res = len(f.read().splitlines())

    return TaskResult(error_count=res, output_log=output_log)


def fix_copyright_year(changed_files: Sequence[str], **kwargs: Dict[str, Any]) -> None:
    """Check the project against copy right year rules."""
    path_slices = splice_changed_files(changed_files)
    checker = CopyrightChecker()
    for path_slice in path_slices:
        checker.fix_files(path_slice.split())


def check_py_file_headers(
    output: str,
    changed_files: Sequence[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Check that python files have valid header."""
    output_log = os.path.join(output, "py_header.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=changed_files)
    res = 0

    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            res += subprocess.call(
                shlex.split(
                    f'"{sys.executable}" "{CODECHECK_FOLDER}/checker_py_headers.py" {user_args_s} {path_slice}'
                ),
                stdout=f,
                stderr=f,
                timeout=timeout,
            )

    if res:
        with open(output_log, "r", encoding="utf-8") as f:
            res = len(f.read().splitlines())

    return TaskResult(error_count=res, output_log=output_log)


def fix_py_file_headers(changed_files: Sequence[str], **kwargs: Dict[str, Any]) -> None:
    """Check the project against copy right year rules."""
    path_slices = splice_changed_files(changed_files)
    for path_slice in path_slices:
        fix_py_headers_in_files(path_slice.split())


def check_jupyter_outputs(
    output: str,
    changed_files: Sequence[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Checker of Jupiter notebooks outputs.

    :param output: Output report folder
    :param changed_files: List of files to check
    :param kwargs: Keyword arguments for specific type of key
    :return: Checker result
    """
    output_log = os.path.join(output, "jupyter_outputs.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=changed_files)
    res = 0

    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            res += subprocess.call(
                shlex.split(
                    f'"{sys.executable}" "{CODECHECK_FOLDER}/checker_jupyter.py" {user_args_s} {path_slice}'
                ),
                stdout=f,
                stderr=f,
                timeout=timeout,
            )
    return TaskResult(error_count=res, output_log=output_log)


def check_cyclic_imports(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Cyclic import check.

    :param output: Reports output folder
    :param check_paths: List of paths to check
    :param kwargs: Keyword arguments for specific type of key
    :return: Task results
    """
    output_log = os.path.join(output, "cyclic_imports.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=check_paths)
    res = 0
    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            res += subprocess.call(
                shlex.split(
                    f'"{sys.executable}" "{CODECHECK_FOLDER}/checker_cyclic_import.py" {user_args_s} {path_slice}'
                ),
                stdout=f,
                stderr=f,
                timeout=timeout,
            )
    return TaskResult(error_count=res, output_log=output_log)


def check_cspell(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Check the project spelling with cspell."""
    output_log = os.path.join(output, "cspell.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=check_paths)

    cspell_path = shutil.which("cspell")
    if not cspell_path:
        return TaskResult(error_count=1, output_log="CSPELL NOT FOUND", not_run=True)

    with open(output_log, "w", encoding="utf-8") as f:
        try:
            res = subprocess.run(
                f'"{cspell_path}" --help',
                check=False,
                capture_output=True,
                shell=True,
                timeout=5,
            )  # nosec calling this without shell=True causes [WinError 193] %1 is not a valid Win32 application
        except subprocess.TimeoutExpired:
            return TaskResult(error_count=1, output_log="TIMED OUT", not_run=True)
        if res.returncode != 0:
            f.write(res.stdout.decode("utf-8"))
            f.write(res.stderr.decode("utf-8"))
            return TaskResult(error_count=res.returncode, output_log=output_log, not_run=True)

        for path_slice in path_slices:
            try:
                res = subprocess.run(
                    f'"{cspell_path}" {user_args_s} {path_slice}',
                    check=False,
                    capture_output=True,
                    shell=True,
                    timeout=timeout,
                )  # nosec calling this without shell=True causes [WinError 193] %1 is not a valid Win32 application
            except subprocess.TimeoutExpired:
                return TaskResult(error_count=1, output_log="TIMED OUT", not_run=True)
            f.write(res.stdout.decode("utf-8"))
            f.write(res.stderr.decode("utf-8"))

        match = 0
        matched = None

        if res.stderr:
            stderr = res.stderr.decode("utf-8")
            matched = re.search(r"Issues found: (\d+)", stderr)

        if matched:
            match = int(matched.group(1))

    return TaskResult(error_count=match or res.returncode, output_log=output_log)


def check_lychee(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: Dict[str, Any],
) -> TaskResult:
    """Check the project links with lychee."""
    output_log = os.path.join(output, "lychee.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=check_paths)

    lychee_path = shutil.which("lychee")
    if not lychee_path:
        return TaskResult(error_count=1, output_log="LYCHEE NOT FOUND", not_run=True)

    with open(output_log, "w", encoding="utf-8") as f:
        res = subprocess.run(
            shlex.split(f'"{lychee_path}" --help'),
            check=False,
            capture_output=True,
            timeout=5,
        )
        if res.returncode != 0:
            f.write(res.stderr.decode("utf-8"))
            return TaskResult(error_count=res.returncode, output_log=output_log, not_run=True)

        for path_slice in path_slices:
            res = subprocess.run(
                shlex.split(f'"{lychee_path}" {user_args_s} {path_slice}'),
                check=False,
                capture_output=True,
                timeout=timeout,
            )

            f.write(res.stdout.decode("utf-8"))

        match = 0
        matched = None

        if res.stdout:
            stderr = res.stdout.decode("utf-8")
            matched = re.search(r"(\d+)\sErrors", stderr)

        if matched:
            match = int(matched.group(1))

    return TaskResult(error_count=match or res.returncode, output_log=output_log)


def check_bandit(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: str,
) -> TaskResult:
    """Check for project's security vulnerabilities using Bandit."""
    output_log = os.path.join(output, "bandit.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=check_paths)
    res = 0
    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            res += subprocess.call(
                shlex.split(f"bandit -c pyproject.toml -r {path_slice} {user_args_s}"),
                stderr=f,
                stdout=f,
                timeout=timeout,
            )
    # bandit return's 1 if there are any errors, we get the exact amount from the log file
    if res > 0:
        with open(output_log, encoding="utf-8") as f:
            log_data = f.read()
        res = len(re.findall(">> Issue:", log_data))

    return TaskResult(error_count=res, output_log=output_log)


def check_ruff(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: str,
) -> TaskResult:
    """Check for project's security vulnerabilities using Bandit."""
    output_log = os.path.join(output, "ruff.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=check_paths)
    res = 0
    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            res += subprocess.call(
                shlex.split(f"ruff check {path_slice} {user_args_s}"),
                stderr=f,
                stdout=f,
                timeout=timeout,
            )
    # bandit return's 1 if there are any errors, we get the exact amount from the log file
    if res > 0:
        with open(output_log, encoding="utf-8") as f:
            log_data = f.read()
        res = int(re.findall(r"Found (\d+) error", log_data)[0])

    return TaskResult(error_count=res, output_log=output_log)


def fix_ruff(
    output: str,
    check_paths: List[str],
    user_args: Optional[list[str]] = None,
    user_kwargs: Optional[dict[str, str]] = None,
    timeout: int = 100,
    **kwargs: str,
) -> TaskResult:
    """Check for project's security vulnerabilities using Bandit."""
    output_log = os.path.join(output, "ruff.txt")
    user_args_s = _serialize_args_kwargs(user_args, user_kwargs, kw_separator=" ")
    path_slices = splice_changed_files(changed_files=check_paths)
    res = 0
    with open(output_log, "w", encoding="utf-8") as f:
        for path_slice in path_slices:
            res += subprocess.call(
                shlex.split(f"ruff check --fix {path_slice} {user_args_s}"),
                stderr=f,
                stdout=f,
                timeout=timeout,
            )
    # bandit return's 1 if there are any errors, we get the exact amount from the log file
    if res > 0:
        with open(output_log, encoding="utf-8") as f:
            log_data = f.read()
        res = int(re.findall(r"Found (\d+) errors", log_data)[0])

    return TaskResult(error_count=res, output_log=output_log)


def fix_found_problems(
    checks: TaskList,
    all_checks: TaskList,
    silence: int = 0,
    run_check_again: bool = True,
) -> None:
    """Fix the failed checks automatically is possible."""
    re_checks = TaskList()
    for check in checks:
        if not check.fixer:
            continue
        if check.result and check.result.error_count != 0:
            check.fixer(**check.kwargs)
            click.echo(f"{colorama.Fore.GREEN}{check.name} problems fixed.{colorama.Fore.RESET}")
            check.reset()
            re_checks.append(check)
    if run_check_again and len(re_checks) > 0:
        click.echo("Running the failed codechecks again.")
        # sometimes, fixers any change code and final copyright check is required
        # make sure COPYRIGHT checker is always included and executed as the last one
        copyright_checker = all_checks.get_task_by_name("COPYRIGHT")
        if copyright_checker in re_checks:
            re_checks.remove(copyright_checker)
        copyright_checker.reset()
        re_checks.append(copyright_checker)

        runner = PrettyProcessRunner(
            re_checks, print_func=(lambda x: None) if silence else click.echo
        )
        # run things sequently to ensure COPYRIGHT runs at the last one
        runner.run(concurrent_runs=1, clear_console=True)
        if silence < 2:
            print_results(re_checks)


def splice_changed_files(changed_files: Sequence[str], max_size: int = 2000) -> List[str]:
    """Splice list of changed files into chunks of max_size.

    :param changed_files: List of changed files
    :param max_size: Max size of each chunk of changed files
    :raises RuntimeError: Splicing malfunctioned
    :return: Spliced of changed files
    """
    big_string = " ".join(changed_files)
    total_len = len(big_string)
    splice_length = max_size
    max_iterations = 2 * (total_len // splice_length) + 1

    start_offset = 0
    end_offset = splice_length
    pieces = []
    for _ in range(max_iterations):
        if end_offset >= total_len:
            pieces.append(big_string[start_offset:])
            break
        terminal = big_string.rfind(" ", start_offset, end_offset)
        pieces.append(big_string[start_offset:terminal])
        start_offset = terminal + 1
        end_offset = start_offset + splice_length
    else:
        raise RuntimeError("Changed files splicing takes way too much time")
    return pieces


@click.command(name="codecheck", no_args_is_help=False)
@click.option(
    "-c",
    "--check",
    type=click.Choice(
        CHECK_LIST,
        case_sensitive=False,
    ),
    multiple=True,
    help="Run only selected test instead of all. Can be specified multiple times.",
)
@click.option(
    "-ic",
    "--info-check",
    type=click.Choice(
        CHECK_LIST,
        case_sensitive=False,
    ),
    multiple=True,
    help=(
        "Mark selected test as INFO ONLY. Test's result won't be "
        "added to final exit code. Can be specified multiple times."
    ),
)
@click.option(
    "-dc",
    "--disable-check",
    type=click.Choice(CHECK_LIST, case_sensitive=False),
    multiple=True,
    help="Disable selected test. Can be specified multiple times.",
)
@click.option(
    "-j",
    "--job-cnt",
    type=click.IntRange(1, 32),
    default=CPU_CNT,
    help="Choose concurrent count of running check jobs.",
)
@click.option(
    "-s",
    "--silence",
    count=True,
    help="The level of silence, -s: Only summary table is printed, -ss: Nothing is printed.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    required=False,
    help="Override the default output folder to store reports files.",
)
@click.option(
    "-f",
    "--fix",
    is_flag=True,
    default=False,
    help="Fix the problems automatically if possible.",
)
@click.option(
    "-dx",
    "--disable-xdist",
    is_flag=True,
    default=False,
    help=(
        "Disable parallel pytest execution (using pytest-xdist). "
        "This is useful on Linux machines with lower CPU count."
    ),
)
@click.option(
    "-dm",
    "--disable-merges",
    is_flag=True,
    default=False,
    help="Disable scan for files which were introduced via merge into development branch.",
)
@click.option(
    "-pb",
    "--parent-branch",
    default="origin/master",
    help="Name of the upstream branch for PR integration/merge.",
)
@click.option(
    "-q",
    "--quick",
    is_flag=True,
    default=False,
    help="Quick test mode, do not run INFO_ONLY checks.",
)
@click.version_option(codecheck_version)
def main(  # pylint: disable=too-many-arguments,too-many-locals,too-many-positional-arguments
    check: List[str],
    info_check: List[str],
    disable_check: List[str],
    job_cnt: int,
    silence: int,
    output: click.Path,
    fix: bool,
    disable_xdist: bool,
    disable_merges: bool,
    parent_branch: str,
    quick: bool,
) -> None:
    """Simple tool to check the Python generic development rules.

    Overall result is passed to OS.
    """
    # logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    logging.basicConfig(level=logging.INFO)
    config = CodeCheckConfig.load_from_toml()
    changed_files = gitcov.get_changed_files(
        repo_path=".",
        include_merges=not disable_merges,
        parent_branch=parent_branch or config.git_parent_branch,
    )
    for checker in config.checkers:
        checker.kwargs["changed_files"] = changed_files
        # Override output if CLI wants :-)
        if output:
            checker.kwargs["output"] = output
        # Add disable_xdist if defined on CLI
        if disable_xdist:
            checker.kwargs["disable_xdist"] = disable_xdist

        # Update info only part
        if checker.name in list(info_check):
            checker.info_only = True

    output_dir = str(output) if output else config.output_directory
    disable_check = [x.upper() for x in list(disable_check)]

    if quick:
        # Disable info checks
        disable_check += [x.name for x in config.checkers if x.info_only]

    ret = 1
    try:
        checks = get_configured_task_list(
            available_tasks=config.checkers,
            enabled_checks=check,
            disabled_checks=disable_check,
        )

        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)

        runner = PrettyProcessRunner(checks, print_func=(lambda x: None) if silence else click.echo)
        runner.run(job_cnt, True)

        ret = check_results(checks, output_dir)
        if silence < 2:
            print_results(checks)
            click.echo(f"Overall time: {round(runner.process_time, 1)} second(s).")
            res_color = (
                (colorama.Fore.GREEN + "PASS") if ret == 0 else (colorama.Fore.RED + "FAILED")
            )
            click.echo(f"Overall result: {res_color}. {colorama.Fore.RESET}")

        if fix:
            fix_found_problems(checks, all_checks=config.checkers, silence=silence)
            ret = 0

    except Exception as exc:  # pylint: disable=broad-except
        click.echo(exc)
        ret = 1

    sys.exit(ret)


def get_configured_task_list(
    available_tasks: TaskList,
    enabled_checks: Optional[List[str]] = None,
    disabled_checks: Optional[List[str]] = None,
) -> TaskList:
    """Create final list of tasks that shall be executed."""
    checks = TaskList()
    # pylint: disable=not-an-iterable,unsupported-membership-test   # TaskList is a list
    for task in available_tasks:
        if disabled_checks and task.name in disabled_checks:
            continue
        if (
            disabled_checks
            and task.dependencies
            and any(dependency in disabled_checks for dependency in task.dependencies)
        ):
            continue

        if enabled_checks and task.name not in enabled_checks:
            continue
        if (
            enabled_checks
            and task.dependencies
            and len(set(task.dependencies) - set(enabled_checks)) != 0
        ):
            # insert missing dependencies
            for dependency_name in task.dependencies:
                extra_task = available_tasks.get_task_by_name(dependency_name)
                if extra_task not in checks:
                    checks.append(extra_task)
        checks.append(task)
    return checks


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover  # pylint: disable=no-value-for-parameter
