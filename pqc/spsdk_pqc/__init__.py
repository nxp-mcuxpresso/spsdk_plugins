#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Wrapper for Dilithium library."""

__author__ = """NXP"""
__email__ = "michal.starecek@nxp.com"
__version__ = "0.3.1"

from .wrapper import DilithiumPrivateKey, DilithiumPublicKey

__all__ = ["DilithiumPrivateKey", "DilithiumPublicKey"]
