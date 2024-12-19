#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""This module provides functionality for interfacing with DAP probes.

It implements classes and utilities for managing DAP (Debug Access Port) probes,
including probe discovery, connection handling, and communication. The module supports
various probe interfaces and provides data structures for probe information management.
"""
import ctypes
import logging
from dataclasses import dataclass
from time import sleep
from typing import Any, Callable, cast

import hid
import libusb_package
import usb.core
import usb.util
from typing_extensions import Optional, Union

from .webix_dapper_wasm import Uint8Array, WebixDapperWasm

logger = logging.getLogger("dapper")

# todo(mkelnar) replace by trace flag and prepare formatter stdout/json for it
deep_trace: bool = False


@dataclass
class DapperProbeInfo:
    """Class representing information about a DAP probe."""

    serial_no: str = ""
    description: str = ""
    device = None

    def __init__(self, serial_no: str, description: str, device: Any = None):
        """Initialize a new DapperProbeInfo instance.

        :param serial_no: Serial number of the probe
        :param description: Description or name of the probe
        :param device: Associated device object
        """
        super().__init__()
        self.serial_no = serial_no
        self.description = description
        self.device = device


@dataclass
class ProbeInfo:
    """Class representing information about a probe."""

    vendor_id: str = ""
    product_id: str = ""
    serial_no: str = ""
    firmware_ver: str = ""
    target_vendor: str = ""
    target_name: str = ""
    board_vendor: str = ""
    board_name: str = ""
    product_fw_ver: str = ""

    @staticmethod
    def from_dict(data: dict[str, str]) -> "ProbeInfo":
        """Create ProbeInfo instance from dictionary.

        :param data: Dictionary containing probe information
        :return: New ProbeInfo instance
        """
        instance = ProbeInfo()
        instance.vendor_id = data.get("vendorId", "N/A")
        instance.product_id = data.get("productId", "N/A")
        instance.serial_no = data.get("serialNo", "N/A")
        instance.firmware_ver = data.get("firmwareVer", "N/A")
        instance.target_vendor = data.get("targetVendor", "N/A")
        instance.target_name = data.get("targetName", "N/A")
        instance.board_vendor = data.get("boardVendor", "N/A")
        instance.board_name = data.get("boardName", "N/A")
        instance.product_fw_ver = data.get("productFwVer", "N/A")
        return instance


class Interface:
    """Base class for probe interfaces.

    This class provides a common interface for working with different types of debug probes.
    It defines basic properties and methods that all probe interfaces should implement.
    """

    def __init__(self) -> None:
        """Initialize Interface instance.

        :return: None
        """
        self._type: str = "unknown"
        self._device: Any = None
        self.vid: int = 0
        self.pid: int = 0
        self.vendor: str = ""
        self.product: str = ""
        self.serial_no: str = ""
        self.packet_size: int = 0

    @staticmethod
    def list_probes() -> list["Interface"]:
        """List available probes.

        :return: List of Interface instances
        """
        raise NotImplementedError("Probes listing not implemented")

    @property
    def type(self) -> str:
        """Get interface type.

        :return: Interface type string
        """
        return self._type

    @property
    def probe_id(self) -> str:
        """Get probe identifier.

        :return: Probe serial number
        :raises RuntimeError: If device is not initialized
        """
        if self._device is None:
            raise RuntimeError("Device not initialized")
        return self._device.serial_number

    @property
    def description(self) -> str:
        """Get interface description.

        :return: Description string combining vendor and product
        """
        return f"{self.vendor} {self.product}"

    def open(self) -> None:
        """Open the interface connection.

        :return: None
        :raises RuntimeError: If USB device is undefined
        """
        if self._device is None:
            raise RuntimeError("USB device is undefined.")

    def close(self) -> None:
        """Close the interface connection.

        :return: None
        :raises NotImplementedError: If not implemented in derived class
        """
        raise NotImplementedError(f"{self.__class__}.close() must be implemented.")

    def write(self, data: Uint8Array) -> None:
        """Write data to interface.

        :param data: Data to write
        :return: None
        :raises NotImplementedError: If not implemented in derived class
        """
        raise NotImplementedError(f"{self.__class__}.write() must be implemented.")

    def read(self) -> Uint8Array:
        """Read data from interface.

        :return: Data read from interface
        :raises NotImplementedError: If not implemented in derived class
        """
        raise NotImplementedError(f"{self.__class__}.read() must be implemented.")


class HidInterface(Interface):
    """HID interface implementation for communicating with USB HID devices.

    This class provides functionality for interfacing with USB HID devices,
    specifically NXP debug probes like LPC-Link2, MCU-Link and DAP-Link.
    It handles device enumeration, connection management and data transfer.
    """

    def __init__(
        self, device: hid.device, info: dict  # pylint: disable=c-extension-no-member
    ) -> None:
        """Initialize HID interface.

        :param device: HID device instance
        :param info: Dictionary containing device information
        """
        super().__init__()
        self._type = "hid"
        self._device = device

        self.serial_no = info["serial_number"]
        self.vid = info["vendor_id"]
        self.pid = info["product_id"]
        self.vendor = info["manufacturer_string"]
        self.product = info["product_string"]
        self.device_info = info

        self.packet_size = 64

    @staticmethod
    def list_probes() -> list[Interface]:
        """List available HID probes.

        :return: List of available HID interfaces
        """
        probes: list[Interface] = []

        devices = hid.enumerate()  # pylint: disable=c-extension-no-member
        for device_info in devices:
            if device_info["vendor_id"] in {0x1FC9, 0xD28}:  # nxp vid, dap link vid
                if device_info["product_id"] in {
                    0x0090,
                    0x0143,
                    0x204,
                }:  # lpc-link, mcu-link, dap-link
                    if device_info["usage_page"] == 0xFF00:  # vendor defined usage page
                        device = hid.device(  # pylint: disable=c-extension-no-member
                            vendor_id=device_info["vendor_id"],
                            product_id=device_info["product_id"],
                            path=device_info["path"],
                        )
                        probes.append(HidInterface(device, device_info))

        return probes

    def open(self) -> None:
        """Open the HID interface connection.

        :raises RuntimeError: If device is not initialized
        """
        super().open()

        self._device.open_path(self.device_info["path"])

    def close(self) -> None:
        """Close the HID interface connection."""
        if self._device is not None:
            self._device.close()

    def write(self, data: Uint8Array) -> None:
        """Write data to HID interface.

        :param data: Data to write
        """
        write_data = ([0] + list(data.buffer))[0:64]
        self._device.write(write_data)
        if deep_trace:
            print(
                "write: ("
                + str(len(data.buffer))
                + ") ["
                + ",".join(f"{x:02X}" for x in write_data[0:64])
                + "]"
            )

    def read(self) -> Uint8Array:
        """Read data from HID interface.

        :return: Data read from interface
        :raises RuntimeError: If device endpoint is not opened
        """
        if self._device is None:
            raise RuntimeError("Device endpoint needs to be opened first.")
        data = self._device.read(self.packet_size)
        if deep_trace:
            print(
                "read:  (" + str(len(data)) + ") [" + ",".join(f"{x:02X}" for x in data[0:64]) + "]"
            )

        return Uint8Array((ctypes.c_uint8 * len(data))(*data))

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context manager.

        :param exc_type: Exception type
        :param exc_val: Exception value
        :param exc_tb: Exception traceback
        """
        if self._device is not None:
            self._device.close()


# todo(mkelnar) try import libusb_package, and usb imports to make it available


class UsbInterface(Interface):
    """USB Interface implementation for communicating with USB devices.

    This class provides functionality for USB communication including device enumeration,
    reading/writing data, and managing USB endpoints. It supports NXP specific interfaces
    and handles USB device configuration.
    """

    def __init__(self, device: usb.core.Device) -> None:
        """Initialize USB interface.

        :param device: USB device instance
        """
        super().__init__()
        self._type = "usb"
        self._device = device
        self._endpoint_in: Optional[usb.core.Endpoint] = None
        self._endpoint_out: Optional[usb.core.Endpoint] = None

        self.serial_no = device.serial_number
        self.vendor = device.manufacturer
        self.product = device.product
        self.vid = device.idVendor
        self.pid = device.idProduct
        self.packet_size = 64

    @staticmethod
    def list_probes() -> list[Interface]:
        """List available USB probes.

        :return: List of available USB interfaces
        """
        probes: list[Interface] = []
        # todo(mkelnar) supported_vendor_ids will be changed
        for vid in list([0x1FC9]):
            usb_devices = libusb_package.find(find_all=True, idVendor=vid)
            for usb_device in usb_devices:
                if usb_device.bDeviceClass in {0x00, 0xEF}:  # not HID
                    config = usb_device.get_active_configuration()
                    ifaces = usb.util.find_descriptor(config, find_all=True)
                    for iface in ifaces:
                        if iface.bInterfaceClass == 0xFF:  # nxp specific interface
                            probes.append(UsbInterface(usb_device))
        return probes

    def open(self) -> None:
        """Open the USB interface connection.

        :raises RuntimeError: If unable to find USB device endpoints
        """
        super().open()

        logger.info(f"Device to open: {self._device.product} ({self._device.manufacturer})")

        self._device.set_configuration()
        cfg = self._device.get_active_configuration()
        interfaces = cfg[(0, 0)]

        self._endpoint_in = usb.util.find_descriptor(
            interfaces,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
            == usb.util.ENDPOINT_IN,
        )
        self._endpoint_out = usb.util.find_descriptor(
            interfaces,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
            == usb.util.ENDPOINT_OUT,
        )

        if self._endpoint_in is None or self._endpoint_out is None:
            raise RuntimeError("Unable to fine USB device endpoints.")

    def close(self) -> None:
        """Close the USB interface connection."""
        self._endpoint_in = None
        self._endpoint_out = None

    def write(self, data: Uint8Array) -> None:
        """Write data to USB interface.

        :param data: Data to write
        :raises RuntimeError: If device endpoint is not opened or data is not Uint8Array
        """
        if self._endpoint_out is None:
            raise RuntimeError("Device endpoint needs to be opened first.")
        if not isinstance(data, Uint8Array):
            raise RuntimeError("Data must be an instance of Uint8Array.")
        self._endpoint_out.write(data.buffer, self.packet_size)

    def read(self) -> Uint8Array:
        """Read data from USB interface.

        :return: Data read from interface
        :raises RuntimeError: If device endpoint is not opened
        """
        if self._endpoint_in is None:
            raise RuntimeError("Device endpoint needs to be opened first.")
        data = self._endpoint_in.read(self.packet_size)
        return Uint8Array((ctypes.c_uint8 * len(data))(*data))


class WebixDapper:  # pylint: disable=too-many-public-methods
    """WebixDapper class for handling WASM-based DAP operations."""

    def __init__(self, context_path: Optional[str] = None) -> None:
        """Initialize WebixDapper instance.

        :param context_path: Optional path to the context
        """
        self._module: Optional[WebixDapperWasm] = None
        self.interface: Optional[Interface] = None
        self.trace_data: dict[str, list[str]] = {"inbound": [], "outbound": []}
        self.stdout_handler = None
        self.stderr_handler = None

        self.read_data_handler: Optional[Callable] = None
        self.write_data_handler: Optional[Callable] = None

        self.context_path = context_path

    @property
    def module(self) -> WebixDapperWasm:
        """Get the WebixDapperWasm module instance.

        :return: WebixDapperWasm module instance
        """
        if self._module is None:
            self.init()
        return cast(WebixDapperWasm, self._module)

    @property
    def stdout_handler(self) -> Optional[Callable]:
        """Get the stdout handler.

        :return: Callable stdout handler or None
        """
        return self._stdout_handler

    @stdout_handler.setter
    def stdout_handler(self, value: Optional[Callable]) -> None:
        """Set the stdout handler.

        :param value: Callable handler function or None
        """
        if callable(value):
            self._stdout_handler = value
        else:
            self._stdout_handler = print

    @property
    def stderr_handler(self) -> Optional[Callable]:
        """Get the stderr handler.

        :return: Callable stderr handler or None
        """
        return self._stderr_handler

    @stderr_handler.setter
    def stderr_handler(self, value: Optional[Callable]) -> None:
        """Set the stderr handler.

        :param value: Callable handler function or None
        """
        if callable(value):
            self._stderr_handler = value
        else:
            self._stderr_handler = lambda data: print(f"ERROR: {data}")

    @property
    def read_data_handler(self) -> Optional[Callable]:
        """Get the read data handler.

        :return: Callable read data handler or None
        """
        return self._read_data_handler

    @read_data_handler.setter
    def read_data_handler(self, handler: Optional[Callable]) -> None:
        """Set the read data handler.

        :param handler: Callable handler function or None
        """
        if callable(handler):
            self._read_data_handler = handler
        else:
            self._read_data_handler = self.read_data_usb

    @property
    def write_data_handler(self) -> Optional[Callable]:
        """Get the write data handler.

        :return: Callable write data handler or None
        """
        return self._write_data_handler

    @write_data_handler.setter
    def write_data_handler(self, handler: Optional[Callable]) -> None:
        """Set the write data handler.

        :param handler: Callable handler function or None
        """
        if callable(handler):
            self._write_data_handler = handler
        else:
            self._write_data_handler = self.write_data_usb

    def read_data_usb(self) -> Uint8Array:
        """Read data from USB interface.

        :return: Data read from USB interface as Uint8Array
        :raises RuntimeError: If device interface is not opened
        """
        if self.interface is None:
            raise RuntimeError("Device interface needs to be opened first.")
        return self.interface.read()

    def write_data_usb(self, data: Uint8Array) -> None:
        """Write data to USB interface.

        :param data: Data to write as Uint8Array
        :raises RuntimeError: If device interface is not opened
        """
        if self.interface is None:
            raise RuntimeError("Device interface needs to be opened first.")
        self.interface.write(data)

    def read_data(self) -> Uint8Array:
        """Read data using the configured read data handler.

        :return: Data read as Uint8Array
        """
        return self._read_data_handler()

    def write_data(self, data: Uint8Array) -> None:
        """Write data using the configured write data handler.

        :param data: Data to write as Uint8Array
        """
        self._write_data_handler(data)

    def stdout(self, data: Uint8Array) -> None:
        """Handle stdout data.

        :param data: Data to write to stdout as Uint8Array
        """
        self._stdout_handler(data)

    def stderr(self, data: Uint8Array) -> None:
        """Handle stderr data.

        :param data: Data to write to stderr as Uint8Array
        """
        self._stderr_handler(data)

    def init(self) -> None:
        """Initialize the WebixDapperWasm module and register handlers."""
        module_instance = WebixDapperWasm(self.context_path)
        module_instance.runtime_init()

        def writeData(  # pylint: disable=invalid-name
            instance: "WebixDapper", data: Uint8Array
        ) -> None:
            # pylint: disable=unused-argument
            self.write_data(data)

        def readData(instance: "WebixDapper") -> Uint8Array:  # pylint: disable=invalid-name
            # pylint: disable=unused-argument
            return self.read_data()

        def stdout(instance: "WebixDapper", data: Uint8Array) -> None:
            # pylint: disable=unused-argument
            self.stdout(data)

        def stderr(instance: "WebixDapper", data: Uint8Array) -> None:
            # pylint: disable=unused-argument
            self.stderr(data)

        module_instance.register_handler(readData)
        module_instance.register_handler(writeData)
        module_instance.register_handler(stdout)
        module_instance.register_handler(stderr)
        self._module = module_instance

    def reinit_target(self) -> None:
        """Reinitialize the target."""

    def supported_vendor_ids(self) -> list[int]:
        """Get list of supported vendor IDs.

        :return: List of supported vendor IDs
        """
        # pylint: disable=no-member
        return list(self.module.getSupportedVendorIDs())  # type: ignore[attr-defined]

    def get_probe_id(self) -> Optional[str]:
        """Get the probe ID.

        :return: Probe ID string or None
        :raises RuntimeError: If device interface is not initialized
        """
        if self.interface is None:
            raise RuntimeError("Device interface is not initialized.")
        return self.interface.probe_id

    def open(self, device: Optional[Interface] = None) -> None:
        """Open connection to the device.

        :param device: Interface device to open
        :raises RuntimeError: If probe is undefined
        """
        if device is None:
            raise RuntimeError("Probe is undefined.")
        self.interface = device

        # todo(mkelnar) add checker to identify device and decide to use UsbInterface or HidInterface
        self.interface.open()

        self.get_probe_dap_info()

    def close(self) -> None:
        """Close the device interface connection.

        :raises RuntimeError: If device interface is not opened
        """
        if self.interface is None:
            raise RuntimeError("Device interface needs to be opened first.")
        self.interface.close()

    def power_control(self, sys_power: bool) -> None:
        """Control device power.

        :param sys_power: True for system power, False for debug power
        :raises RuntimeError: If failed to control device power
        """
        # Request value for power control command
        req = 0x0F << 8
        check_status = 0
        if sys_power:
            # Set system power control bit
            req |= 0x40 << 24
            check_status = 0x80 << 24
        else:
            # Set debug power control bit
            req |= 0x10 << 24
            check_status = 0x20 << 24

        # Write power control request
        self.core_sight_write(False, 0x04, req)

        # Wait for power control to complete with timeout
        index = 10
        succeed = False

        while index >= 0:
            sleep(0.1)
            ret = self.core_sight_read(False, 0x04)
            # Check if power control status matches expected value
            if (ret & (0x80 << 24 | 0x20 << 24)) == check_status:
                succeed = True
                break
            index -= 1

        if not succeed:
            raise RuntimeError("Failed to control device power")

    def connect(self) -> None:
        """Connect to the device and control power."""
        # pylint: disable=no-member
        self.module.connect()  # type: ignore[attr-defined]
        self.power_control(True)
        self._stdout_handler("System Power True")
        self.power_control(False)
        self._stdout_handler("Debug Power True")

    def get_probe_dap_info(self) -> ProbeInfo:
        """Get probe DAP information.

        :return: ProbeInfo object containing DAP information
        """
        # pylint: disable=no-member
        data = self.module.getProbeDAPInfo()  # type: ignore[attr-defined]
        return ProbeInfo.from_dict(data)

    def reset(self) -> None:
        """Reset the device."""
        # pylint: disable=no-member
        self.module.reset()  # type: ignore[attr-defined]

    def core_sight_read(self, access_port: bool, address: int) -> int:
        """Read from CoreSight.

        :param access_port: True for access port, False for debug port
        :param address: Address to read from
        :return: Read value
        """
        # pylint: disable=no-member
        return self.module.coreSightRead(access_port, address) & 0xFFFFFFFF  # type: ignore[attr-defined]

    def core_sight_write(self, access_port: bool, address: int, data: int) -> None:
        """Write to CoreSight.

        :param access_port: True for access port, False for debug port
        :param address: Address to write to
        :param data: Data to write
        """
        # pylint: disable=no-member
        self.module.coreSightWrite(access_port, address, data)  # type: ignore[attr-defined]


class DapperFactory:
    """Factory class for creating and managing WebixDapper instances.

    :param _instance: Singleton instance of DapperFactory
    :param _dapper: WebixDapper instance
    :param probes: List of available probes
    :param path: Path to WASM file
    """

    _instance: Optional["DapperFactory"] = None
    _dapper: Optional[WebixDapper] = None
    probes: list[Interface] = []
    path: Optional[str] = None

    def __init__(self) -> None:
        """Initialize DapperFactory.

        :raises RuntimeError: Always raises as singleton should be accessed via instance()
        """
        raise RuntimeError("Get singleton over instance()")

    def dapper(self) -> WebixDapper:
        """Get WebixDapper instance.

        :return: WebixDapper instance
        """
        if self._dapper is None:
            self._dapper = WebixDapper(self.path)
            self._dapper.init()

        return self._dapper

    @classmethod
    def instance(cls) -> "DapperFactory":
        """Get singleton instance of DapperFactory.

        :return: DapperFactory instance
        """
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        return cls._instance

    @classmethod
    def set_wasm_path(cls, path: str) -> None:
        """Set path to WASM file.

        :param path: Path to WASM file
        """
        cls.instance().path = path

    @classmethod
    def list_probes(cls) -> list[Interface]:
        """List all available probes.

        :return: List of available probes
        """
        probes = UsbInterface.list_probes()
        hid_to_add = []
        for hid_device in HidInterface.list_probes():
            if hid_device.serial_no not in {probe.serial_no for probe in probes}:
                hid_to_add.append(hid_device)
        probes += hid_to_add
        DapperFactory.probes = probes
        return probes

    @classmethod
    def create_probe(cls, probe: Union[Interface, str]) -> WebixDapper:
        """Create probe instance.

        :param probe: Probe interface or serial number
        :return: WebixDapper instance
        :raises RuntimeError: If probe type is not supported
        """
        dapper = cls.instance().dapper()
        probe_iface = None
        if isinstance(probe, str):
            for prb in DapperFactory.probes:
                if prb.serial_no == probe:
                    probe_iface = prb
        elif isinstance(probe, Interface):
            probe_iface = probe
        else:
            raise RuntimeError("Not supported probe type detected")

        dapper.open(probe_iface)
        return dapper
