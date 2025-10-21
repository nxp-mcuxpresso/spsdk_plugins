#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

# pylint: disable=invalid-name, import-error

"""Add hidden imports, binaries, and data for this package."""

from PyInstaller.utils.hooks import PY_DYLIB_PATTERNS, collect_dynamic_libs, copy_metadata

hiddenimports = ["spsdk_pemicro"]

datas = copy_metadata("spsdk_pemicro")

binaries = collect_dynamic_libs("pypemicro", search_patterns=PY_DYLIB_PATTERNS + ["*.so"])
