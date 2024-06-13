#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

import json
from io import StringIO
from pathlib import Path

from pylint.lint import Run
from pylint.reporters import JSON2Reporter

THIS_DIR = Path(__file__).parent


def test_checker():
    file = THIS_DIR.joinpath("sample.py").as_posix()
    pylint_output = StringIO()
    reporter = JSON2Reporter(pylint_output)
    Run(
        [
            file,
            "--load-plugins=spsdk_pylint_plugins",
            "--enable=click-choice",
            "--disable=all",
        ],
        reporter=reporter,
        exit=False,
    )
    results = json.loads(pylint_output.getvalue())
    assert len(results["messages"]) == 3
