#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Wrapper for Dilithium library."""

import os
import platform
import shutil
import subprocess

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class CMakeExtension(Extension):
    def __init__(self, name, cmake_lists_dir="./ref", sources=[], **kwa):
        Extension.__init__(self, name, sources=sources, **kwa)
        self.cmake_lists_dir = os.path.abspath(cmake_lists_dir)


class CMakeBuild(build_ext):

    def get_ext_filename(self, fullname):
        return "spsdk_pqc/liboqs.so"

    def get_ext_fullpath(self, ext_name):
        return f"{self.build_lib}/spsdk_pqc/liboqs.so"

    def build_extensions(self):
        if not shutil.which("cmake"):
            raise RuntimeError("Cannot find CMake executable")

        for ext in self.extensions:

            extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))
            cfg = "Release"

            cmake_args = [
                "-DBUILD_SHARED_LIBS=ON",
                "-DOQS_BUILD_ONLY_LIB=ON",
                "-DOQS_USE_OPENSSL=OFF",
                "-DOQS_MINIMAL_BUILD=SIG_dilithium_2;SIG_dilithium_3;SIG_dilithium_5;SIG_ml_dsa_44;SIG_ml_dsa_65;SIG_ml_dsa_87",
                "-DCMAKE_BUILD_TYPE=%s" % cfg,
                "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}".format(cfg.upper(), extdir),
                "-DCMAKE_ARCHIVE_OUTPUT_DIRECTORY_{}={}".format(cfg.upper(), self.build_temp),
            ]

            if platform.system() == "Windows":
                plat = "x64" if platform.architecture()[0] == "64bit" else "Win32"
                cmake_args += [
                    "-DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=TRUE",
                    "-DCMAKE_RUNTIME_OUTPUT_DIRECTORY_{}={}".format(cfg.upper(), extdir),
                ]
                if self.compiler.compiler_type == "msvc":
                    cmake_args += [
                        "-DCMAKE_GENERATOR_PLATFORM=%s" % plat,
                    ]
                else:
                    cmake_args += [
                        "-G",
                        "MinGW Makefiles",
                    ]

            if not os.path.exists(self.build_temp):
                os.makedirs(self.build_temp)
            # Config and build the extension
            subprocess.check_call(["cmake", ext.cmake_lists_dir] + cmake_args, cwd=self.build_temp)
            subprocess.check_call(["cmake", "--build", ".", "--config", cfg], cwd=self.build_temp)


setup(
    ext_modules=[CMakeExtension("spsdk_pqc.liboqs")],
    cmdclass={"build_ext": CMakeBuild},
)
