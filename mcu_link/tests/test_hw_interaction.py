#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for basic HW interaction."""

import pytest
from spsdk_mcu_link.probe import DebugProbeMCULink

HW_CONNECTED = False


@pytest.mark.skipif(not HW_CONNECTED, reason="No HW connected")
def test_re_open():
    connected_probes = DebugProbeMCULink.get_connected_probes()
    assert len(connected_probes) > 0

    probe = connected_probes[0].get_probe()
    assert probe

    probe.open()
    probe.connect()
    probe.close()

    probe.open()
    probe.connect()
    probe.close()
