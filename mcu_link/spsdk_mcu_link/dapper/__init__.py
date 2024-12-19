#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

# noqa: D205, D212, D415
"""
SPSDK MCU Link Dapper Module
============================

This module provides interfaces for working with Dapper debug probes.

Components
---------
* DapperFactory: Factory class for creating Dapper instances
* DapperProbeInfo: Class containing probe information
* WebixDapper: Main Dapper implementation class
* WebixDapperWasm: WASM-based Dapper implementation
* Uint8Array: Type for handling byte arrays
* Interface: Enumeration of available interfaces
"""

from .webix_dapper import DapperFactory, DapperProbeInfo, Interface, WebixDapper
from .webix_dapper_wasm import Uint8Array, WebixDapperWasm

__all__ = [
    "DapperFactory",
    "DapperProbeInfo",
    "WebixDapper",
    "WebixDapperWasm",
    "Uint8Array",
    "Interface",
]
