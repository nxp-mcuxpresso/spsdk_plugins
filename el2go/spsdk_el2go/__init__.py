#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Top-level package for el2go_signature_provider."""

__author__ = """NXP"""
__email__ = "spsdk@nxp.com"
__version__ = "0.2.0"

from .key_derivation_provider import EL2GoKDP
from .signature_provider import EL2GoSP

__all__ = ["EL2GoKDP", "EL2GoSP"]
