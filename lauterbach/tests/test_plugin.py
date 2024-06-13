#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for `spsdk-lauterbach` package."""

from click.testing import CliRunner
from spsdk.apps import nxpdebugmbox


def test_integration():
    runner = CliRunner()
    result = runner.invoke(nxpdebugmbox.main, "--help")
    assert "lauterbach" in result.output
