#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

from typing import Any, Dict, List, Optional, Set, Tuple

from spsdk.crypto.keys import PrivateKey


def fun(params: List[str]) -> Tuple[int, int]: ...


def fun2(param: Dict) -> dict: ...


class Nieco:
    param: Optional[List] = None


l1: List = [1, 2, 3]

d: Dict[str, Any] = {}

l2: Optional[List[PrivateKey]] = None

s: Set[int] = set()
