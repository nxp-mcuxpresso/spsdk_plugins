#!/usr/bin/env python
#
# Copyright 2024,2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Tests for `spsdk_pemicro` package integration in SPSDK."""

from unittest.mock import Mock, patch

from click.testing import CliRunner
from spsdk.apps import nxpdebugmbox
from spsdk.debuggers.debug_probe import SPSDKDebugProbeError
from spsdk_pemicro.probe import DebugProbePemicro


def test_connect_uses_default_protocol():
    probe = DebugProbePemicro("", {})
    pemicro = Mock()
    probe.pemicro = pemicro

    with (
        patch.object(probe, "read_dp_idr") as read_dp_idr,
        patch.object(probe, "clear_sticky_errors"),
        patch.object(probe, "power_up_target"),
    ):
        probe.connect()

    pemicro.connect.assert_called_once()
    assert pemicro.connect.call_args.args[0].name == "SWD"
    assert pemicro.connect.call_args.kwargs["shift_speed"] == 100000
    read_dp_idr.assert_called_once()


def test_connect_rejects_selected_jtag_protocol():
    probe = DebugProbePemicro("", {"protocol": "jtag", "frequency": 500000})
    pemicro = Mock()
    probe.pemicro = pemicro

    try:
        probe.connect()
    except SPSDKDebugProbeError as exc:
        assert "does not support JTAG protocol" in str(exc)
    else:
        raise AssertionError("Temporarily disabled JTAG protocol should fail")

    pemicro.connect.assert_not_called()


def test_advertised_protocols_exclude_temporarily_disabled_jtag():
    assert [protocol.label for protocol in DebugProbePemicro.SUPPORTED_PROTOCOLS] == ["swd"]


def test_connect_rejects_unsupported_protocol():
    probe = DebugProbePemicro("", {"protocol": "once"})
    probe.pemicro = Mock()

    try:
        probe.connect()
    except SPSDKDebugProbeError as exc:
        assert "does not support ONCE protocol" in str(exc)
    else:
        raise AssertionError("Unsupported protocol should fail")


def test_connect_safe_rejects_temporarily_disabled_jtag_without_recovery():
    probe = DebugProbePemicro("", {"protocol": "jtag"})

    with (
        patch.object(probe, "connect", side_effect=SPSDKDebugProbeError("attach failed")),
        patch.object(probe, "recover_debug_connection") as recover_debug_connection,
    ):
        try:
            probe.connect_safe()
        except SPSDKDebugProbeError as exc:
            assert "does not support JTAG protocol" in str(exc)
        else:
            raise AssertionError("Temporarily disabled JTAG protocol should fail")

    recover_debug_connection.assert_not_called()


def test_assert_reset_line_reports_unsupported():
    probe = DebugProbePemicro("", {})
    probe.pemicro = Mock()

    try:
        probe.assert_reset_line(True)
    except SPSDKDebugProbeError as exc:
        assert "hardware reset line control is not supported" in str(exc)
    else:
        raise AssertionError("PEMicro HW reset line should not report success")

    probe.pemicro.control_reset_line.assert_not_called()


def test_integration():
    runner = CliRunner()
    result = runner.invoke(nxpdebugmbox.main, "--help")
    assert "pemicro" in result.output
