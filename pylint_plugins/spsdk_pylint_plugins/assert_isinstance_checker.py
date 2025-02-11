#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""When using click.Choice option, check if case_sensitive is set to True."""

import astroid
from pylint.checkers import BaseChecker


class AssertIsinstanceChecker(BaseChecker):
    """When using click.Choice option, check if case_sensitive is set to True."""

    name = "disallowed-assert"
    msgs = {
        "W9801": (
            "Only assert isinstance is allowed",
            "assert-instance",
            "Only assert isinstance is allowed",
        )
    }

    def visit_assert(self, node: astroid.Assert) -> None:
        """Checked assert statement: assert isinstance(x, y) [and/or isinstance(j, k)]..."""
        if isinstance(node.test, astroid.Call) and isinstance(node.test.func, astroid.Name):
            if node.test.func.name == "isinstance":
                return
        if isinstance(node.test, astroid.BoolOp):
            if all(isinstance(val, astroid.Call) for val in node.test.values):
                if all(val.func.name == "isinstance" for val in node.test.values):
                    return
        self.add_message("assert-instance", node=node)
