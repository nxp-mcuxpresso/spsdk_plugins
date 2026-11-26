#!/usr/bin/env python
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Tests of USB probe enumeration robustness."""

import gc
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import usb

from spsdk.apps.nxpdebugmbox import DebugProbeParams
from spsdk.apps.nxpdebugmbox import test_connection as check_connection
from spsdk.apps.utils.utils import SPSDKAppError
from spsdk.debuggers.utils import PROBES
from spsdk.utils.family import FamilyRevision
from spsdk_mcu_link.dapper import DapperFactory, WebixDapper
from spsdk_mcu_link.dapper.interfaces import usb_v1_interface, usb_v2_interface
from spsdk_mcu_link.probe import DebugProbeMCULink


@pytest.mark.parametrize(
    "module, interface",
    [
        (usb_v1_interface, usb_v1_interface.UsbV1Interface),
        (usb_v2_interface, usb_v2_interface.UsbV2Interface),
    ],
)
@pytest.mark.parametrize("error", [ValueError("The device has no langid"), usb.core.USBError("io")])
def test_list_probes_skips_unreadable_device(module, interface, error: Exception) -> None:
    """Device with unreadable descriptors is skipped, enumeration does not fail."""
    device = MagicMock()
    device.bDeviceClass = 0x00
    device.get_active_configuration.side_effect = error
    with (
        patch.object(module, "get_usb_backend", return_value=MagicMock()),
        patch.object(module.usb.core, "find", return_value=[device]),
    ):
        assert interface.list_probes() == []
    device._finalize_object.assert_called()  # pylint: disable=protected-access


def test_failed_connection_releases_usb_after_reopen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated failed target connections release each reopened USB handle."""
    backend = MagicMock()
    backend.open_device.side_effect = lambda _: object()
    # Garbage collection inside close_device finalizes discarded probes;
    # it must not close the same handle once more.
    backend.close_device.side_effect = lambda _: gc.collect()
    device = usb.core.Device.__new__(usb.core.Device)
    device._ctx = usb.core._ResourceManager(object(), backend)
    device._serial_number = "virtual-mcu-link"
    device._manufacturer = "NXP"
    device._product = "MCU-Link"
    device.idVendor = 0x1FC9
    device.idProduct = 0x0143
    endpoints = [
        SimpleNamespace(bEndpointAddress=0x81),
        SimpleNamespace(bEndpointAddress=0x01),
    ]

    def get_configuration() -> dict:
        device._ctx.managed_open()
        return {(0, 0): endpoints}

    monkeypatch.setattr(device, "get_active_configuration", get_configuration)
    interface = usb_v2_interface.UsbV2Interface(device)
    dapper = WebixDapper()
    dapper._module = MagicMock()
    dapper._module.getProbeDAPInfo.return_value = {}
    dapper._module.connect.side_effect = RuntimeError("Target not connected")
    monkeypatch.setattr(DapperFactory.instance(), "_dapper", dapper)
    monkeypatch.setattr(DapperFactory, "probes", [interface])
    monkeypatch.setattr(DapperFactory, "list_probes", lambda: [interface])
    monkeypatch.setitem(PROBES, "mcu-link", DebugProbeMCULink)
    probe_base = DebugProbeMCULink.__base__
    monkeypatch.setattr(probe_base, "_level1_soft_recovery", lambda self: False)
    monkeypatch.setattr(probe_base, "_level2_power_cycle_recovery", lambda self: False)
    monkeypatch.setattr("spsdk_mcu_link.dapper.webix_dapper.sleep", lambda _: None)
    monkeypatch.setattr(sys.modules[probe_base.__module__], "sleep", lambda _: None)
    params = DebugProbeParams(
        interface="mcu-link", serial_no=interface.serial_no, debug_probe_user_params={}
    )

    for _ in range(2):
        try:
            result = check_connection(FamilyRevision("lpc55s69"), params, "debug_port")
        except SPSDKAppError as exc:
            assert "Testing AHB access failed" in str(exc)
        else:
            assert result is False
        assert backend.open_device.call_count > 1
        assert backend.close_device.call_count == backend.open_device.call_count

    dapper._module.connect.side_effect = None
    dapper._module.coreSightRead.return_value = 0xA0000001
    assert check_connection(FamilyRevision("lpc55s69"), params, "debug_port")
    assert backend.close_device.call_count == backend.open_device.call_count
