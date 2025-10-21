#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# -*- coding: UTF-8 -*-
#
# Copyright 2023,2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Main module for OfflineSP."""

from enum import Enum
from pathlib import Path
from typing import Any, Optional

from spsdk.crypto.hash import EnumHashAlgorithm, get_hash
from spsdk.crypto.keys import PublicKeyEcc
from spsdk.crypto.signature_provider import SignatureProvider


class SignatureAlgorithm(Enum):
    """Supported signature algorithms."""

    ECC = "ecc"
    RSA_PSS = "rsa-pss"
    RSA_PKCS1V15 = "rsa-pkcs1v15"


# mapping key_size -> hash algorithm for ECC
_ECC_HASH_ALGS = {
    256: EnumHashAlgorithm.SHA256,
    384: EnumHashAlgorithm.SHA384,
    521: EnumHashAlgorithm.SHA512,
}

# mapping key_size -> hash algorithm for RSA (both PSS and PKCS1v15)
_RSA_HASH_ALGS = {
    2048: EnumHashAlgorithm.SHA256,
    3072: EnumHashAlgorithm.SHA256,
    4096: EnumHashAlgorithm.SHA256,
}

# mapping key_size -> signature_length for ECC
_ECC_SIG_SIZES = {256: 64, 384: 96, 521: 132}

# mapping key_size -> signature_length for RSA (signature length equals key size in bytes)
_RSA_SIG_SIZES = {2048: 256, 3072: 384, 4096: 512}

# mapping hash algorithm names to EnumHashAlgorithm
_HASH_ALG_MAP = {
    "sha256": EnumHashAlgorithm.SHA256,
    "sha384": EnumHashAlgorithm.SHA384,
    "sha512": EnumHashAlgorithm.SHA512,
    "sha1": EnumHashAlgorithm.SHA1,
}


class OfflineSP(SignatureProvider):
    """Offline Signature Provider supporting ECC, RSA-PSS, and RSA-PKCS1v15 algorithms."""

    # identifier of this signature provider; used in yaml configuration file
    identifier = "offline-sp"

    # pylint: disable=unused-argument
    def __init__(
        self,
        hash_file: str = "hash_file",
        key_size: str = "256",
        algorithm: str = "ecc",
        hash_algorithm: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Offline SignatureProvider.

        :param hash_file: File to store the hash
        :param key_size: Size of the key in bits
        :param algorithm: Signature algorithm to use ('ecc', 'rsa-pss', or 'rsa-pkcs1v15')
        :param hash_algorithm: Hash algorithm to use ('sha256', 'sha384', 'sha512', 'sha1').
                              If None, uses default based on algorithm and key size.
        :param kwargs: Variable keyword arguments (not used)
        """
        self.hash_file = hash_file
        self.key_size = int(key_size)
        default_hash_alg = None
        # Validate and set algorithm
        try:
            self.algorithm = SignatureAlgorithm(algorithm.lower())
        except ValueError as e:
            raise ValueError(
                f"Unsupported algorithm: {algorithm}. "
                f"Supported: {[alg.value for alg in SignatureAlgorithm]}"
            ) from e

        # Set default hash algorithm and signature size based on algorithm type
        if self.algorithm == SignatureAlgorithm.ECC:
            if self.key_size not in _ECC_HASH_ALGS:
                raise ValueError(
                    f"Unsupported ECC key size: {key_size}. "
                    f"Supported: {list(_ECC_HASH_ALGS.keys())}"
                )
            default_hash_alg = _ECC_HASH_ALGS[self.key_size]
            self.sig_size = _ECC_SIG_SIZES[self.key_size]
        elif self.algorithm in [SignatureAlgorithm.RSA_PSS, SignatureAlgorithm.RSA_PKCS1V15]:
            if self.key_size not in _RSA_HASH_ALGS:
                raise ValueError(
                    f"Unsupported RSA key size: {key_size}. "
                    f"Supported: {list(_RSA_HASH_ALGS.keys())}"
                )
            default_hash_alg = _RSA_HASH_ALGS[self.key_size]
            self.sig_size = _RSA_SIG_SIZES[self.key_size]

        # Set hash algorithm - use provided or default
        if hash_algorithm is not None:
            hash_alg_lower = hash_algorithm.lower()
            if hash_alg_lower not in _HASH_ALG_MAP:
                raise ValueError(
                    f"Unsupported hash algorithm: {hash_algorithm}. "
                    f"Supported: {list(_HASH_ALG_MAP.keys())}"
                )
            self.hash_alg = _HASH_ALG_MAP[hash_alg_lower]
            self.hash_alg_override = True
        else:
            assert default_hash_alg is not None, "Default hash algorithm must be set"
            self.hash_alg = default_hash_alg
            self.hash_alg_override = False

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

    def _process_ecc_signature(self, sig_data: bytes) -> bytes:
        """Process ECC signature data.

        :param sig_data: Raw signature data
        :return: Processed signature data
        :raises ValueError: If signature format is invalid
        """
        # check if we have raw r||s signature
        if len(sig_data) == self.signature_length:
            return sig_data

        # attempt to extract r||s from DER-encoded signature
        try:
            sig_data = PublicKeyEcc.serialize_signature(
                signature=sig_data, coordinate_length=self.key_size // 8
            )
            if len(sig_data) == self.signature_length:
                return sig_data
        except Exception as e:
            raise ValueError(f"Failed to process ECC signature: {e}") from e

        raise ValueError(
            "Got incorrect ECC signature size! "
            f"Expected: {self.signature_length} (or DER-encoded equivalent), "
            f"actual: {len(sig_data)}"
        )

    def _process_rsa_signature(self, sig_data: bytes) -> bytes:
        """Process RSA signature data (both PSS and PKCS1v15).

        :param sig_data: Raw signature data
        :return: Processed signature data
        :raises ValueError: If signature format is invalid
        """
        # For RSA signatures, we expect the signature to be exactly the key size in bytes
        if len(sig_data) == self.signature_length:
            return sig_data

        # Try to handle different signature formats
        try:
            # Check if it's a DER-encoded signature that needs to be extracted
            if len(sig_data) > self.signature_length:
                # For RSA signatures in DER format, we might need to extract the raw signature
                # This is a basic approach - the actual implementation might vary based on the
                # specific DER structure used by your signing tool
                # Basic DER signature extraction (simplified approach)
                # This assumes the signature is at the end of the DER structure
                if len(sig_data) >= self.signature_length:
                    # Try extracting from the end (common for some DER formats)
                    potential_sig = sig_data[-self.signature_length :]
                    return potential_sig

        except Exception as e:
            raise ValueError(f"Failed to process RSA signature: {e}") from e

        raise ValueError(
            f"Got incorrect RSA signature size! "
            f"Expected: {self.signature_length}, actual: {len(sig_data)}"
        )

    def _get_algorithm_display_name(self) -> str:
        """Get display name for the algorithm.

        :return: Human-readable algorithm name
        """
        if self.algorithm == SignatureAlgorithm.ECC:
            return "ECC"
        if self.algorithm == SignatureAlgorithm.RSA_PSS:
            return "RSA-PSS"
        if self.algorithm == SignatureAlgorithm.RSA_PKCS1V15:
            return "RSA-PKCS1v15"
        return "Unknown"

    def sign(self, data: bytes) -> bytes:  # pylint: disable=too-many-branches
        """Perform the signing.

        :param data: Data to sign
        :return: Signature
        """
        data_hash = get_hash(data=data, algorithm=self.hash_alg)
        algorithm_name = self._get_algorithm_display_name()

        print(f"Hash value ({self.hash_alg.label}): {data_hash.hex()}")
        print(f"Algorithm: {algorithm_name}, Key size: {self.key_size} bits")
        if self.hash_alg_override:
            print(f"Hash algorithm: {self.hash_alg.label} (custom override)")
        else:
            print(
                f"Hash algorithm: {self.hash_alg.label} (default for {algorithm_name}-{self.key_size})"
            )

        # Create algorithm-specific hash file name
        full_hash_file_path = f"{self.hash_file}_{self.algorithm.value}.{self.hash_alg.label}"

        try:
            with open(full_hash_file_path, "wb") as f:
                f.write(data_hash)
            print(f"Hash is also stored in file: {full_hash_file_path}")
        except IOError as e:
            print(f"Warning: Could not write hash file {full_hash_file_path}: {e}")

        # Provide algorithm-specific signing instructions
        if self.algorithm == SignatureAlgorithm.ECC:
            print("\nFor ECC signing, use the hash with your ECC private key.")
            print("The signature should be in raw r||s format or DER-encoded format.")
        elif self.algorithm == SignatureAlgorithm.RSA_PSS:
            print("\nFor RSA-PSS signing, use the hash with your RSA private key and PSS padding.")
            print(f"Use {self.hash_alg.label} hash algorithm with PSS padding.")
        elif self.algorithm == SignatureAlgorithm.RSA_PKCS1V15:
            print(
                "\nFor RSA-PKCS1v15 signing, use the hash with your RSA private key and PKCS1v15 padding."
            )
            print(f"Use {self.hash_alg.label} hash algorithm with PKCS1v15 padding.")

        while True:
            sig_file_input = input("\nProvide path to signature file: ")
            try:
                sig_file = self._validate_file_path(sig_file_input)
            except ValueError as e:
                print(f"Error: {e}")
                continue

            try:
                with open(sig_file, "rb") as f:
                    sig_data = f.read()

                print(f"Read signature file: {len(sig_data)} bytes")

                # Process signature based on algorithm type
                if self.algorithm == SignatureAlgorithm.ECC:
                    return self._process_ecc_signature(sig_data)
                if self.algorithm in [
                    SignatureAlgorithm.RSA_PSS,
                    SignatureAlgorithm.RSA_PKCS1V15,
                ]:
                    return self._process_rsa_signature(sig_data)

            except FileNotFoundError:
                print(f"Error: Signature file not found: {sig_file}")
                continue
            except ValueError as e:
                print(f"Error: {e}")
                print("Please check your signature file and try again.")
                continue
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"Unexpected error reading signature file: {e}")
                continue

    @property
    def signature_length(self) -> int:
        """Return length of the signature."""
        return self.sig_size

    @property
    def is_rsa_algorithm(self) -> bool:
        """Check if the current algorithm is RSA-based.

        :return: True if RSA algorithm, False otherwise
        """
        return self.algorithm in [SignatureAlgorithm.RSA_PSS, SignatureAlgorithm.RSA_PKCS1V15]

    @property
    def uses_pss_padding(self) -> bool:
        """Check if the current algorithm uses PSS padding.

        :return: True if PSS padding is used, False otherwise
        """
        return self.algorithm == SignatureAlgorithm.RSA_PSS

    def get_algorithm_info(self) -> dict:
        """Get information about the current algorithm configuration.

        :return: Dictionary with algorithm information
        """
        return {
            "algorithm": self.algorithm.value,
            "algorithm_display": self._get_algorithm_display_name(),
            "key_size": self.key_size,
            "hash_algorithm": self.hash_alg.label,
            "hash_algorithm_override": self.hash_alg_override,
            "signature_length": self.signature_length,
            "is_rsa": self.is_rsa_algorithm,
            "uses_pss_padding": self.uses_pss_padding,
        }

    def get_signing_instructions(self) -> str:
        """Get algorithm-specific signing instructions.

        :return: Signing instructions as string
        """
        if self.algorithm == SignatureAlgorithm.ECC:
            return (
                f"ECC-{self.key_size} signing instructions:\n"
                f"1. Use {self.hash_alg.label} to hash your data\n"
                f"2. Sign the hash with your ECC-{self.key_size} private key\n"
                f"3. Provide signature in raw r||s format ({self.signature_length} bytes) "
                f"or DER-encoded format"
            )
        if self.algorithm == SignatureAlgorithm.RSA_PSS:
            return (
                f"RSA-PSS-{self.key_size} signing instructions:\n"
                f"1. Use {self.hash_alg.label} to hash your data\n"
                f"2. Sign the hash with your RSA-{self.key_size} private key using PSS padding\n"
                f"3. Use salt length equal to digest length\n"
                f"4. Provide signature as raw bytes ({self.signature_length} bytes)"
            )
        if self.algorithm == SignatureAlgorithm.RSA_PKCS1V15:
            return (
                f"RSA-PKCS1v15-{self.key_size} signing instructions:\n"
                f"1. Use {self.hash_alg.label} to hash your data\n"
                f"2. Sign the hash with your RSA-{self.key_size} private key using PKCS1v15 padding\n"
                f"3. Provide signature as raw bytes ({self.signature_length} bytes)"
            )
        return "Unknown algorithm"

    def validate_signature_compatibility(self, signature_data: bytes) -> bool:
        """Validate if signature data is compatible with current algorithm settings.

        :param signature_data: Signature data to validate
        :return: True if compatible, False otherwise
        """
        try:
            if self.algorithm == SignatureAlgorithm.ECC:
                self._process_ecc_signature(signature_data)
                return True
            if self.algorithm in [SignatureAlgorithm.RSA_PSS, SignatureAlgorithm.RSA_PKCS1V15]:
                self._process_rsa_signature(signature_data)
                return True
        except ValueError:
            return False
        return False

    def __str__(self) -> str:
        """String representation of the signature provider."""
        return (
            f"OfflineSP(algorithm={self.algorithm.value}, "
            f"key_size={self.key_size}, "
            f"hash_alg={self.hash_alg.label})"
        )

    def __repr__(self) -> str:
        """Detailed string representation of the signature provider."""
        return (
            f"OfflineSP(hash_file='{self.hash_file}', "
            f"key_size={self.key_size}, "
            f"algorithm='{self.algorithm.value}', "
            f"hash_algorithm='{self.hash_alg.label}')"
        )
