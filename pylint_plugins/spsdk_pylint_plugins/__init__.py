#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Top-level package for PyLint extensions for SPSDK coding style."""

__author__ = """NXP"""
__email__ = "michal.starecek@gmail.com"
__version__ = "0.2.2"

from pylint.lint import PyLinter

from .assert_isinstance_checker import AssertIsinstanceChecker
from .click_choice_check import ClickChoiceChecker
from .typing_checker import TypingChecker


def register(linter: PyLinter) -> None:
    """Register all SPSDK plugins."""
    checkers = linter.get_checker_names()
    if ClickChoiceChecker.name not in checkers:
        linter.register_checker(ClickChoiceChecker(linter))
    if AssertIsinstanceChecker.name not in checkers:
        linter.register_checker(AssertIsinstanceChecker(linter))
    if TypingChecker.name not in checkers:
        linter.register_checker(TypingChecker(linter))
