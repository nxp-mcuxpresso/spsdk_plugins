#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Checker of Python code cyclic imports."""

import argparse
import os
import shlex
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Dict, Iterator, List, Optional


def check_file(path: str) -> int:
    """Check a one Python file against cyclic imports.

    :param path: File name
    :return: 0 for success, 1 for cyclic import detected
    """
    output = subprocess.run(
        shlex.split(f'"{sys.executable}" {path}'), text=True, check=False, capture_output=True
    )
    if "(most likely due to a circular import)" in output.stderr + output.stdout:
        print(output.stderr + output.stdout)
        return 1
    return 0


def collect_files(sources: List[str]) -> Iterator[str]:
    """Collect all python files in project.

    :param sources: List of folders or files
    :yield: One file path
    """
    for source in sources:
        if os.path.isfile(source) and source.endswith(".py"):
            yield source
        if os.path.isdir(source):
            for root, _, files in os.walk(source):
                yield from collect_files([os.path.join(root, f) for f in files])


def parse_inputs(input_args: Optional[List[str]] = None) -> Dict[str, Any]:
    """Parse input application arguments.

    :param input_args: Input string with arguments, defaults to None
    :return: The dictionary with input arguments
    """
    parser = argparse.ArgumentParser(
        description="Tool for checking cyclic imports",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-j", "--jobs", default=os.cpu_count() or 1, type=int)
    parser.add_argument(
        "sources",
        nargs="*",
        metavar="SOURCE",
        help="Path(s) to python files or directories with python files",
    )
    args = vars(parser.parse_args(input_args))
    return args


def main(input_args: Optional[List[str]] = None) -> int:
    """Checker against cyclic imports.

    :param input_args: Input CLI arguments, defaults to None
    :return: 0 for success, 1 cyclic import detected
    """
    args = parse_inputs(input_args)

    files = list(collect_files(sources=args["sources"]))
    print(f"Checking {len(files)} files")

    with ProcessPoolExecutor(max_workers=args["jobs"]) as executor:
        tasks = executor.map(check_file, files)
    error_code = sum(tasks)

    print(f"Found {error_code} errors in {len(files)} files")
    return error_code


if __name__ == "__main__":
    sys.exit(main())
