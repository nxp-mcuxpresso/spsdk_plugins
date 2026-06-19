#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""SPSDK IPED - Fast C++ PRINCE cipher backend for IPED encryption."""

__author__ = "NXP"
__email__ = "spsdk@nxp.com"
__version__ = "0.1.0"

from .iped import IPED, IPEDError

__all__ = ["IPED", "IPEDError"]
