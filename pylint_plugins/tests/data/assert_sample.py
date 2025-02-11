#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

str_var = "var"
int_var = 1

# Errors
assert str_var
assert str_var and int_var
assert isinstance(str_var, str) or int_var

# OK
assert isinstance(str_var, str)
assert isinstance(str_var, (str, int))
assert isinstance(int_var, int) and isinstance(str_var, str)
