#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Check if legacy typing annotations are not used."""

import astroid
from pylint.checkers import BaseChecker


class TypingChecker(BaseChecker):
    """Check if legacy typing annotations are not used."""

    name = "disallowed-typing"
    msgs = {
        "W9701": (
            "Don't use typing.%s, use %s instead",
            "disallowed-type-annotation",
            "Don't use typing.%s, use %s instead",
        )
    }

    obsolete_types = {"List": "list", "Dict": "dict", "Tuple": "tuple", "Set": "set"}

    def visit_name(self, node: astroid.Name) -> None:
        """Search for names: List, Dict, Tuple, and Set."""
        if node.name in self.obsolete_types:

            self.add_message(
                "disallowed-type-annotation",
                node=node,
                args=(node.name, self.obsolete_types[node.name]),
            )
