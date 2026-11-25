#!/usr/bin/env python
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Unit tests for Lauterbach debug probe connect/close/reset handling."""

from unittest.mock import MagicMock, patch

import pytest
from spsdk.debuggers.debug_probe import SPSDKDebugProbeError

import lauterbach.trace32.rcl as t32
from spsdk_lauterbach.probe import DebugProbeLauterbach, T32Mode


def _mode_aware_connection() -> MagicMock:
    """Create a mocked T32 connection that reports the last requested SYStem.Mode."""
    connection = MagicMock()
    state = {"mode": "Down"}

    def cmd(command: str) -> None:
        if command.startswith("SYStem.Mode "):
            state["mode"] = command.split(" ", 1)[1]

    def fnc(function: str) -> object:
        if function == "SYStem.Mode()":
            return T32Mode.from_label(state["mode"]).tag
        raise t32.FunctionError("bus error at address EDBG:0x41000000")

    connection.cmd.side_effect = cmd
    connection.fnc.side_effect = fnc
    return connection


@pytest.fixture(name="probe")
def probe_fixture() -> DebugProbeLauterbach:
    """Lauterbach probe with a mocked, mode-aware T32 connection."""
    probe = DebugProbeLauterbach(hardware_id="C0000000000")
    probe.connection = _mode_aware_connection()
    return probe


def test_connect_does_not_read_dpidr(probe: DebugProbeLauterbach) -> None:
    """SPSDK-7207: connect succeeds although a raw DP register read reports a bus error."""
    probe.connect()
    assert probe.mode == T32Mode.PREPARE
    assert all("EDBG" not in str(call) for call in probe.connection.fnc.call_args_list)  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "error",
    [
        t32.ApiConnectionTimeoutError("timed out"),
        t32.ApiConnectionTransmitError("'NoneType' object has no attribute 'sendto'"),
        t32.CommandError("command failed"),
    ],
)
def test_close_never_raises(probe: DebugProbeLauterbach, error: Exception) -> None:
    """SPSDK-6945: close() swallows T32 errors raised while switching to mode Down."""
    probe.mode = T32Mode.PREPARE
    probe.connection.cmd.side_effect = error  # type: ignore[union-attr]
    with patch("spsdk_lauterbach.probe.time.sleep"):
        probe.close()
    assert probe.connection is None
    assert probe.mode == T32Mode.UNKNOWN
    # second close (e.g. from __del__) is a no-op
    probe.close()


def test_close_sets_mode_down(probe: DebugProbeLauterbach) -> None:
    """close() still switches Trace32 to mode Down when it responds."""
    connection = probe.connection
    probe.connect()
    probe.close()
    connection.cmd.assert_called_with("SYStem.Mode Down")  # type: ignore[union-attr]
    assert probe.connection is None


def test_reset_timeout_reconnects(probe: DebugProbeLauterbach) -> None:
    """SPSDK-6945: T32 API timeout during reset re-opens the connection instead of failing."""
    probe.connection.cmd.side_effect = t32.ApiConnectionTimeoutError("timed out")  # type: ignore[union-attr]
    new_connection = _mode_aware_connection()
    with patch("spsdk_lauterbach.probe.t32.connect", return_value=new_connection) as connect:
        probe.assert_reset_line(True)
    connect.assert_called_once()
    assert probe.connection is new_connection
    assert probe.mode == T32Mode.UNKNOWN


def test_reset_reconnect_failure(probe: DebugProbeLauterbach) -> None:
    """A failing reconnect after reset timeout is reported as SPSDKDebugProbeError."""
    probe.connection.cmd.side_effect = t32.ApiConnectionTimeoutError("timed out")  # type: ignore[union-attr]
    with patch("spsdk_lauterbach.probe.t32.connect", side_effect=ConnectionRefusedError()):
        with pytest.raises(SPSDKDebugProbeError):
            probe.assert_reset_line(True)


def test_reset_line_not_asserted(probe: DebugProbeLauterbach) -> None:
    """assert_reset_line(False) does not touch the target."""
    probe.assert_reset_line(False)
    probe.connection.cmd.assert_not_called()  # type: ignore[union-attr]
