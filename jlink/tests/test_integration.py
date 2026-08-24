#!/usr/bin/env python
#
# Copyright 2024,2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Tests for `spsdk_jlink` package integration in SPSDK."""

from unittest.mock import Mock, patch

from click.testing import CliRunner
from spsdk.apps import nxpdebugmbox
from spsdk_jlink.probe import DebugProbeJLink
from spsdk_jlink.protocols import DebugProbeProtocol


def test_integration():
    runner = CliRunner()
    result = runner.invoke(nxpdebugmbox.main, "--help")
    assert "jlink" in result.output


def test_close_is_safe_on_partially_initialized_probe():
    probe = object.__new__(DebugProbeJLink)

    probe.close()


def test_swd_connect_sets_initial_speed_before_interface():
    probe = object.__new__(DebugProbeJLink)
    probe.pylink = Mock()
    probe.options = {"frequency": "1000"}
    probe.last_accessed_ap = -1

    with (
        patch("spsdk_jlink.probe.get_debug_probe_protocol", return_value=DebugProbeProtocol.SWD),
        patch.object(probe, "select_ap"),
        patch.object(probe, "read_dp_idr"),
        patch.object(probe, "clear_sticky_errors"),
        patch.object(probe, "power_up_target"),
    ):
        probe.connect()

    call_names = [call[0] for call in probe.pylink.method_calls]
    assert call_names[:3] == ["set_speed", "set_tif", "coresight_configure"]
    probe.pylink.set_speed.assert_any_call(100)
    probe.pylink.set_speed.assert_any_call(speed=1000)


def test_swd_connect_reads_dpidr_after_coresight_configuration():
    probe = object.__new__(DebugProbeJLink)
    probe.pylink = Mock()
    probe.pylink.coresight_read.return_value = 0x2BA01477
    probe.options = {}
    probe.last_accessed_ap = -1
    probe.disable_reinit = False

    with (
        patch("spsdk_jlink.probe.get_debug_probe_protocol", return_value=DebugProbeProtocol.SWD),
        patch.object(probe, "select_ap"),
        patch.object(probe, "clear_sticky_errors"),
        patch.object(probe, "power_up_target"),
    ):
        probe.connect()

    assert probe.pylink.method_calls[2] == ("coresight_configure", (), {})
    assert probe.pylink.method_calls[3] == ("coresight_read", (), {"reg": 0, "ap": False})


def test_ap_register_access_uses_bank_local_register_index():
    probe = object.__new__(DebugProbeJLink)
    probe.pylink = Mock()
    probe.pylink.coresight_read.return_value = 0x84770001
    probe.last_accessed_ap = -1

    value = probe.coresight_reg_read(access_port=True, addr=0xFC)

    assert value == 0x84770001
    probe.pylink.coresight_write.assert_called_once_with(reg=2, data=0xF0, ap=False)
    probe.pylink.coresight_read.assert_called_once_with(reg=3, ap=True)
