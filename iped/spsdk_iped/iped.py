#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""IPED PRINCE cipher engine using C++ shared library via ctypes."""

import ctypes
import logging
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


class IPEDError(Exception):
    """IPED operation error."""


class _Transaction(  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    ctypes.Structure
):
    """C struct matching the prince_mem_enc transaction layout."""

    _fields_ = [
        ("mode", ctypes.c_uint32),
        ("dec", ctypes.c_uint32),
        ("run_dbl_enc", ctypes.c_uint32),
        ("i_data", ctypes.POINTER(ctypes.c_uint64)),
        ("iv", ctypes.c_uint64),
        ("address", ctypes.POINTER(ctypes.c_uint64)),
        ("data_key0", ctypes.c_uint64),
        ("data_key1", ctypes.c_uint64),
        ("o_data", ctypes.POINTER(ctypes.c_uint64)),
        ("in_ad", ctypes.c_uint64),
        ("in_auth_tag", ctypes.c_uint64),
        ("o_auth_tag", ctypes.c_uint64),
    ]


class IPED:  # pylint: disable=too-many-instance-attributes
    """IPED PRINCE cipher wrapper over native C++ shared library.

    Provides CTR and GCM encryption/decryption using a compiled PRINCE
    cipher core (``prince.so`` / ``prince.dll``).
    """

    BLOCK_SIZE = 8
    KEY_SIZE = 16

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        key: Union[int, bytes],
        address: Union[int, bytes],
        iv: Union[int, bytes],
        use_gcm: bool = False,
        aad: Union[int, bytes, None] = None,
        tag: Union[int, bytes] = 0,
        double_encrypt: bool = False,
    ) -> None:
        """Initialize IPED cipher instance.

        :param key: 128-bit encryption key (int or 16 bytes).
        :param address: Starting memory address for encryption.
        :param iv: 64-bit initialization vector.
        :param use_gcm: Use GCM mode (True) or CTR mode (False).
        :param aad: Additional Authentication Data for GCM mode.
        :param tag: Authentication tag for GCM decryption verification.
        :param double_encrypt: Enable double-encryption (22 effective rounds).
        :raises IPEDError: If parameters are invalid or library cannot be loaded.
        """
        self.key = (
            key if isinstance(key, bytes) else key.to_bytes(length=self.KEY_SIZE, byteorder="big")
        )
        self.key0 = int.from_bytes(self.key[: self.BLOCK_SIZE], byteorder="big")
        self.key1 = int.from_bytes(self.key[self.BLOCK_SIZE :], byteorder="big")

        if len(self.key) != 2 * self.BLOCK_SIZE:
            raise IPEDError(
                f"Invalid key length. Expected {2 * self.BLOCK_SIZE}B, got {len(self.key)}B."
            )
        self.iv = iv if isinstance(iv, int) else int.from_bytes(iv, byteorder="big")
        if self.iv.bit_length() > 8 * self.BLOCK_SIZE:
            raise IPEDError(f"IV is too big. Expected up to {self.BLOCK_SIZE}B.")

        self.next_address = (
            address if isinstance(address, int) else int.from_bytes(address, byteorder="big")
        )
        self.double_encrypt = 0x1 if double_encrypt else 0x0

        self.mode = 0x1 if use_gcm else 0x0
        if use_gcm:
            if aad is None:
                raise IPEDError("GCM encryption requires AAD (Additional Authentication Data)")
            self.aad = aad if isinstance(aad, int) else int.from_bytes(aad, byteorder="big")
        else:
            self.aad = 0
        self.tag = tag if isinstance(tag, int) else int.from_bytes(tag, byteorder="big")

        self.lib_file = Path(__file__).parent / "prince.so"
        if not self.lib_file.exists():
            raise IPEDError(
                f"PRINCE shared library not found at {self.lib_file}. "
                "Make sure the package was built with C++ extension compilation."
            )
        self._lib = ctypes.CDLL(str(self.lib_file))
        self.prince_mem_enc = self._lib["prince_mem_enc"]
        self.prince_mem_enc.argtypes = [ctypes.c_int, ctypes.POINTER(_Transaction)]
        self.prince_mem_enc.restype = ctypes.c_int

    def decrypt(self, data: Union[bytes, int], address: Optional[int] = None) -> bytes:
        """Decrypt data using PRINCE cipher.

        :param data: Encrypted data (bytes or single 64-bit int).
        :param address: Optional override address for this block.
        :return: Decrypted data bytes.
        """
        if isinstance(data, int):
            data = data.to_bytes(length=8, byteorder="big")
        return self._transaction(decrypt=True, data=data, address=address)

    def encrypt(self, data: Union[bytes, int], address: Optional[int] = None) -> bytes:
        """Encrypt data using PRINCE cipher.

        :param data: Plaintext data (bytes or single 64-bit int).
        :param address: Optional override address for this block.
        :return: Encrypted data bytes.
        """
        if isinstance(data, int):
            data = data.to_bytes(length=8, byteorder="big")
        return self._transaction(decrypt=False, data=data, address=address)

    def is_gcm(self) -> bool:
        """Check if GCM mode is enabled.

        :return: True if GCM mode, False if CTR mode.
        """
        return self.mode == 1

    def _transaction(self, decrypt: bool, data: bytes, address: Optional[int] = None) -> bytes:
        """Execute PRINCE cipher transaction via native library.

        :param decrypt: True for decryption, False for encryption.
        :param data: Input data bytes.
        :param address: Optional override starting address.
        :return: Output data bytes.
        :raises IPEDError: If native library returns error code.
        """
        transaction = _Transaction()
        transaction.mode = self.mode
        transaction.run_dbl_enc = self.double_encrypt
        transaction.dec = 0x1 if decrypt else 0x0
        transaction.iv = self.iv
        transaction.data_key0 = self.key0
        transaction.data_key1 = self.key1
        transaction.in_ad = self.aad
        transaction.in_auth_tag = self.tag
        transaction.o_auth_tag = 0x0

        address = address if address is not None else self.next_address

        n_blocks = (len(data) + self.BLOCK_SIZE - 1) // self.BLOCK_SIZE
        padded_size = n_blocks * self.BLOCK_SIZE
        data = data.ljust(padded_size, b"\x00")

        if self.is_gcm():
            o_data = (ctypes.c_uint64 * n_blocks)()
            i_address = (ctypes.c_uint64 * n_blocks)()
            i_data = (ctypes.c_uint64 * n_blocks)()

            for i in range(n_blocks):
                i_address[i] = address + i * 8
                i_data[i] = int.from_bytes(data[8 * i : 8 * (i + 1)], byteorder="big")

            transaction.address = i_address
            transaction.i_data = i_data
            transaction.o_data = o_data

            status_code = self.prince_mem_enc(n_blocks, ctypes.byref(transaction))

            if status_code != 1:
                raise IPEDError(f"Encryption failed with error code: {status_code}")

            self.tag = transaction.o_auth_tag
            self.next_address = address + padded_size
            return b"".join(o.to_bytes(8, "big") for o in o_data)

        # CTR mode: process block by block
        o_data = (ctypes.c_uint64 * 1)()
        i_address = (ctypes.c_uint64 * 1)()
        i_data = (ctypes.c_uint64 * 1)()

        result = bytearray()

        for i in range(n_blocks):
            i_data[0] = int.from_bytes(data[8 * i : 8 * (i + 1)], byteorder="big")
            i_address[0] = address + 8 * i

            transaction.i_data = i_data
            transaction.address = i_address
            transaction.o_data = o_data

            status_code = self.prince_mem_enc(1, ctypes.byref(transaction))

            if status_code != 1:
                raise IPEDError(f"Encryption failed with error code: {status_code}")

            result.extend(o_data[0].to_bytes(8, "big"))

        self.next_address = address + padded_size
        return bytes(result)
