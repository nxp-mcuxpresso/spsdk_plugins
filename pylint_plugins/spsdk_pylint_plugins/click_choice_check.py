#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""When using click.Choice option, check if case_sensitive is set to True."""

import astroid
from pylint.checkers import BaseChecker


class ClickChoiceChecker(BaseChecker):
    """When using click.Choice option, check if case_sensitive is set to True."""

    name = "click-choice"
    msgs = {
        "W9901": (
            "Click.Choice is case sensitive",
            "case-sensitive-choice",
            "The Click.Choice argument must be case in-sensitive",
        )
    }

    def visit_keyword(self, node: astroid.Keyword) -> None:
        """Checked keyword statement: type=[click.]Choice([...], case_sensitive=...)."""
        if node.arg == "type" and isinstance(node.value, astroid.Call):
            f = node.value.func

            if (
                isinstance(f, astroid.Name)
                and f.name == "Choice"
                or isinstance(f, astroid.Attribute)
                and f.attrname == "Choice"  # cspell: ignore attrname
            ):
                # check if `case_sensitive` is set
                for kw in node.value.keywords:
                    if kw.arg == "case_sensitive":
                        if kw.value.value:
                            self.add_message("case-sensitive-choice", node=node)
                        break
                else:
                    self.add_message("case-sensitive-choice", node=node)
