# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Top-level package for PKCS#11 Signature Provider."""

__author__ = """NXP"""
__email__ = "michal.starecek@nxp.com"
__version__ = "0.1.1"

from .provider import PKCS11SP

__all__ = ["PKCS11SP"]
