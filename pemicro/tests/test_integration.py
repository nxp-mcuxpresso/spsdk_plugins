#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for `spsdk_pemicro` package integration in SPSDK."""

from click.testing import CliRunner
from spsdk.apps import nxpdebugmbox


def test_integration():
    runner = CliRunner()
    result = runner.invoke(nxpdebugmbox.main, "--help")
    assert "pemicro" in result.output
