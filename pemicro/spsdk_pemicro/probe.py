#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Main module for P&E Micro debugger probe plugin."""

import logging
from typing import Dict, Optional

from pypemicro import PEMicroException, PEMicroInterfaces, PyPemicro
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
logger_pypemicro = logger.getChild("PyPemicro")


class DebugProbePemicro(DebugProbeCoreSightOnly):
    """Class to define Pemicro package interface for NXP SPSDK."""

    NAME = "pemicro"

    @classmethod
    def get_options_help(cls) -> Dict[str, str]:
        """Get full list of options of debug probe.

        :return: Dictionary with individual options. Key is parameter name and value the help text.
        """
        options_help = super().get_options_help()
        options_help["frequency"] = "Set the communication frequency in Hz, default is 100_000Hz"
        return options_help

    @classmethod
    def get_pemicro_lib(cls) -> PyPemicro:
        """Get Pemicro object.

        :return: The Pemicro Object
        :raises SPSDKDebugProbeError: The Pemicro object get function failed.
        """
        try:
            return PyPemicro(
                log_info=logger_pypemicro.info,
                log_debug=logger_pypemicro.debug,
                log_err=logger_pypemicro.error,
                log_war=logger_pypemicro.warn,
            )
        except PEMicroException as exc:
            raise SPSDKDebugProbeError(f"Cannot get Pemicro library: ({str(exc)})") from exc

    def __init__(self, hardware_id: str, options: Optional[Dict] = None) -> None:
        """The Pemicro class initialization.

        The Pemicro initialization function for SPSDK library to support various DEBUG PROBES.
        """
        super().__init__(hardware_id, options)

        self.pemicro: Optional[PyPemicro] = None

        logger.debug("The SPSDK Pemicro Interface has been initialized")

    # pylint: disable=unused-argument # we need to satisfy the method signature
    @classmethod
    def get_connected_probes(
        cls, hardware_id: Optional[str] = None, options: Optional[Dict] = None
    ) -> DebugProbes:
        """Get all connected probes over Pemicro.

        This functions returns the list of all connected probes in system by Pemicro package.

        :param hardware_id: None to list all probes, otherwise the the only probe with matching
            hardware id is listed.
        :param options: The options dictionary
        :return: probe_description
        """
        probes = DebugProbes()
        try:
            connected_probes = PyPemicro.list_ports()
            for probe in connected_probes:
                if not hardware_id or hardware_id == str(probe["id"]):
                    probes.append(
                        ProbeDescription(
                            "PEMicro", probe["id"], probe["description"], DebugProbePemicro
                        )
                    )
        except PEMicroException as exc:
            logger.warning(f"Cannot get list of PEMicro probes: {str(exc)}")
        return probes

    def open(self) -> None:
        """Open Pemicro interface for NXP SPSDK.

        The Pemicro opening function for SPSDK library to support various DEBUG PROBES.
        The function is used to initialize the connection to target and enable using debug probe
        for DAT purposes.

        :raises SPSDKDebugProbeError: Opening of the debug probe failed
        """
        try:
            self.pemicro = DebugProbePemicro.get_pemicro_lib()
            if self.pemicro is None:
                raise SPSDKDebugProbeError("Getting of Pemicro library failed.")
        except SPSDKDebugProbeError as exc:
            raise SPSDKDebugProbeError(f"Getting of Pemicro library failed({str(exc)}).") from exc
        try:
            self.pemicro.open(debug_hardware_name_ip_or_serialnum=self.hardware_id)
        except PEMicroException as exc:
            raise SPSDKDebugProbeError(f"Opening the debug probe failed ({str(exc)})") from exc

    def connect(self) -> None:
        """Connect to target.

        The Pemicro connecting function for SPSDK library to support various DEBUG PROBES.
        The function is used to initialize the connection to target

        :raises SPSDKDebugProbeError: The Pemicro cannot establish communication with target
        """
        if self.pemicro is None:
            raise SPSDKDebugProbeError("Debug probe must be opened first")
        try:
            self.pemicro.connect(PEMicroInterfaces.SWD)
            self.pemicro.set_debug_frequency(value_to_int(self.options.get("frequency", 100000)))
            self.clear_sticky_errors()
            self.power_up_target()

        except PEMicroException as exc:
            raise SPSDKDebugProbeError(
                f"Pemicro cannot establish communication with target({str(exc)})."
            ) from exc

    def close(self) -> None:
        """Close Pemicro interface.

        The Pemicro closing function for SPSDK library to support various DEBUG PROBES.
        """
        if self.pemicro:
            self.pemicro.close()

    def coresight_reg_read(self, access_port: bool = True, addr: int = 0) -> int:
        """Read coresight register over Pemicro interface.

        The Pemicro read coresight register function for SPSDK library to support various DEBUG PROBES.

        :param access_port: if True, the Access Port (AP) register will be read(default), otherwise the Debug Port
        :param addr: the register address
        :return: The read value of addressed register (4 bytes)
        :raises SPSDKDebugProbeTransferError: The IO operation failed
        :raises SPSDKDebugProbeNotOpenError: The Pemicro probe is NOT opened
        """
        if self.pemicro is None:
            raise SPSDKDebugProbeNotOpenError("The Pemicro debug probe is not opened yet")

        try:
            if access_port:
                ap_ix = (addr & self.APSEL_APBANKSEL) >> self.APSEL_SHIFT
                ret = self.pemicro.read_ap_register(apselect=ap_ix, addr=addr)
            else:
                ret = self.pemicro.read_dp_register(addr=addr)
            return ret
        except PEMicroException as exc:
            self._reinit_target()
            raise SPSDKDebugProbeTransferError(
                f"The Coresight read operation failed({str(exc)})."
            ) from exc

    def coresight_reg_write(self, access_port: bool = True, addr: int = 0, data: int = 0) -> None:
        """Write coresight register over Pemicro interface.

        The Pemicro write coresight register function for SPSDK library to support various DEBUG PROBES.

        :param access_port: if True, the Access Port (AP) register will be write(default), otherwise the Debug Port
        :param addr: the register address
        :param data: the data to be written into register
        :raises SPSDKDebugProbeTransferError: The IO operation failed
        :raises SPSDKDebugProbeNotOpenError: The Pemicro probe is NOT opened
        """
        if self.pemicro is None:
            raise SPSDKDebugProbeNotOpenError("The Pemicro debug probe is not opened yet")

        try:
            if access_port:
                ap_ix = (addr & self.APSEL_APBANKSEL) >> self.APSEL_SHIFT
                self.pemicro.write_ap_register(apselect=ap_ix, addr=addr, value=data)
            else:
                self.pemicro.write_dp_register(addr=addr, value=data)

        except PEMicroException as exc:
            self._reinit_target()
            raise SPSDKDebugProbeTransferError(
                f"The Coresight write operation failed({str(exc)})."
            ) from exc

    def assert_reset_line(self, assert_reset: bool = False) -> None:
        """Control reset line at a target.

        :param assert_reset: If True, the reset line is asserted(pulled down), if False the reset line is not affected.
        :raises SPSDKDebugProbeNotOpenError: The Pemicro debug probe is not opened yet
        :raises SPSDKDebugProbeError: The PyPEMicro probe RESET function failed
        """
        if self.pemicro is None:
            raise SPSDKDebugProbeNotOpenError("The Pemicro debug probe is not opened yet")

        try:
            if assert_reset:
                self.pemicro.control_reset_line(True)
            else:
                self.pemicro.control_reset_line(False)
        except PEMicroException as exc:
            raise SPSDKDebugProbeError(f"Pemicro reset operation failed: {str(exc)}") from exc
