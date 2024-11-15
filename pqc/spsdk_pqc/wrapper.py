#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Wrapper for Dilithium library."""

import pathlib
from ctypes import CDLL, POINTER, byref, c_char_p, c_int, c_ulonglong, create_string_buffer
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


@dataclass
class KeyInfo:
    """Dilithium Key information class."""

    level: int
    private_key_size: int
    public_key_size: int
    signature_size: int


KEY_INFO = {
    2: KeyInfo(level=2, private_key_size=2528, public_key_size=1312, signature_size=2420),
    3: KeyInfo(level=3, private_key_size=4000, public_key_size=1952, signature_size=3293),
    5: KeyInfo(level=5, private_key_size=4864, public_key_size=2592, signature_size=4595),
}


def get_crypto_library_path(mode: int = 3, use_aes: bool = False) -> str:
    """Get path to selected crypto backend library.

    :param level: NIST claim level, defaults to 3
    :param use_aes: Use AES version of the algorithm, defaults to False
    :return: Path to crypto backend library
    """
    if use_aes:
        raise NotImplementedError("AES mode is not yet supported")
    return str(pathlib.Path(__file__).parent / f"_dil{mode}.so")


def get_key_info(level: int = 3) -> KeyInfo:
    """Get sizes of private key, public key, and signature for Dilithium in given mode.

    :param mode: NIST claim level (Dilithium mode) (2, 3, 5), defaults to 3
    :return: Tuple of private key, public key, and signature lengths
    """
    return KEY_INFO[level]


class DilithiumWrapper:
    """Wrapper class for Dilithium DLL."""

    # pylint: disable=too-many-instance-attributes
    def __init__(self, level: int = 3, use_aes: bool = False, randomized: bool = True) -> None:
        """Initialize the Dilithium wrapper class.

        :param mode: Dilithium mode (NIST claim level), defaults to 2
        :param use_aes: Use AES-CRT instead of SHAKE256, defaults to False
        :param randomized: Use randomized signing
        """
        self.level = level
        self.use_aes = use_aes
        self.randomized = randomized
        self._lib_path = get_crypto_library_path(mode=level, use_aes=use_aes)
        self.key_info = get_key_info(level=level)

        self._lib = CDLL(self._lib_path)
        self._infix = f"{level}{'aes' if use_aes else ''}"

        self._keypair = self._lib[f"pqcrystals_dilithium{self._infix}_ref_keypair"]
        self._keypair.argtypes = [c_char_p, c_char_p]
        self._keypair.restype = c_int

        self._sign = self._lib[f"pqcrystals_dilithium{self._infix}_ref_signature"]
        self._sign.argtypes = [
            c_char_p,
            POINTER(c_ulonglong),
            c_char_p,
            c_ulonglong,
            c_char_p,
        ]
        self._sign.restype = c_int

        self._verify = self._lib[f"pqcrystals_dilithium{self._infix}_ref_verify"]
        self._verify.argtypes = [c_char_p, c_ulonglong, c_char_p, c_ulonglong, c_char_p]
        self._verify.restype = c_int

    def key_pair(self) -> Tuple[bytes, bytes]:
        """Generate a key pair.

        :raises RuntimeError: Failure during key generation
        :return: Tuple containing private key and public key
        """
        public_key = create_string_buffer(self.key_info.public_key_size)
        private_key = create_string_buffer(self.key_info.private_key_size)

        if self._keypair(public_key, private_key):
            raise RuntimeError("Keygen malfunctioned!")
        return private_key.raw, public_key.raw

    def sign(self, data: bytes, private_key: bytes) -> bytes:
        """Sign data using the private key.

        :param data: Data to sign
        :param private_key: Private key to sign the data
        :raises RuntimeError: Invalid size of the private key
        :raises RuntimeError: Sign operation fails
        :return: Signature
        """
        if len(private_key) != self.key_info.private_key_size:
            raise RuntimeError(
                "Invalid private key size! "
                f"Expected: {self.key_info.private_key_size}, got: {len(private_key)}"
            )
        d = create_string_buffer(data)
        dlen = c_ulonglong(len(data))
        s = create_string_buffer(self.key_info.signature_size)
        slen = c_ulonglong(0)
        prk = create_string_buffer(private_key)

        if self._sign(s, byref(slen), d, dlen, prk):
            raise RuntimeError("Signing malfunctioned!")
        return s.raw[: slen.value]

    def verify(self, data: bytes, signature: bytes, public_key: bytes) -> bool:
        """Verify signature using the public key.

        :param data: Original data that were signed
        :param signature: Signature
        :param public_key: Public key
        :raises RuntimeError: Invalid size of the signature
        :raises RuntimeError: Invalid size of the public key
        :return: True if signature matches
        """
        if len(signature) != self.key_info.signature_size:
            raise RuntimeError(
                "Invalid signature size! "
                f"Expected {self.key_info.signature_size}, got: {len(signature)}"
            )
        if len(public_key) != self.key_info.public_key_size:
            raise RuntimeError(
                "Invalid public key size! "
                f"Expected {self.key_info.public_key_size}, got {len(public_key)}"
            )
        d = create_string_buffer(data)
        dlen = c_ulonglong(len(data))
        s = create_string_buffer(signature)
        puk = create_string_buffer(public_key)

        if self._verify(s, self.key_info.signature_size, d, dlen, puk):
            return False
        return True


BACKENDS = {
    2: DilithiumWrapper(level=2),
    3: DilithiumWrapper(level=3),
    5: DilithiumWrapper(level=5),
}


class DilObjectType(Enum):
    """Dilithium Object type enumeration."""

    PRIVATE_DATA = "private_data"
    PUBLIC_DATA = "public_data"
    PRIVATE_PUBLIC_DATA = "private_public_data"
    SIGNATURE_DATA = "signature_data"

    @classmethod
    def detect(cls, data: bytes) -> Tuple["DilObjectType", KeyInfo]:
        """Detect the Dilithium key type.

        :param data: Data representation of Dilithium key/signature
        :raises ValueError: Invalid data given.
        :return: Tuple of data type and its key information.
        """
        for key_info in KEY_INFO.values():
            if len(data) == key_info.private_key_size + key_info.public_key_size:
                return cls.PRIVATE_PUBLIC_DATA, key_info
            if len(data) == key_info.private_key_size:
                return cls.PRIVATE_DATA, key_info
            if len(data) == key_info.public_key_size:
                return cls.PUBLIC_DATA, key_info
            if len(data) == key_info.signature_size:
                return cls.SIGNATURE_DATA, key_info
        raise ValueError(f"Data of length {len(data)} doesn't represent any object in Dilithium.")


class DilithiumPrivateKey:
    """Dilithium private key class."""

    def __init__(self, level: Optional[int] = None, data: Optional[bytes] = None) -> None:
        """Dilithium private key constructor.

        :param level: Optional level of dilithium algorithm, defaults to None
        :param data: Data of private key, defaults to None
        :raises ValueError: You must provide either 'data' or 'level'
        :raises ValueError: Provided data do not represent a private key
        """
        self.public_data: Optional[bytes] = None
        if data is None:
            if level is None:
                raise ValueError("You must provide either 'data' or 'level'")
            self.backend = BACKENDS[level]
            self.private_data, self.public_data = self.backend.key_pair()
        else:
            data_type, key_info = DilObjectType.detect(data=data)
            if data_type not in [DilObjectType.PRIVATE_DATA, DilObjectType.PRIVATE_PUBLIC_DATA]:
                raise ValueError("Provided data do not represent a private key")
            self.backend = BACKENDS[key_info.level]
            self.private_data = data[: key_info.private_key_size]
            if data_type == DilObjectType.PRIVATE_PUBLIC_DATA:
                self.public_data = data[key_info.private_key_size :]

    def sign(self, data: bytes) -> bytes:
        """Sign the data by Dilithium key.

        :param data: Data to sign.
        :return: Signature data.
        """
        return self.backend.sign(data=data, private_key=self.private_data)

    def verify(self, data: bytes, signature: bytes) -> bool:
        """Verify Dilithium signature.

        :param data: Signed data.
        :param signature: Signature data.
        :raises ValueError: The key doesn't contains the public data usable to verify.
        :return: True if signature fits the data, False otherwise.
        """
        if self.public_data is None:
            raise ValueError("The key doesn't contains the public data usable to verify.")
        return self.backend.verify(data=data, signature=signature, public_key=self.public_data)

    @property
    def signature_size(self) -> int:
        """Signature size."""
        return self.backend.key_info.signature_size

    @property
    def key_size(self) -> int:
        """Key size."""
        return self.backend.key_info.private_key_size

    @property
    def level(self) -> int:
        """Dilithium algorithm level."""
        return self.backend.key_info.level


class DilithiumPublicKey:
    """Dilithium public key class."""

    def __init__(self, public_data: bytes) -> None:
        """Dilithium public key constructor.

        :param public_data: Dilithium public key data.
        :raises ValueError: Provided data do not represent a public key.
        """
        data_type, key_info = DilObjectType.detect(data=public_data)
        if data_type != DilObjectType.PUBLIC_DATA:
            raise ValueError("Provided data do not represent a public key")
        self.backend = BACKENDS[key_info.level]
        self.public_data = public_data

    def verify(self, data: bytes, signature: bytes) -> bool:
        """Verify Dilithium signature.

        :param data: Signed data.
        :param signature: Signature data.
        :return: True if signature fits the data, False otherwise.
        """
        return self.backend.verify(data=data, signature=signature, public_key=self.public_data)

    @property
    def signature_size(self) -> int:
        """Signature size."""
        return self.backend.key_info.signature_size

    @property
    def key_size(self) -> int:
        """Key size."""
        return self.backend.key_info.public_key_size

    @property
    def level(self) -> int:
        """Dilithium algorithm level."""
        return self.backend.key_info.level
