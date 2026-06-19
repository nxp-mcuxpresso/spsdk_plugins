#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Wrapper for Dilithium library."""

__author__ = """NXP"""
__email__ = "spsdk@nxp.com"
__version__ = "0.7.1"

try:
    from spsdk.__version__ import version, version_tuple
except ImportError as exc:
    raise RuntimeError("Unable to detect SPSDK version. Is SPSDK installed?") from exc


MIN_SPSDK_VERSION = (3, 10)
MIN_SPSDK_VERSION_STR = ".".join(str(i) for i in MIN_SPSDK_VERSION)

if version_tuple < MIN_SPSDK_VERSION:
    raise RuntimeError(
        f"You are using old version of SPSDK ({version}). "
        f"Please update SPSDK to at least version: {MIN_SPSDK_VERSION_STR}"
    )

# pylint: disable=wrong-import-position
from .errors import PQCError  # noqa: E402
from .wrapper import (  # noqa: E402
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
