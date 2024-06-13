#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for `pkcs11` package."""

from spsdk.crypto.signature_provider import SignatureProvider

from spsdk_pkcs11 import PKCS11SP


def test_registration() -> None:
    """Test whether PKCS11SP got picked up by SPSDK."""
    assert PKCS11SP.identifier in SignatureProvider.get_types()
