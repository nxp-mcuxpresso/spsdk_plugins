#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2020-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""GitCov script is to calculate code coverage for changed files."""

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
from os import path
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional, Sequence, Tuple, cast

import git
import tomli
from defusedxml.ElementTree import parse as xml_parse

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element, ElementTree  # nosec
else:
    Element = ElementTree = object

logger = logging.getLogger()
# Modify logger to proper format
LOG_HANDLER = logging.StreamHandler()
LOG_HANDLER.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(LOG_HANDLER)

GIT_PATH = shutil.which("git")
if not GIT_PATH:
    raise FileNotFoundError("git not found in PATH")


DEFAULT_CONFIG = {
    "skip-files": "",
    "repo-path": ".",
    "module": "codecheck",
    "coverage-report": "reports/coverage.xml",
    "coverage-cutoff": 0.8,
    "parent-branch": "origin/master",
    "include-merges": False,
    "verbose": 0,
    "debug": 0,
    "full-file-test": False,
}


class MyFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    """Class customizing behavior for argparse."""


def parse_input(input_args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse default configuration file and process user inputs."""
    # read the gitcov defaults use values to set defaults to argparse
    toml = {}
    pyproject_toml_path = os.path.join(os.getcwd(), "pyproject.toml")
    if os.path.exists(pyproject_toml_path):
        with open(pyproject_toml_path, "rb") as f:
            toml = tomli.load(f)
    gitcov_config = DEFAULT_CONFIG
    if toml.get("tool") and toml["tool"].get("gitcov"):
        gitcov_config.update(toml["tool"]["gitcov"])
    if toml.get("project") and toml["project"].get("name"):
        gitcov_config["module"] = toml["project"]["name"]

    parser = argparse.ArgumentParser(
        description="""
    Check test coverage of changed lines of code.
!!! For accurate results, make sure to update your reference branch     !!!
!!! The name of reference branch is passed as 'parent_branch' parameter !!!""",
        formatter_class=MyFormatter,
    )
    parser.add_argument(
        "-p",
        "--repo-path",
        required=False,
        default=gitcov_config["repo-path"],
        help="Path to root of repository",
    )
    parser.add_argument(
        "-m",
        "--module",
        required=False,
        default=gitcov_config["module"],
        help="Module for branch coverage analysis",
    )
    parser.add_argument(
        "-cr",
        "--coverage-report",
        required=False,
        default=gitcov_config["coverage-report"],
        help="File containing the XML coverage report",
    )
    parser.add_argument(
        "-cc",
        "--coverage-cutoff",
        required=False,
        default=gitcov_config["coverage-cutoff"],
        help="Cutoff for success",
        type=float,
    )
    parser.add_argument(
        "-b",
        "--parent-branch",
        required=False,
        default=gitcov_config["parent-branch"],
        help="Branch to compare HEAD to",
    )
    parser.add_argument(
        "-i",
        "--include-merges",
        default=bool(gitcov_config["include-merges"]),
        action="store_true",
        required=False,
        help="Include files brought in by merge commits",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        default=bool(gitcov_config["verbose"]),
        required=False,
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "-d",
        "--debug",
        default=bool(gitcov_config["debug"]),
        required=False,
        action="store_true",
        help="Debugging output",
    )
    parser.add_argument(
        "-f",
        "--full-file-test",
        default=bool(gitcov_config["full-file-test"]),
        required=False,
        action="store_true",
        help="Enable full file test instead of branch changes",
    )

    args = parser.parse_args(input_args)

    log_level = logging.WARNING
    if bool(gitcov_config.get("verbose", False)) or args.verbose:
        log_level = logging.INFO
    if bool(gitcov_config.get("debug", False)) or args.debug:
        log_level = logging.DEBUG
    args.log_level = log_level

    assert path.isdir(args.repo_path), f"Repo path '{args.repo_path}' doesn't exist"
    args.repo_path = path.abspath(args.repo_path)
    if not path.isabs(args.coverage_report):
        args.coverage_report = path.normpath(path.join(args.repo_path, args.coverage_report))
    assert path.isfile(
        args.coverage_report
    ), f"Coverage report '{args.coverage_report}' doesn't exist"
    skip_files = cast(str, gitcov_config.get("skip-files", ""))
    args.skip_files = skip_files.replace("\n", "").split(",")

    return args


# pylint: disable=too-many-locals
def get_changed_files(
    repo_path: str,
    include_merges: bool = True,  # pylint: disable=unused-argument # backward compatibility
    parent_branch: str = "origin/master",
    file_extensions: Optional[Iterable[str]] = None,
) -> Sequence[str]:
    """Get a list of changed files.

    :param repo_path: Path to the root of the repository
    :param include_merges: Include changes done via merge-commits
    :param parent_branch: Git branch to compare to
    :param file_extensions: File extensions to be searched
    :return: List of changed files
    """
    # root of project may not be the root of the git repository
    git_top_level = subprocess.check_output(
        f"{GIT_PATH} rev-parse --show-toplevel".split(), text=True
    ).strip()

    repo = git.Repo(git_top_level)

    changed_files: list[str] = []
    untracked = repo.untracked_files
    logger.debug(f"Untracked: {untracked}")
    changed_files.extend(untracked)

    unstaged = [i.a_path for i in repo.index.diff(None)]
    logger.debug(f"Unstaged: {unstaged}")
    changed_files.extend(filter(None, unstaged))

    modified = [i.a_path for i in repo.index.diff("HEAD")]
    logger.debug(f"Modified: {modified}")
    changed_files.extend(filter(None, modified))

    common_commit = repo.merge_base(parent_branch, "HEAD")[0]
    previously_changed = [i.a_path for i in repo.index.diff(common_commit)]
    logger.debug(f"Previously changed: {previously_changed}")
    changed_files.extend(filter(None, previously_changed))

    # remove duplicates
    changed_files = list(set(changed_files))

    # filter files based on extensions
    if file_extensions:
        logger.debug(f"File extension filter: {file_extensions}")
        changed_files = list(filter(lambda x: x.endswith(tuple(file_extensions)), changed_files))
        logger.debug(f"After filter: {changed_files}")

    # root of project may not be the root of the git repository
    # so we need to adjust the paths
    prefix = Path(repo_path).absolute().relative_to(git_top_level)
    logger.debug(f"Project prefix (from repo root): {prefix}")
    project_scope = []
    for f in changed_files:
        try:
            project_scope.append(Path(f).relative_to(prefix).as_posix())
        except ValueError:
            logger.debug(f"File {f} is not in the project scope")
    logger.debug(f"Files after scope check: {len(project_scope)}: {project_scope}")
    return project_scope


def extract_linenumber(base_dir: str, file_path: str, parent_branch: str) -> Sequence[int]:
    """Get changed lines in given file.

    :param base_dir: Path to root of the repository
    :param file_path: Path to file
    :param parent_branch: Git branch to compare to
    :return: List of changed lines in file
    """
    line_regex_str = r"^@@ -\d{1,3}[0-9,]*\s\+(?P<start>\d{1,3}),?(?P<count>\d*)"
    line_regex = re.compile(line_regex_str)

    cmd = f"{GIT_PATH} diff {parent_branch} --unified=0 -- {file_path}"
    logger.debug(f"Executing: {cmd}")
    git_diff = subprocess.check_output(cmd.split(), cwd=base_dir).decode("utf-8")
    line_numbers = []
    for line in git_diff.split("\n"):
        match = line_regex.match(line)
        if match:
            start = int(match.group("start"))
            count = int(match.group("count") or 1)
            for i in range(count):
                line_numbers.append(start + i)
    return line_numbers


def _cov_statement_category(line: Element) -> str:
    """Get the coverage category for one record of statement coverage."""
    hit = int(line.attrib["hits"])
    return "hit" if hit else "miss"


def _cov_branch_category(line: Element) -> str:
    """Get the coverage category for one record of branch coverage."""
    category = _cov_statement_category(line)
    if "missing-branches" in line.attrib:
        category = "partial"
    return category


def extract_coverage(
    cov_report: ElementTree, file_path: str, line_numbers: Optional[Sequence[int]] = None
) -> dict:
    """Extract coverage data for a given file.

    :param cov_report: Parsed xml coverage report
    :param file_path: Path to file to get the data for
    :param line_numbers: List of changed line numbers
    :return: Coverage data for a given file
    """
    lines_elem = cov_report.findall(f".//*/class[@filename='{file_path}']/lines/line")
    data: dict = {
        "statement": {"hit": [], "miss": []},
        "branch": {"hit": [], "miss": [], "partial": []},
    }
    for item in lines_elem:
        line_num = int(item.attrib["number"])
        if line_numbers and line_num not in line_numbers:
            continue
        data["statement"][_cov_statement_category(item)].append(line_num)
        if "branch" in item.attrib:
            data["branch"][_cov_branch_category(item)].append(line_num)
    return data


def uncovered_changed_lines(statement_lines: list, branch_lines: list, changed_lines: list) -> set:
    """Get the set of changed lines which are not covered."""
    all_bad_lines = set(statement_lines).union(set(branch_lines))
    return all_bad_lines.intersection(set(changed_lines))


def calc_statement_coverage(statement_data: dict) -> float:
    """Calculate result statement coverage."""
    hit = len(statement_data["hit"])
    total = hit + len(statement_data["miss"])
    return (hit / total) if total else -1


def calc_branch_coverage(branch_data: dict) -> float:
    """Calculate result branch coverage."""
    hit = len(branch_data["hit"])
    miss = len(branch_data["miss"])
    partial = len(branch_data["partial"])
    total = 2 * (hit + miss + partial)
    if total == 0:
        return -1
    return (2 * hit + partial) / total


def calc_coverage(cov_data: dict) -> Tuple[float, float]:
    """Calculate overall coverage."""
    statement = calc_statement_coverage(cov_data["statement"])
    brach = calc_branch_coverage(cov_data["branch"])
    return statement, brach


def did_pass(number: float, cutoff: float) -> bool:
    """Check whether cutoff threshold is met."""
    return number == -1 or number >= cutoff


def stringify_pass(number: float, cutoff: float) -> str:
    """Stringify threshold result to human-friendly format."""
    msg = "OK" if did_pass(number, cutoff) else "FAILED"
    msg += f" ({number*100:2.2f}%)" if number != -1 else " (Not Used)"
    return msg


def is_skipped(file_path: str, skip_patterns: Sequence[str]) -> bool:
    """Find whether file should qualifies given filer patterns."""
    return any(skip_pattern in file_path for skip_pattern in skip_patterns)


def get_parent_commit() -> str:
    """Returns commit of parent branch.

    Iteratively looks at parent commits of current commit and checks, whether
    the parent commit belongs to different branches. In case it does, this
    should be the point where we branched off and the given commit is returned.

    An exception can be raised in case the repository is empty (fresh new repo)
    or there are no branches.

    :return: sha of found commit
    :raises: CalledProcessError
    """
    # !!!Warning: This approach will fail, if applied for branch B1 to get M!!!
    # M ---A----B-----C
    # B1    \---D--E
    # B2         \---F--G
    #
    # With the above scenario, we want to identify changes between B2 and
    # point we branched of - commit D.
    # To achieve this, the process is following:
    #
    # 1. get the current sha: $ git rev-parse HEAD
    # iterate is_crossroad:
    #   2. get all branches the commit is part of: $ git branch -a --contains {SHA}
    #   3. check whether returned branches contain other branches except the one
    #   we are on (crossroad)
    #   4. we haven't found a crossroad, get next sha: $ git rev-parse {SHA}^
    #
    # Example:
    # get commit G sha
    # Check all branches G is part of
    # G is only part of B2
    # Get next commit F sha
    # Check all branches F is part of
    # F is only part of B2
    # Get next commit D sha
    # Check all branches D is part of
    # D is part of B1 and B2 branches
    # We are on a crossroad -> return D sha
    cmd = f"{GIT_PATH} rev-parse HEAD"
    current_sha = subprocess.check_output(cmd.split(), text=True).strip()
    logging.debug(f"Initial sha: {current_sha}")

    cmd = f"{GIT_PATH} rev-list --merges {current_sha}"
    merge_commits = subprocess.check_output(cmd.split(), text=True).strip().split("\n")

    while 1:
        # first check if we're not on a merge commit
        if current_sha in merge_commits:
            break

        cmd = f"{GIT_PATH} branch -a --contains {current_sha}"
        current_branches = subprocess.check_output(cmd.split(), text=True)

        branches = list(filter(None, current_branches.split("\n")))
        logging.debug(f"All branches containing sha {current_sha}: {branches}")

        cmd = f"{GIT_PATH} rev-parse --abbrev-ref HEAD"
        current_branch = subprocess.check_output(cmd.split(), text=True).strip()
        logging.debug(f"We are on branch: {current_branch}")

        on_crossroad = False
        for branch in branches:
            if current_branch not in branch:
                on_crossroad = True
                break

        if on_crossroad is True:
            break

        cmd = f"{GIT_PATH} rev-parse {current_sha}^"
        current_sha = subprocess.check_output(cmd.split(), text=True).strip()
        logging.debug(f"Parent sha: {current_sha}")

    return current_sha


def main(argv: Optional[Sequence[str]] = None) -> int:  # pylint:disable=too-many-locals
    """Main function."""
    args = parse_input(argv)

    default_log_level = args.log_level
    logger.setLevel(default_log_level)
    logger.handlers[0].setLevel(default_log_level)

    logger.debug(args)

    files = get_changed_files(
        repo_path=args.repo_path,
        parent_branch=args.parent_branch,
        include_merges=args.include_merges,
    )
    files = [f for f in files if f.startswith(args.module)]
    logger.debug(f"files to process: {len(files)}: {files}\n")
    cov_report = xml_parse(args.coverage_report)
    error_counter = 0

    for f in files:
        is_skipped_file = is_skipped(f, args.skip_files)
        git_numbers = extract_linenumber(args.repo_path, f, args.parent_branch)
        # the coverage.xml removes the module name from path
        sanitized_name = f.replace(f"{args.module}/", "")
        cov_numbers = extract_coverage(
            cov_report, sanitized_name, None if args.full_file_test else git_numbers
        )
        statement_cov, branch_cov = calc_coverage(cov_numbers)
        changed_uncovered_lines = uncovered_changed_lines(
            cov_numbers["statement"]["miss"], cov_numbers["branch"]["miss"], list(git_numbers)
        )
        no_fails = statement_cov * branch_cov in (1.0, -1.0)
        critical_fails = not no_fails and not is_skipped_file

        if not did_pass(statement_cov, args.coverage_cutoff) and not is_skipped_file:
            error_counter += 1
        if not did_pass(branch_cov, args.coverage_cutoff) and not is_skipped_file:
            error_counter += 1

        # Change temporary, if needed, log level to print interesting information
        if critical_fails and logger.level > logging.INFO:
            logger.handlers[0].setLevel(logging.INFO)
            logger.setLevel(logging.INFO)

        logger.info(f"processing: {f}")

        if is_skipped_file:
            logger.info("The file is skipped and will not contribute to the error counter.")
            if logger.level > logging.DEBUG:
                logger.info("")  # Just add a new line
                continue

        logger.debug(f"git lines: {git_numbers}")
        logger.debug(f"cov lines: {cov_numbers}")

        if no_fails:
            logger.info("File is fully covered.\n")
        else:
            changed_uncovered_lines_msg = (
                changed_uncovered_lines if changed_uncovered_lines != set() else "None"
            )
            logger.info(f"changed uncovered lines: {changed_uncovered_lines_msg}")
            logger.info(f"uncovered lines: {cov_numbers['statement']['miss']}")
            logger.info(f"uncovered branches: {cov_numbers['branch']['miss']}")
            logger.info(f"partially covered branches: {cov_numbers['branch']['partial']}")
            logger.info(
                f"Statement coverage: {stringify_pass(statement_cov, args.coverage_cutoff)}"
            )
            logger.info(f"Branch coverage: {stringify_pass(branch_cov, args.coverage_cutoff)}\n")

        # Return back log level to default value
        logger.handlers[0].setLevel(default_log_level)
        logger.setLevel(default_log_level)

    if error_counter == 0:
        logger.info("No errors found")
    else:
        logger.error(f"Total errors: {error_counter}")

    return error_counter


if __name__ == "__main__":
    sys.exit(main())
