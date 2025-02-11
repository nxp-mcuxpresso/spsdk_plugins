#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Main module for J-Link Debug probe."""

import logging
from typing import Dict, Optional

from pylink import JLink, JLinkException, JLinkInterfaces
from spsdk.debuggers.debug_probe import (
    DebugProbeCoreSightOnly,
    DebugProbes,
    ProbeDescription,
    SPSDKDebugProbeError,
    SPSDKDebugProbeNotOpenError,
    SPSDKDebugProbeTransferError,
)
from spsdk.utils.misc import value_to_int

logger = logging.getLogger(__name__)
logger_pylink = logger.getChild("PyLink")
logger_pylink.setLevel(logging.CRITICAL)


class DebugProbeJLink(DebugProbeCoreSightOnly):
    """SPSDK Debug Probe J-Link Debug probe class."""

    NAME = "jlink"

    @classmethod
    def get_options_help(cls) -> Dict[str, str]:
        """Get full list of options of debug probe.

        :return: Dictionary with individual options. Key is parameter name and value the help text.
        """
        options_help = super().get_options_help()
        options_help["frequency"] = "Set the communication frequency in KHz, default is 100KHz"
        return options_help

    @classmethod
    def get_jlink_lib(cls) -> JLink:
        """Get J-Link object.

        :return: The J-Link Object
        :raises SPSDKDebugProbeError: The J-Link object get function failed.
        """
        try:
            return JLink(
                log=logger_pylink.info,
                detailed_log=logger_pylink.debug,
                error=logger_pylink.error,
                warn=logger_pylink.warn,
            )
        except TypeError as exc:
            raise SPSDKDebugProbeError("Cannot open Jlink DLL") from exc

    def __init__(self, hardware_id: str, options: Optional[Dict] = None) -> None:
        """The PyLink class initialization.

        The PyLink initialization function for SPSDK library to support various DEBUG PROBES.
        """
        super().__init__(hardware_id, options)
        self.pylink = None

        logger.debug("The SPSDK PyLink Interface has been initialized")

    @classmethod
    def get_connected_probes(
        cls, hardware_id: Optional[str] = None, options: Optional[Dict] = None
    ) -> DebugProbes:
        """Get all connected probes over PyLink.

        This functions returns the list of all connected probes in system by PyLink package.

        :param hardware_id: None to list all probes, otherwise the the only probe with matching
            hardware id is listed.
        :param options: The options dictionary
        :return: probe_description
        """
        jlink = cls.get_jlink_lib()

        probes = DebugProbes()
        connected_probes = jlink.connected_emulators()
        for probe in connected_probes:
            if not hardware_id or hardware_id == str(probe.SerialNumber):
                probes.append(
                    ProbeDescription(
                        "Jlink",
                        str(probe.SerialNumber),
                        f"Segger {probe.acProduct.decode('utf-8')}",
                        cls,
                    )
                )

        return probes

    def open(self) -> None:
        """Open PyLink interface for NXP SPSDK.

        The PyLink opening function for SPSDK library to support various DEBUG PROBES.
        The function is used to initialize the connection to target and enable using debug probe
        for DAT purposes.

        :raises SPSDKDebugProbeError: Opening of the debug probe failed
        """
        try:
            self.pylink = self.get_jlink_lib()
            if self.pylink is None:
                raise SPSDKDebugProbeError("Getting of J-Link library failed")
        except SPSDKDebugProbeError as exc:
            raise SPSDKDebugProbeError(f"Getting of J-Link library failed({str(exc)})") from exc

        try:
            self.pylink.open(
                serial_no=self.hardware_id,
                ip_addr=self.options.get("ip_address") if self.options else None,
            )
        except JLinkException as exc:
            raise SPSDKDebugProbeError(f"Opening the debug probe failed ({str(exc)})") from exc

    def connect(self) -> None:
        """Connect to target.

        The PyLink connecting function for SPSDK library to support various DEBUG PROBES.
        The function is used to initialize the connection to target

        :raises SPSDKDebugProbeError: The PyLink cannot establish communication with target
        """
        if self.pylink is None:
            raise SPSDKDebugProbeError("Debug probe must be opened first")
        try:
            if self.options.get("use_jtag") is None:
                self.pylink.set_tif(JLinkInterfaces.SWD)
            else:
                logger.warning(
                    "Experimental support for JTAG on RW61x."
                    "The implementation may have bugs and lack features."
                )
                self.pylink.set_speed(100)
                self.pylink.set_tif(JLinkInterfaces.JTAG)
            self.pylink.coresight_configure()
            self.pylink.set_speed(speed=value_to_int(self.options.get("frequency", 100)))
            # Power Up the system and debug and clear sticky errors
            self.clear_sticky_errors()
            self.power_up_target()

        except JLinkException as exc:
            raise SPSDKDebugProbeError(
                f"PyLink cannot establish communication with target({str(exc)})"
            ) from exc

    def close(self) -> None:
        """Close PyLink interface.

        The PyLink closing function for SPSDK library to support various DEBUG PROBES.
        """
        if self.pylink:
            self.pylink.close()

    def coresight_reg_read(self, access_port: bool = True, addr: int = 0) -> int:
        """Read coresight register over PyLink interface.

        The PyLink read coresight register function for SPSDK library to support various DEBUG PROBES.

        :param access_port: if True, the Access Port (AP) register will be read(default), otherwise the Debug Port
        :param addr: the register address
        :return: The read value of addressed register (4 bytes)
        :raises SPSDKDebugProbeTransferError: The IO operation failed
        :raises SPSDKDebugProbeNotOpenError: The PyLink probe is NOT opened

        """
        if self.pylink is None:
            raise SPSDKDebugProbeNotOpenError("The PyLink debug probe is not opened yet")

        try:
            if access_port:
                self.select_ap(addr)
                addr = addr & 0x0F

            return self.pylink.coresight_read(reg=addr // 4, ap=access_port)
        except (JLinkException, ValueError, TypeError) as exc:
            # In case of transaction error reconfigure and initialize the JLink
            self._reinit_jlink_target()
            raise SPSDKDebugProbeTransferError(
                f"The Coresight read operation failed({str(exc)})"
            ) from exc

    def coresight_reg_write(self, access_port: bool = True, addr: int = 0, data: int = 0) -> None:
        """Write coresight register over PyLink interface.

        The PyLink write coresight register function for SPSDK library to support various DEBUG PROBES.

        :param access_port: if True, the Access Port (AP) register will be write(default), otherwise the Debug Port
        :param addr: the register address
        :param data: the data to be written into register
        :raises SPSDKDebugProbeTransferError: The IO operation failed
        :raises SPSDKDebugProbeNotOpenError: The PyLink probe is NOT opened
        """
        if self.pylink is None:
            raise SPSDKDebugProbeNotOpenError("The PyLink debug probe is not opened yet")

        try:
            if access_port:
                self.select_ap(addr)
                addr = addr & 0x0F

            self.pylink.coresight_write(reg=addr // 4, data=data, ap=access_port)

        except (JLinkException, ValueError, TypeError) as exc:
            # In case of transaction error reconfigure and initialize the JLink
            self._reinit_jlink_target()
            raise SPSDKDebugProbeTransferError(
                f"The Coresight write operation failed({str(exc)})"
            ) from exc

    def assert_reset_line(self, assert_reset: bool = False) -> None:
        """Control reset line at a target.

        :param assert_reset: If True, the reset line is asserted(pulled down), if False the reset line is not affected.
        :raises SPSDKDebugProbeNotOpenError: The PyLink probe is NOT opened
        :raises SPSDKDebugProbeError: The PyLink probe RESET function failed
        """
        if self.pylink is None:
            raise SPSDKDebugProbeNotOpenError("The PyLink debug probe is not opened yet")

        try:
            if assert_reset:
                self.pylink.set_reset_pin_low()
            else:
                self.pylink.set_reset_pin_high()
        except JLinkException as exc:
            raise SPSDKDebugProbeError(f"Jlink reset operation failed: {str(exc)}") from exc

    def _reinit_jlink_target(self) -> None:
        """Re-initialize the Jlink connection."""
        if self.pylink is None:
            raise SPSDKDebugProbeNotOpenError("The PyLink debug probe is not opened yet")

        if not self.disable_reinit:
            self.pylink.coresight_configure()
            self._reinit_target()
