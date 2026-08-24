#!/usr/bin/env python
#
# Copyright 2024-2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Tests for `spsdk_mcu_link` package integration in SPSDK."""

import inspect
from unittest.mock import patch

from click.testing import CliRunner
from spsdk.apps import nxpdebugmbox
from spsdk.debuggers.debug_probe import SPSDKDebugProbeError

from spsdk_mcu_link.dapper.webix_dapper_wasm import WebixDapperWasm
from spsdk_mcu_link.probe import DebugProbeMCULink


def test_integration():
    runner = CliRunner()
    result = runner.invoke(nxpdebugmbox.main, "--help")
    if "mcu-link" not in result.output:
        raise AssertionError("mcu-link not found in --help")


class MockDapperProbe:
    """Mock WebixDapper probe."""

    def __init__(self) -> None:
        """Initialize mock probe."""
        self.use_jtag = False
        self.connected = False

    def connect(self) -> None:
        """Mock target connection."""
        self.connected = True

    def initialize_debug_port(self) -> None:
        """Mock debug port initialization."""

    def close(self) -> None:
        """Mock probe close."""


class MockJtagStatusFailDapperProbe(MockDapperProbe):
    """Mock WebixDapper probe with failing JTAG connect and working DP access."""

    def __init__(self) -> None:
        """Initialize mock probe."""
        super().__init__()
        self.initialized = False

    def connect(self) -> None:
        """Mock target connection failure."""
        raise RuntimeError("Status fail")

    def initialize_debug_port(self) -> None:
        """Mock working debug port initialization after JTAG connect failure."""
        self.initialized = True


def test_connect_uses_default_protocol():
    probe = DebugProbeMCULink("", {})
    probe.probe = MockDapperProbe()

    with patch.object(probe, "read_dp_idr") as read_dp_idr:
        probe.connect()

    assert probe.probe.connected
    assert probe.probe.use_jtag is False
    read_dp_idr.assert_called_once()


def test_connect_uses_selected_jtag_protocol():
    probe = DebugProbeMCULink("", {"protocol": "jtag"})
    probe.probe = MockDapperProbe()

    with patch.object(probe, "read_dp_idr"):
        probe.connect()

    assert probe.probe.connected
    assert probe.probe.use_jtag is True


def test_connect_accepts_jtag_status_fail_when_dp_is_accessible():
    probe = DebugProbeMCULink("", {"protocol": "jtag"})
    probe.probe = MockJtagStatusFailDapperProbe()

    probe.connect()

    assert probe.probe.use_jtag is True
    assert probe.probe.initialized is True


def test_wasm_connect_accepts_protocol_argument():
    dapper_wasm = WebixDapperWasm()
    dapper_wasm.runtime_init()

    assert inspect.signature(dapper_wasm.connect) == inspect.Signature(
        [
            inspect.Parameter(
                "args",
                inspect.Parameter.VAR_POSITIONAL,
            )
        ]
    )


def test_connect_rejects_unsupported_protocol():
    probe = DebugProbeMCULink("", {"protocol": "once"})
    probe.probe = MockDapperProbe()

    try:
        probe.connect()
    except SPSDKDebugProbeError as exc:
        assert "does not support ONCE protocol" in str(exc)
    else:
        raise AssertionError("Unsupported protocol should fail")


def test_close_is_safe_on_partially_initialized_probe():
    probe = object.__new__(DebugProbeMCULink)

    probe.close()
