#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Setup script with C++ extension compilation for PRINCE cipher library."""

from distutils.command.build_ext import build_ext

from setuptools import Extension, setup


class CTypesExtension(Extension):
    """Extension subclass for ctypes shared libraries."""


class BuildCtypesExtension(build_ext):
    """Custom build_ext that produces a plain .so instead of Python extension module."""

    def build_extension(self, ext) -> None:  # type: ignore[override]
        """Build the extension module."""
        self._ctypes = isinstance(ext, CTypesExtension)
        return super().build_extension(ext)

    def get_ext_filename(self, ext_name: str) -> str:
        """Get output filename without Python ABI suffix for ctypes libs."""
        if self._ctypes:
            return ext_name.replace(".", "/") + ".so"
        return super().get_ext_filename(ext_name)

    def get_export_symbols(self, ext: Extension) -> list:
        """Get export symbols for ctypes extension."""
        if self._ctypes:
            return ext.export_symbols  # type: ignore[return-value]
        return super().get_export_symbols(ext)


prince_lib = CTypesExtension(
    name="spsdk_iped.prince",
    sources=[
        "src/ip_prince_ctr.cpp",
        "src/ip_prince_model.cpp",
        "src/PrinceCore.cpp",
    ],
    include_dirs=["src"],
)


setup(
    ext_modules=[prince_lib],
    cmdclass={"build_ext": BuildCtypesExtension},
)
