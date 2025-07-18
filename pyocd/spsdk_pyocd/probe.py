#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Main module for PyOCD SW Debugger."""

import logging
from time import sleep
from typing import Dict, List, Optional

from spsdk.debuggers.debug_probe import (
    DebugProbeCoreSightOnly,
    DebugProbes,
    ProbeDescription,
    SPSDKDebugProbeError,
    SPSDKDebugProbeNotOpenError,
    SPSDKDebugProbeTransferError,
)
from spsdk.exceptions import SPSDKError

import pyocd
from pyocd.core.exceptions import Error as PyOCDError
from pyocd.core.exceptions import ProbeError
from pyocd.core.helpers import ConnectHelper
from pyocd.core.session import Session
from pyocd.coresight.dap import DPConnector
from pyocd.probe.debug_probe import DebugProbe as PyOCDDebugProbe

TRACE_ENABLE = True
logger = logging.getLogger(__name__)


class DebugProbePyOCD(DebugProbeCoreSightOnly):
    """Class to define PyOCD package interface for NXP SPSDK."""

    NAME = "pyocd"

    def __init__(self, hardware_id: str, options: Optional[Dict] = None) -> None:
        """The PyOCD class initialization.

        The PyOCD initialization function for SPSDK library to support various DEBUG PROBES.
        """
        super().__init__(hardware_id, options)
        self.probe: PyOCDDebugProbe = None

        logger.debug("The SPSDK PyOCD Interface has been initialized")

    @classmethod
    def get_connected_probes(
        cls, hardware_id: Optional[str] = None, options: Optional[Dict] = None
    ) -> DebugProbes:
        """Get all connected probes over PyOCD.

        This functions returns the list of all connected probes in system by PyOCD package.

        :param hardware_id: None to list all probes, otherwise the the only probe with matching
            hardware id is listed.
        :param options: The options dictionary
        :return: probe_description
        """
        probes = DebugProbes()
        try:
            connected_probes: List[PyOCDDebugProbe] = ConnectHelper.get_all_connected_probes(
                blocking=False, unique_id=hardware_id
            )
        except ProbeError as exc:
            logger.debug(f"Probing connected probes over PyOCD failed: {str(exc)}")
            connected_probes = []

        for probe in connected_probes:
            probes.append(
                ProbeDescription("PyOCD", probe.unique_id, probe.description, DebugProbePyOCD)
            )

        return probes

    def open(self) -> None:
        """Open PyOCD interface for NXP SPSDK.

        The PyOCD opening function for SPSDK library to support various DEBUG PROBES.

        :raises SPSDKProbeNotFoundError: The probe has not found
        :raises SPSDKDebugMailBoxAPNotFoundError: The debug mailbox access port NOT found
        :raises SPSDKDebugProbeError: Opening of the debug probe failed
        """
        try:
            self.probe = ConnectHelper.choose_probe(
                blocking=False,
                return_first=True,
                unique_id=self.hardware_id,
            )

            self.probe.session = Session(self.probe, options={"target_override": "cortex_m"})
            self.probe.open()
        except PyOCDError as exc:
            raise SPSDKDebugProbeError(f"Opening the debug probe failed ({str(exc)})") from exc

    def connect(self) -> None:
        """Connect to target.

        The PyOCD connecting function for SPSDK library to support various DEBUG PROBES.
        The function is used to initialize the connection to target

        :raises SPSDKDebugProbeError: The PyOCD cannot establish communication with target
        """
        if self.probe is None:
            raise SPSDKDebugProbeError("Debug probe must be opened first")
        try:
            if self.options.get("use_jtag") is None:
                self.probe.connect(pyocd.probe.debug_probe.DebugProbe.Protocol.SWD)
            else:
                logger.warning(
                    "Experimental support for JTAG on RW61x."
                    "The implementation may have bugs and lack features."
                )
                self.probe.connect(pyocd.probe.debug_probe.DebugProbe.Protocol.JTAG)
            # Do reset sequence to switch to used protocol
            connector = DPConnector(self.probe)
            connector.connect()
            logger.debug(connector._idr)  # pylint: disable=protected-access
            # Power Up the system and debug and clear sticky errors
            self.clear_sticky_errors()
            self.power_up_target()
            logger.info(f"PyOCD connected via {self.probe.product_name} probe.")
        except (PyOCDError, SPSDKError) as exc:
            raise SPSDKDebugProbeError("PyOCD cannot establish communication with target.") from exc

    def close(self) -> None:
        """Close PyLink interface.

        The PyLink closing function for SPSDK library to support various DEBUG PROBES.
        """
        if self.probe:
            if self.probe.is_open:
                self.probe.close()
            self.probe = None

    def assert_reset_line(self, assert_reset: bool = False) -> None:
        """Control reset line at a target.

        :param assert_reset: If True, the reset line is asserted(pulled down), if False the reset line is not affected.
        :raises SPSDKDebugProbeNotOpenError: The PyOCD debug probe is not opened yet
        :raises SPSDKDebugProbeError: The PyOCD probe RESET function failed
        """
        if self.probe is None:
            raise SPSDKDebugProbeNotOpenError("The PyOCD debug probe is not opened yet")

        try:
            self.probe.assert_reset(assert_reset)
        except PyOCDError as exc:
            raise SPSDKDebugProbeError(f"PyOCD reset operation failed: {str(exc)}") from exc

    def reset(self) -> None:
        """Reset a target.

        It resets a target.

        :raises SPSDKDebugProbeError: Internal error on debug probe, detected during reset request.
        """
        self.assert_reset_line(True)
        if not self.probe.is_reset_asserted():
            raise SPSDKDebugProbeError(
                "The reset signal is NOT asserted during reset sequence. "
                "Check a debug probe if it is using latest firmware."
            )
        sleep(self.RESET_TIME)
        self.assert_reset_line(False)
        sleep(self.AFTER_RESET_TIME)

    def coresight_reg_read(self, access_port: bool = True, addr: int = 0) -> int:
        """Read coresight register over PyOCD interface.

        The PyOCD read coresight register function for SPSDK library to support various DEBUG PROBES.

        :param access_port: if True, the Access Port (AP) register will be read(default), otherwise the Debug Port
        :param addr: the register address
        :return: The read value of addressed register (4 bytes)
        :raises SPSDKDebugProbeTransferError: The IO operation failed
        :raises SPSDKDebugProbeNotOpenError: The PyOCD probe is NOT opened
        """
        if self.probe is None:
            raise SPSDKDebugProbeNotOpenError("The PyOCD debug probe is not opened yet")
        try:
            if access_port:
                if PyOCDDebugProbe.Capability.MANAGED_AP_SELECTION not in self.probe.capabilities:
                    self.select_ap(addr)
                    addr = addr & 0x0F
                ret = self.probe.read_ap(addr=addr)
            else:
                ret = self.probe.read_dp(addr)
            if TRACE_ENABLE:
                logger.debug(
                    f"Coresight read {'AP' if access_port else 'DP'}, address: {addr:08X}, data: {ret:08X}"
                )
            return ret
        except (PyOCDError, Exception) as exc:
            self._reinit_target()
            raise SPSDKDebugProbeTransferError("The Coresight read operation failed") from exc

    def coresight_reg_write(self, access_port: bool = True, addr: int = 0, data: int = 0) -> None:
        """Write coresight register over PyOCD interface.

        The PyOCD write coresight register function for SPSDK library to support various DEBUG PROBES.

        :param access_port: if True, the Access Port (AP) register will be write(default), otherwise the Debug Port
        :param addr: the register address
        :param data: the data to be written into register
        :raises SPSDKDebugProbeTransferError: The IO operation failed
        :raises SPSDKDebugProbeNotOpenError: The PyOCD probe is NOT opened
        """
        if self.probe is None:
            raise SPSDKDebugProbeNotOpenError("The PyOCD debug probe is not opened yet")
        try:
            if access_port:
                if PyOCDDebugProbe.Capability.MANAGED_AP_SELECTION not in self.probe.capabilities:
                    self.select_ap(addr)
                    addr = addr & 0x0F
                self.probe.write_ap(addr=addr, data=data)
            else:
                self.probe.write_dp(addr, data)
            if TRACE_ENABLE:
                logger.debug(
                    f"Coresight write {'AP' if access_port else 'DP'}, address: {addr:08X}, data: {data:08X}"
                )
        except (PyOCDError, Exception) as exc:
            self._reinit_target()
            raise SPSDKDebugProbeTransferError("The Coresight write operation failed") from exc
