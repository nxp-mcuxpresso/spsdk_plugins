#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Top-level package for P&E Micro debugger probe plugin."""

__author__ = """NXP"""
__email__ = "starecek.michal@nxp.com"
__version__ = "0.1.2"

from .probe import DebugProbePemicro

__all__ = ["DebugProbePemicro"]
