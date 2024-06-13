#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Tests for `codecheck` package."""


import unittest

from click.testing import CliRunner

from codecheck import main


class TestCodecheck(unittest.TestCase):
    """Tests for `codecheck` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_000_something(self):
        """Test something."""

    def test_command_line_interface(self):
        """Test the CLI."""
        runner = CliRunner()
        help_result = runner.invoke(main.main, ["--help"])
        assert help_result.exit_code == 0
        assert "Usage: codecheck" in help_result.output
        assert "Usage: codecheck" in help_result.output
