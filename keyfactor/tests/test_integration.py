#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Tests for `keyfactor_sp` package."""

from spsdk.crypto.signature_provider import SignatureProvider

from spsdk_keyfactor import KeyfactorSP


def test_registration() -> None:
    """Test whether KeyfactorSP got picked up by SPSDK."""
    assert KeyfactorSP.identifier in SignatureProvider.get_types()
