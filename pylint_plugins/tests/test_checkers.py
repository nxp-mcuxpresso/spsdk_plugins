#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause


import json
from io import StringIO
from pathlib import Path

import pytest
from pylint.lint import Run
from pylint.reporters import JSON2Reporter

THIS_DIR = Path(__file__).parent


def run_checker(sample: str, checker: str) -> int:
    file = THIS_DIR.joinpath("data", sample).as_posix()
    pylint_output = StringIO()
    reporter = JSON2Reporter(pylint_output)
    Run(
        [
            file,
            "--load-plugins=spsdk_pylint_plugins",
            f"--enable={checker}",
            "--disable=all",
        ],
        reporter=reporter,
        exit=False,
    )
    results = json.loads(pylint_output.getvalue())
    return len(results["messages"])


@pytest.mark.parametrize(
    "checker, sample, error_count",
    [
        ("click-choice", "click_sample.py", 3),
        ("disallowed-assert", "assert_sample.py", 3),
        ("disallowed-type-annotation", "typing_sample.py", 8),
    ],
)
def test_click_choice_checker(checker: str, sample: str, error_count: int) -> None:
    result = run_checker(checker=checker, sample=sample)
    assert result == error_count
