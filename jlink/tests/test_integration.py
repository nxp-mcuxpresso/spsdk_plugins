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


def test_swd_connect_initializes_dp_before_reading_dpidr_and_selecting_ap():
    probe = object.__new__(DebugProbeJLink)
    probe.pylink = Mock()
    probe.options = {}
    connection_steps = []
    probe.pylink.coresight_configure.side_effect = lambda: connection_steps.append(
        "coresight_configure"
    )

    with (
        patch("spsdk_jlink.probe.get_debug_probe_protocol", return_value=DebugProbeProtocol.SWD),
        patch.object(
            probe, "select_ap", side_effect=lambda _: connection_steps.append("select_ap")
        ),
        patch.object(
            probe, "read_dp_idr", side_effect=lambda: connection_steps.append("read_dp_idr")
        ),
        patch.object(
            probe,
            "clear_sticky_errors",
            side_effect=lambda: connection_steps.append("clear_sticky_errors"),
        ),
        patch.object(
            probe, "power_up_target", side_effect=lambda: connection_steps.append("power_up_target")
        ),
    ):
        probe.connect()

    assert connection_steps == [
        "coresight_configure",
        "clear_sticky_errors",
        "power_up_target",
        "read_dp_idr",
        "select_ap",
    ]


def test_ap_register_access_uses_bank_local_register_index():
    probe = object.__new__(DebugProbeJLink)
    probe.pylink = Mock()
    probe.pylink.coresight_read.return_value = 0x84770001
    probe.last_accessed_ap = -1

    value = probe.coresight_reg_read(access_port=True, addr=0xFC)

    assert value == 0x84770001
    probe.pylink.coresight_write.assert_called_once_with(reg=2, data=0xF0, ap=False)
    probe.pylink.coresight_read.assert_called_once_with(reg=3, ap=True)


def test_reinit_invalidates_ap_cache_without_select_transaction():
    probe = object.__new__(DebugProbeJLink)
    probe.pylink = Mock()
    probe.last_accessed_ap = 0
    probe.disable_reinit = False

    with patch.object(probe, "_reinit_target") as reinit_target:
        probe._reinit_jlink_target()

    probe.pylink.coresight_configure.assert_called_once_with()
    probe.pylink.coresight_write.assert_not_called()
    assert probe.last_accessed_ap == -1
    reinit_target.assert_called_once_with()
