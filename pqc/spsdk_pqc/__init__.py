#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Wrapper for Dilithium library."""

__author__ = """NXP"""
__email__ = "michal.starecek@nxp.com"
__version__ = "0.6.1"

from .errors import PQCError
from .wrapper import (
    DISABLE_DIL_MLDSA_PUBLIC_KEY_MISMATCH_WARNING,
    DilithiumPrivateKey,
    DilithiumPublicKey,
    MLDSAPrivateKey,
    MLDSAPublicKey,
    PQCAlgorithm,
)

__all__ = [
    "DISABLE_DIL_MLDSA_PUBLIC_KEY_MISMATCH_WARNING",
    "DilithiumPrivateKey",
    "DilithiumPublicKey",
    "MLDSAPrivateKey",
    "MLDSAPublicKey",
    "PQCAlgorithm",
    "PQCError",
]
