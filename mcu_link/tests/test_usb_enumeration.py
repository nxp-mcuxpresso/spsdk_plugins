#!/usr/bin/env python
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Tests of USB probe enumeration robustness."""

from unittest.mock import MagicMock, patch

import pytest
import usb

from spsdk_mcu_link.dapper.interfaces import usb_v1_interface, usb_v2_interface




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
