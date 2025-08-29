#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Script to check Jupyter Notebook consistency."""

import argparse
import json
import logging
import os
import pathlib
import sys
from typing import Dict, List, Optional, Union

import tomli

JUPYTER_EXTENSIONS = ("ipynb",)
REPO_ROOT = os.getcwd()


logger = logging.getLogger(__name__)


def outputs(sources: List[str], exceptions: Dict[str, List[Union[str, int]]]) -> int:
    """Command for checking that code cells have output."""
    error_counter = 0
    file_counter = 0
    for source in sources:
        if os.path.isfile(source) and source.endswith(JUPYTER_EXTENSIONS):
            file_counter += 1
            error_counter += check_jupyter_output(path=source, exceptions=exceptions)
        if os.path.isdir(source):
            for root, _, files in os.walk(source):
                if root.endswith(".ipynb_checkpoints"):
                    continue
                for file in files:
                    if file.endswith(JUPYTER_EXTENSIONS):
                        file_counter += 1
                        error_counter += check_jupyter_output(
                            os.path.join(root, file), exceptions=exceptions
                        )

    print(f"Found {error_counter} errors in {file_counter} files.")
    return error_counter


def check_jupyter_output(  # pylint: disable=too-many-locals,too-many-branches
    path: str, exceptions: Dict[str, List[Union[str, int]]]
) -> int:
    """Checker of Jupyter notebook outputs.

    :param path: Filename of Jupiter notebook
    :param exceptions: Dictionary with notebook exceptions
    :return: Result of operation
    """
    full_path = pathlib.Path(path).absolute().resolve()
    logger.debug(f"Checking {full_path}")
    with open(full_path, encoding="utf-8") as f:
        data = json.load(f)
    if "cells" not in data or len(data["cells"]) == 0:
        print(f"File {full_path} doesn't have any cells")
        return 1
    error_count = 0
    file_was_modified = False
    rel_dir = full_path.relative_to(REPO_ROOT).parent.as_posix()
    rel_path = full_path.relative_to(REPO_ROOT).as_posix()
    exec_counter = 1

    for cell_id, cell in enumerate(data["cells"]):
        if cell["cell_type"] != "code":
            continue

        exec_count = cell.get("execution_count", None)
        if exec_count is not None:
            if exec_count != exec_counter:
                print(
                    f"{full_path}: Execution count mismatch in cell {cell_id}. "
                    f"Expected {exec_counter}, got {exec_count}"
                )
                data["cells"][cell_id]["execution_count"] = exec_counter
                file_was_modified = True
                error_count += 1
        exec_counter += 1

        if len(cell["outputs"]) == 0:
            # if there's an exception record for this file
            # and record contains either this cell number or "*"
            if rel_path in exceptions:
                if "*" == exceptions[rel_path] or cell_id in exceptions[rel_path]:
                    logger.debug(f"{full_path} cell #{cell_id} is amongst exceptions")
                    continue
            # cell was executed, but didn't produce any output
            if cell["execution_count"] and cell["execution_count"] > 0:
                logger.debug(f"{full_path} cell #{cell_id} doesn't provide an output")
                continue
            print(f"{full_path} cell #{cell_id} doesn't have output")
            error_count += 1

        for output_block_id, output_block in enumerate(cell["outputs"]):
            if "text" not in output_block:
                logger.debug(
                    f"{full_path} cell #{cell_id} output block #{output_block_id} doesn't have text member"
                )
                continue
            for line_id, line in enumerate(output_block["text"]):
                words: List[str] = line.split()
                line_was_modified = False
                for word_id, word in enumerate(words):
                    word = word.replace("\\", "/")
                    if rel_dir in word:
                        words[word_id] = word.split(rel_dir + "/")[-1]
                        file_was_modified = line_was_modified = True
                if line_was_modified:
                    output_block["text"][line_id] = " ".join(words) + "\n"
            cell["outputs"][output_block_id]["text"] = output_block["text"]
        data["cells"][cell_id]["outputs"] = cell["outputs"]

    if file_was_modified:
        print(f"Rewriting {full_path}")
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
    return error_count


def parse_inputs(input_args: Optional[List[str]] = None) -> dict:
    """Parse input CLI arguments.

    :param input_args: CLI arguments, defaults to None
    :return: Dictionary with input arguments
    """
    parser = argparse.ArgumentParser(
        description="Tool for checking Jupyter Notebook's consistency.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug messages")

    subcommands = parser.add_subparsers(dest="command", metavar="SUB-COMMAND", required=True)

    outputs_parser = subcommands.add_parser(
        "outputs", help="Command for checking that code cells have output."
    )
    outputs_parser.add_argument(
        "sources",
        nargs="*",
        metavar="SOURCE",
        help=(
            "Path(s) to Notebooks or directory(ies) where to look for Notebooks. "
            "Every directory is traversed recursively."
        ),
    )

    args = vars(parser.parse_args(input_args))
    return args


def main(input_args: Optional[List[str]] = None) -> int:
    """Jupyter notebook checker.

    :param input_args: Input CLI arguments., defaults to None
    :return: Application result, 0 succeeded, otherwise failed
    """
    args = parse_inputs(input_args=input_args)
    logging.basicConfig(level=logging.DEBUG if args["debug"] else logging.WARNING)

    logger.debug(f"Inputs: {args}")
    exceptions = {}
    pyproject_toml_path = os.path.join(os.getcwd(), "pyproject.toml")
    if os.path.exists(pyproject_toml_path):
        with open(pyproject_toml_path, "rb") as f:
            toml = tomli.load(f)
            if toml.get("tool") and toml["tool"].get("checker_jupiter"):
                exceptions = toml["tool"]["checker_jupiter"].get("exceptions", {})

    error_code = 0
    if args["command"] == "outputs":
        error_code = outputs(sources=args["sources"], exceptions=exceptions)

    return error_code


if __name__ == "__main__":
    sys.exit(main())
