#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Unit test package for Dilithium wrapper."""
import site
import sys

# TODO Find better solution for this "dirty" workaround

# In spsdk_pqc, the dll location is determined from the location of wrapper.py file.
# As local package directory is used as first entry in sys.path, the local package files
# takes precedence over the installed package spsdk_pqc.

# Remove the local package directory reference, so it ensures the installed package is used instead
sys.path = [p for p in sys.path if not p.endswith("pqc")]
# recalculate site package path
site.main()
# re-import
import spsdk_pqc  # noqa: E402, F401
