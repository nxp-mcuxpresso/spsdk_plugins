#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# * ********************************************************************************************************* *
# *
# * Copyright 2024 NXP
# *
# * SPDX-License-Identifier: BSD-3-Clause
# * The BSD-3-Clause license for this file can be found in the LICENSE.txt file included with this distribution
# * or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText
# *
# * ********************************************************************************************************* *

"""Tests for `spsdk_mcu_link` package integration in SPSDK."""

from click.testing import CliRunner
from spsdk.apps import nxpdebugmbox


def test_integration():
    runner = CliRunner()
    result = runner.invoke(nxpdebugmbox.main, "--help")
    if "mcu-link" not in result.output:
        raise AssertionError("mcu-link not found in --help")
