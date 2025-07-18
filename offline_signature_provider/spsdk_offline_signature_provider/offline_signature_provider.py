#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# -*- coding: UTF-8 -*-
#
# Copyright 2023,2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Main module for OfflineSP."""


from pathlib import Path
from typing import Any

from spsdk.crypto.hash import EnumHashAlgorithm, get_hash
from spsdk.crypto.keys import PublicKeyEcc
from spsdk.crypto.signature_provider import SignatureProvider

# mapping key_size -> hash algorithm
_HASH_ALGS = {
    256: EnumHashAlgorithm.SHA256,
    384: EnumHashAlgorithm.SHA384,
    521: EnumHashAlgorithm.SHA512,
}
# mapping key_size -> signature_length
_SIG_SIZES = {256: 64, 384: 96, 521: 132}


class OfflineSP(SignatureProvider):
    """Offline Signature Provider."""

    # identifier of this signature provider; used in yaml configuration file
    identifier = "offline-sp"

    # pylint: disable=unused-argument
    def __init__(
        self, hash_file: str = "ahab_container_hash", key_size: int = 256, **kwargs: Any
    ) -> None:
        """Initialize the Offline SignatureProvider.

        :param hash_file: File to store the hash
        :param key_size: Size of the key in bits
        :param args: Variable positional arguments (not used)
        :param kwargs: Variable keyword arguments (not used)
        """
        self.hash_file = hash_file
        self.key_size = key_size
        self.hash_alg = _HASH_ALGS[self.key_size]
        self.sig_size = _SIG_SIZES[self.key_size]

    def _validate_file_path(self, file_path: str) -> str:
        """Validate and sanitize file path.

        :param file_path: The file path to validate
        :return: Validated file path
        :raises ValueError: If path is invalid
        """
        if not file_path or not file_path.strip():
            raise ValueError("File path cannot be empty")

        # Convert to Path object for safer handling
        try:
            path = Path(file_path).resolve()
        except (OSError, ValueError) as e:
            raise ValueError(f"Invalid file path: {file_path}") from e

        # Check for suspicious path components
        path_parts = path.parts
        for part in path_parts:
            if any(char in part for char in ["<", ">", "|", "*", "?"]):
                raise ValueError(f"Invalid characters in path: {file_path}")

        return str(path)

    def sign(self, data: bytes) -> bytes:
        """Perform the signing.

        :param data: Data to sign
        :return: Signature
        """
        data_hash = get_hash(data=data, algorithm=self.hash_alg)
        print(f"Hash value: {data_hash.hex()}")

        full_hash_file_path = f"{self.hash_file}.{self.hash_alg.label}"
        with open(full_hash_file_path, "wb") as f:
            f.write(data_hash)
        print(f"Hash is also stored in file: {full_hash_file_path}")

        while True:
            sig_file_input = input("Provide path to signature file: ")
            try:
                sig_file = self._validate_file_path(sig_file_input)
            except ValueError as e:
                print(f"Error: {e}")
                continue
            with open(sig_file, "rb") as f:
                sig_data = f.read()
            # check if we have raw r||s signature
            if len(sig_data) == self.signature_length:
                return sig_data
            # attempt to extract r||s from DER-encoded signature
            sig_data = PublicKeyEcc.serialize_signature(
                signature=sig_data, coordinate_length=self.key_size // 8
            )
            if len(sig_data) == self.signature_length:
                return sig_data

            raise ValueError(
                "Got incorrect signature size! "
                f"Expected: {self.signature_length} (or DER-encoded equivalent), actual: {len(sig_data)}"
            )

    @property
    def signature_length(self) -> int:
        """Return length of the signature."""
        return self.sig_size
