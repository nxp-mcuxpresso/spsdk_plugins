#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2023,2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Tests for `offline_signature_provider` package."""

from spsdk.crypto.signature_provider import SignatureProvider

from spsdk_offline_signature_provider import OfflineSP


def test_registration():
    """Test whether OfflineSP got picked up by SPSDK."""
    assert OfflineSP.identifier in SignatureProvider.get_types()
