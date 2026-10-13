#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for `spsdk_el2go` package."""

from spsdk.crypto.signature_provider import SignatureProvider
from spsdk.sbfile.utils.key_derivator import SB31KeyDerivator

from spsdk_el2go import EL2GoKDP, EL2GoSP


def test_sp_registration() -> None:
    """Test whether EL2GoSP got picked up by SPSDK."""
    assert EL2GoSP.identifier in SignatureProvider.get_types()


def test_kdp_registration() -> None:
    """Test whether EL2GoKDP got picked up by SPSDK."""
    assert EL2GoKDP.identifier in SB31KeyDerivator.get_types()
