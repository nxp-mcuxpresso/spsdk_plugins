#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

# pylint: disable=invalid-name, import-error

"""Add hidden imports, binaries, and data for this package."""

from PyInstaller.utils.hooks import PY_DYLIB_PATTERNS, collect_data_files, collect_dynamic_libs

hiddenimports = ["spsdk_mcu_link"]

datas = collect_data_files("spsdk_mcu_link")
binaries = collect_dynamic_libs("wasmtime", search_patterns=PY_DYLIB_PATTERNS + ["_lib*.so"])
