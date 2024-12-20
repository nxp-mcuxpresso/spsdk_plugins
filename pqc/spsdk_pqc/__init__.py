#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Wrapper for Dilithium library."""

__author__ = """NXP"""
__email__ = "michal.starecek@nxp.com"
__version__ = "0.5.1"

from .errors import PQCError
from .wrapper import (
    DilithiumPrivateKey,
    DilithiumPublicKey,
    MLDSAPrivateKey,
    MLDSAPublicKey,
    PQCAlgorithm,
)

__all__ = [
    "DilithiumPrivateKey",
    "DilithiumPublicKey",
    "MLDSAPrivateKey",
    "MLDSAPublicKey",
    "PQCAlgorithm",
    "PQCError",
]
