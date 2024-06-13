#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Top-level package for PyLint extensions for SPSDK coding style."""

__author__ = """NXP"""
__email__ = "michal.starecek@gmail.com"
__version__ = "0.1.1"

from pylint.lint import PyLinter

from .click_choice_check import ClickChoiceChecker


def register(linter: PyLinter) -> None:
    """Register all SPSDK plugins."""
    # Sometimes PyLint calls register method twice
    # pylint: disable=protected-access
    if ClickChoiceChecker.name not in linter._checkers:
        linter.register_checker(ClickChoiceChecker(linter))
