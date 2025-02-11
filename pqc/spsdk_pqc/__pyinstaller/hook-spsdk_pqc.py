#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

# pylint: disable=invalid-name, import-error

"""Add hidden imports, binaries, and data for this package."""

from PyInstaller.utils.hooks import collect_dynamic_libs, copy_metadata

hiddenimports = ["spsdk_pqc"]

datas = copy_metadata("spsdk_pqc")

binaries = collect_dynamic_libs("spsdk_pqc", search_patterns=["*.so"])
