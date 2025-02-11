#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Tests for `spsdk_mcu_link` package integration in SPSDK."""

from click.testing import CliRunner
from spsdk.apps import nxpdebugmbox


def test_integration():
    runner = CliRunner()
    result = runner.invoke(nxpdebugmbox.main, "--help")
    if "mcu-link" not in result.output:
        raise AssertionError("mcu-link not found in --help")
