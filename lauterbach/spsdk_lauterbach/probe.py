#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Main module for Lauterbach debug probe plugin."""

# cspell: ignore NETTCP, EDBG

import functools
import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple

from spsdk.debuggers.debug_probe import (
    DebugProbeCoreSightOnly,
    DebugProbes,
    ProbeDescription,
    SPSDKDebugProbeError,
    SPSDKDebugProbeNotOpenError,
    SPSDKDebugProbeTransferError,
)
from spsdk.utils.spsdk_enum import SpsdkEnum

import lauterbach.trace32.rcl as t32

logger = logging.getLogger(__name__)


class T32Mode(SpsdkEnum):
    """Enumeration of known T32 Modes (SYStem.Mode)."""

    DOWN = (0, "Down")
    STAND_BY = (1, "StandBy")
    NO_DEBUG = (2, "NoDebug")
    PREPARE = (4, "Prepare")
    UP = (11, "Up")
    UNKNOWN = (255, "UNKNOWN")


def ensure_mode(mode: Optional[T32Mode]) -> Callable:
    """Decorator that checks if connection is open and sets T32 mode.

    If `mode` is set to None, perform only check for open connection.
    """

    def decorator(func: Callable) -> Any:
        @functools.wraps(func)
        def wrapper(self: "DebugProbeLauterbach", *args: Any, **kwargs: Any) -> Any:
            self.set_mode(mode=mode)
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


class DebugProbeLauterbach(DebugProbeCoreSightOnly):
    """SPSDK Debug Probe Lauterbach debug probe plugin class."""

    NAME = "lauterbach"

    def __init__(self, hardware_id: str, options: Optional[Dict] = None) -> None:
        """The Debug Probe class initialization."""
        super().__init__(hardware_id, options)
        self.address, self.port = self.parse_options(options=options)
        self.connection: Optional[t32.Debugger] = None
        self.mode = T32Mode.UNKNOWN

    @classmethod
    def parse_options(cls, options: Optional[Dict] = None) -> Tuple[str, int]:
        """Parse options passed to __init__ method.

        :param options: Options passed to __init__ method, defaults to None
        :return: T32 address and port (default localhost, 20_000)
        """
        if not options:
            address = "localhost"
            port = 20_000
        else:
            ip: str = options.get("ip", "localhost:20000")
            parts = ip.split(":")
            address = parts[0]
            port = 20_000 if len(parts) == 1 else int(parts[1], 0)

        return address, port

    @classmethod
    def get_connected_probes(
        cls, hardware_id: Optional[str] = None, options: Optional[Dict] = None
    ) -> DebugProbes:
        """Functions returns the list of all connected probes in system.

        There is option to look for just for one debug probe defined by its hardware ID.

        :param hardware_id: None to list all probes, otherwise the the only probe with
            matching hardware id is listed.
        :param options: The options dictionary
        :return: List of ProbeDescription
        """
        probes = DebugProbes()
        address, port = cls.parse_options(options=options)
        try:
            connection = t32.connect(node=address, port=port, timeout=1.0)
            serial = connection.fnc("LICENSE.SERIAL(0)")
            if hardware_id and hardware_id != serial:
                return probes
            probes.append(
                ProbeDescription(
                    interface="lauterbach",
                    hardware_id=serial,
                    description=f"Lauterbach probe at {address}:{port}",
                    probe=cls,
                )
            )
            connection.disconnect()
        except (ConnectionRefusedError, TimeoutError):
            pass

        return probes

    @classmethod
    def get_options_help(cls) -> Dict[str, str]:
        """Get full list of options of debug probe.

        :return: Dictionary with individual options. Key is parameter name and value the help text.
        """
        options_help = super().get_options_help()
        options_help["ip"] = (
            "[HOST][:PORT] of the Lauterbach T32. Default HOST: localhost, default PORT: 20_000"
        )
        options_help["note"] = (
            "Your config.t32 file shall contain the following settings: RCL=NETTCP PORT=20000"
        )
        return options_help

    def open(self) -> None:
        """Debug probe open.

        General opening function for SPSDK library to support various DEBUG PROBES.
        The function is used to initialize the connection to target and enable using debug probe
        for DAT purposes.
        """
        self.connection = t32.connect(node=self.address, port=self.port)

    def connect(self) -> None:
        """Connect to target.

        The PyLink connecting function for SPSDK library to support various DEBUG PROBES.
        The function is used to initialize the connection to target

        :raises SPSDKDebugProbeError: The PyLink cannot establish communication with target
        """
        self.set_mode(T32Mode.PREPARE)

    def close(self) -> None:
        """Debug probe close.

        This is general closing function for SPSDK library to support various DEBUG PROBES.
        """
        if self.connection:
            self.set_mode(T32Mode.DOWN)
            self.connection.disconnect()
            self.connection = None

    def set_mode(self, mode: Optional[T32Mode]) -> None:
        """Method to check if connection is open and sets Trace32 to desired mode.

        If `mode` is set to None, perform only check for open connection.
        """
        if self.connection is None:
            raise SPSDKDebugProbeNotOpenError()
        if mode is None:
            return
        if self.mode == mode:
            return
        try:
            self.connection.cmd(f"SYStem.Mode {mode.label}")
        except t32.CommandError:
            time.sleep(self.RESET_TIME)
        try:
            self.connection.cmd(f"SYStem.Mode {mode.label}")
        except t32.CommandError as e:
            raise SPSDKDebugProbeError(f"Unable to set mode: {mode.label}. Error: {e}") from e
        self.mode = T32Mode.from_tag(self.connection.fnc("SYStem.Mode()"))
        if self.mode != mode:
            raise SPSDKDebugProbeError(f"Unable to set mode: {mode.label}")

    def _get_cs_addr(self, access_port: bool, addr: int) -> int:
        """Get CoreSight register address.

        :param access_port: Get address for Access Port (set to false for Debug Port)
        :param addr: Address of the Coresight register
        :return: Full CoreSight register address
        """
        if access_port:
            ap_num = (addr & self.APSEL) >> self.APSEL_SHIFT
            return self._get_ap_addr(ap_num, addr)
        return self._get_dp_addr(addr)

    @staticmethod
    def _get_dp_addr(reg_addr: int) -> int:
        """Encode DP register byte address into T32 special format.

        :param reg_addr: DP register address
        :return: T32 DP address
        """
        addr = reg_addr & 0xFF
        addr |= 0x4100_0000
        return addr

    @staticmethod
    def _get_ap_addr(ap_number: int, reg_addr: int) -> int:
        """Encode AP register byte address into T32 special format.

        :param ap_number: AP index
        :param reg_addr: AP register address
        :return: T32 AP address
        """
        addr = reg_addr & 0xFF
        addr |= (ap_number & 0xFF) << 8
        addr |= 0x4000_0000
        return addr

    @ensure_mode(T32Mode.PREPARE)
    def coresight_reg_read(self, access_port: bool = True, addr: int = 0) -> int:
        """Read coresight register.

        It reads coresight register function for SPSDK library to support various DEBUG PROBES.

        :param access_port: if True, the Access Port (AP) register will be read(default), otherwise the Debug Port
        :param addr: the register address
        :return: The read value of addressed register (4 bytes)
        """
        logger.debug(f"CS READ: AP: {access_port}, ADDR: {addr:#x}")
        try:
            cs_addr = self._get_cs_addr(access_port=access_port, addr=addr)
            cmd = f"DATA.LONG(EDBG:{cs_addr:#06x})"
            data = self.connection.fnc(cmd)  # type: ignore[union-attr] # None case is handled by "ensure_mode"
            logger.debug(f"RESULT: {data:#x}")
            return data
        except t32.FunctionError as e:
            raise SPSDKDebugProbeTransferError(str(e)) from e

    @ensure_mode(T32Mode.PREPARE)
    def coresight_reg_write(self, access_port: bool = True, addr: int = 0, data: int = 0) -> None:
        """Write coresight register.

        It writes coresight register function for SPSDK library to support various DEBUG PROBES.

        :param access_port: if True, the Access Port (AP) register will be write(default), otherwise the Debug Port
        :param addr: the register address
        :param data: the data to be written into register
        """
        logger.debug(f"CS WRITE: AP: {access_port}, ADDR: {addr:#x}")
        try:
            cs_addr = self._get_cs_addr(access_port=access_port, addr=addr)
            cmd = f"DATA.SET EDBG:{cs_addr:#06x} %Long {data:#x}"
            try:
                self.connection.cmd(cmd)  # type: ignore[union-attr] # None case is handled by "ensure_mode"
            except t32.CommandError as e:
                if e.args[0] == "target reset detected":
                    time.sleep(0.5)
                    return
                raise
        except t32.CommandError as e:
            raise SPSDKDebugProbeTransferError(str(e)) from e

    @ensure_mode(None)
    def assert_reset_line(self, assert_reset: bool = False) -> None:
        """Control reset line at a target.

        :param assert_reset: If True, the reset line is asserted(pulled down), if False the reset line is not affected.
        """
        if assert_reset:
            self.connection.cmd("SYStem.RESetOut")  # type: ignore[union-attr] # None case is handled by "ensure_mode"

    @ensure_mode(None)
    def clear_sticky_errors(self) -> None:
        """Clear sticky errors of Debug port interface."""
        self.set_mode(T32Mode.DOWN)
        self.set_mode(T32Mode.PREPARE)

    def __str__(self) -> str:
        """Return information about the device."""
        return f"lauterbach at {self.address}:{self.port}"
