#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Wrapper for Dilithium library."""

import platform
from distutils.command.build_ext import build_ext

from setuptools import Extension, setup


class CTypesExtension(Extension):
    pass


class build_ctypes_ext(build_ext):
    def build_extension(self, ext) -> None:
        self._ctypes = isinstance(ext, CTypesExtension)
        return super().build_extension(ext)

    def get_ext_filename(self, ext_name: str) -> str:
        if self._ctypes:
            return ext_name + ".so"
        return super().get_ext_filename(ext_name)

    def get_export_symbols(self, ext: CTypesExtension):
        if self._ctypes:
            return ext.export_symbols
        return super().get_export_symbols(ext)


if platform.system() == "Windows":
    c_args = ["/nologo", "/O2", "/W4", "/wd4146", "/wd4244"]
    l_libs = ["advapi32"]
else:
    c_args = ["-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O3"]
    l_libs = []

sources = [
    "ref/sign.c",
    "ref/packing.c",
    "ref/polyvec.c",
    "ref/poly.c",
    "ref/ntt.c",
    "ref/reduce.c",
    "ref/rounding.c",
    "ref/randombytes.c",
    "ref/symmetric-shake.c",
    "ref/fips202.c",
]


def make_extension(level: int) -> CTypesExtension:
    return CTypesExtension(
        f"spsdk_pqc._dil{level}",
        define_macros=[("DILITHIUM_MODE", str(level)), ("DILITHIUM_RANDOMIZED_SIGNING", "1")],
        include_dirs=["ref"],
        sources=sources,
        extra_compile_args=c_args,
        libraries=l_libs,
    )


setup(
    ext_modules=[
        make_extension(level=2),
        make_extension(level=3),
        make_extension(level=5),
    ],
    cmdclass={"build_ext": build_ctypes_ext},
)
