#!/usr/bin/env python
#
# Copyright 2024-2026 NXP
# Copyright 2025 Oidis
#
# SPDX-License-Identifier: BSD-3-Clause
"""Helpers for selecting the PyUSB libusb backend."""

from __future__ import annotations

import importlib
import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


def _import_optional(module_name: str) -> Any:
    """Import an optional module."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


usb_backend_libusb1 = _import_optional("usb.backend.libusb1")
libusb_package = _import_optional("libusb_package")


@lru_cache(maxsize=1)
def get_usb_backend() -> Any | None:
    """Get the configured PyUSB backend."""
    if usb_backend_libusb1 is None:
        return None
    if libusb_package is not None:
        if (
            backend := usb_backend_libusb1.get_backend(find_library=libusb_package.find_library)
        ) is not None:
            return backend
        logger.debug("libusb_package backend unavailable, falling back to system libusb")
        return usb_backend_libusb1.get_backend()
    return None
