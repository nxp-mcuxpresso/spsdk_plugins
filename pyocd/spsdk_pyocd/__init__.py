#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Top-level package for PyOCD SW Debugger."""

__author__ = """NXP"""
__email__ = "michal.starecek@nxp.com"
__version__ = "0.1.1"

from .probe import DebugProbePyOCD

__all__ = ["DebugProbePyOCD"]
