#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""PKCS utilities for handling PKCS5 and PKCS8 encrypted keys."""

import logging
from getpass import getpass

from Crypto.IO import PKCS8
from cryptography.hazmat.decrepit.ciphers import algorithms as decrepit_algorithms
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pyasn1.codec.der.decoder import decode
from pyasn1.codec.der.encoder import encode
from pyasn1.error import PyAsn1Error
from pyasn1.type import namedtype, univ

from spsdk_pqc.errors import PQCError
from spsdk_pqc.pqc_asn import decode_prk

logger = logging.getLogger(__name__)


class AlgorithmIdentifier(univ.Sequence):
    """Algorithm identifier structure.

    AlgorithmIdentifier ::= SEQUENCE {
        algorithm   OBJECT IDENTIFIER,
        parameters  ANY DEFINED BY algorithm OPTIONAL
    }
    """


AlgorithmIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType("algorithm", univ.ObjectIdentifier()),
    namedtype.OptionalNamedType("parameters", univ.Any()),
)


class PBKDF2Params(univ.Sequence):
    """PBKDF2 parameters.

    PBKDF2-params ::= SEQUENCE {
        salt           OCTET STRING,
        iterationCount INTEGER,
        prf            AlgorithmIdentifier OPTIONAL
    }
    """


PBKDF2Params.componentType = namedtype.NamedTypes(
    namedtype.NamedType("salt", univ.OctetString()),
    namedtype.NamedType("iterationCount", univ.Integer()),
    namedtype.OptionalNamedType("prf", AlgorithmIdentifier()),
)


class PBES2Params(univ.Sequence):
    """PBES2 parameters.

    PBES2-params ::= SEQUENCE {
        keyDerivationFunc AlgorithmIdentifier,
        encryptionScheme  AlgorithmIdentifier
    }
    """


PBES2Params.componentType = namedtype.NamedTypes(
    namedtype.NamedType("keyDerivationFunc", AlgorithmIdentifier()),
    namedtype.NamedType("encryptionScheme", AlgorithmIdentifier()),
)


class EncryptedPrivateKeyInfo(univ.Sequence):
    """PKCS#5 EncryptedPrivateKeyInfo structure.

    EncryptedPrivateKeyInfo ::= SEQUENCE {
        encryptionAlgorithm AlgorithmIdentifier,
        encryptedData       OCTET STRING
    }
    """


EncryptedPrivateKeyInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType("encryptionAlgorithm", AlgorithmIdentifier()),
    namedtype.NamedType("encryptedData", univ.OctetString()),
)


# OID constants
OID_PBES2 = "1.2.840.113549.1.5.13"
OID_PBKDF2 = "1.2.840.113549.1.5.12"
OID_DES_EDE3_CBC = "1.2.840.113549.3.7"
OID_HMAC_SHA256 = "1.2.840.113549.2.9"


def unwrap(
    data: bytes, password: str | bytes | None = None
) -> tuple[str, bytes, str | bytes | None]:
    """Unwrap encrypted private key data.

    :param data: DER encoded encrypted private key
    :param password: Password for decryption
    :return: Decrypted private key OID, data and password used for decryption
    :raises PQCError: If parsing or decryption fails
    """
    # First let's try un-encrypted key (CST generates this with .der extension)
    try:
        oid, key_data_decoded = decode_prk(data)
        # re-encode key data, to match PyCryptodome's PKCS8 format
        key_data = encode(univ.OctetString(key_data_decoded))
        return oid, key_data, password
    except (PyAsn1Error, PQCError) as exc:
        logger.info(str(exc))

    # Try PKCS8 first with provided (potentially None/empty) password
    try:
        oid, plain_data = unwrap_pkcs8(data, password=password)
        return oid, plain_data, password
    except PQCError as exc:
        logger.info(str(exc))

    # Try again with PKCS8 and password prompt
    if password is None:
        password = getpass("Enter password for encrypted key: ")
        try:
            oid, plain_data = unwrap_pkcs8(data, password=password)
            return oid, plain_data, password
        except PQCError as exc:
            logger.info(str(exc))

    # Next try PKCS5, here password must be set (either as parameter or from prompt)
    if password is None:
        raise PQCError("Password is required for PKCS5 encoded keys")

    try:
        oid, plain_data = unwrap_pkcs5(data, password=password)
        return oid, plain_data, password
    except (ValueError, PyAsn1Error) as exc:
        logger.error("Failed to unwrap PKCS5 encoded key: %s", str(exc))

    raise PQCError("Unable to unwrap private key")


def unwrap_pkcs8(data: bytes, password: str | bytes | None = None) -> tuple[str, bytes]:
    """Unwrap PKCS8 encrypted private key data.

    :param data: DER encoded encrypted private key
    :param password: Password for decryption
    :return: Private key OID and decrypted data
    :raises PQCError: If parsing or decryption fails
    """
    try:
        oid, plain_data, _ = PKCS8.unwrap(data, passphrase=password)
        return oid, plain_data
    except ValueError as exc:
        raise PQCError(f"Failed to unwrap PKCS8 encoded key: {exc}") from exc


def wrap_pkcs8(private_key_data: bytes, private_key_oid: str, password: str | None = None) -> bytes:
    """Wrap private key data in PKCS8 format with optional password encryption.

    :param private_key_data: DER encoded private key data
    :param private_key_oid: OID of the private key algorithm
    :param password: Optional password for encryption
    :return: DER encoded PKCS8 EncryptedPrivateKeyInfo or PrivateKeyInfo
    """
    # there's a bug in pycryptodome's PKCS8.wrap .pyi, password may be None
    return PKCS8.wrap(private_key_data, private_key_oid, passphrase=password)  # type: ignore


# pylint: disable=too-many-locals
def unwrap_pkcs5(data: bytes, password: str | bytes) -> tuple[str, bytes]:
    """Unwrap PKCS#5 encrypted private key data.

    :param data: DER encoded EncryptedPrivateKeyInfo structure
    :param password: Password for decryption
    :return: Decrypted private key data
    :raises PQCError: If parsing or decryption fails
    """
    try:
        # Decode the EncryptedPrivateKeyInfo structure
        encrypted_key_info, _ = decode(data, asn1Spec=EncryptedPrivateKeyInfo())

        # Extract encryption algorithm and parameters
        enc_alg_oid = str(encrypted_key_info["encryptionAlgorithm"]["algorithm"])
        if enc_alg_oid != OID_PBES2:
            raise PQCError(f"Unsupported encryption algorithm: {enc_alg_oid}")

        # Parse PBES2 parameters
        pbes2_params, _ = decode(
            encrypted_key_info["encryptionAlgorithm"]["parameters"], asn1Spec=PBES2Params()
        )

        # Extract KDF parameters
        kdf_alg = pbes2_params["keyDerivationFunc"]
        kdf_oid = str(kdf_alg["algorithm"])
        if kdf_oid != OID_PBKDF2:
            raise PQCError(f"Unsupported KDF algorithm: {kdf_oid}")

        pbkdf2_params, _ = decode(kdf_alg["parameters"], asn1Spec=PBKDF2Params())
        salt = bytes(pbkdf2_params["salt"])
        iterations = int(pbkdf2_params["iterationCount"])

        # Extract PRF
        if pbkdf2_params["prf"].hasValue():
            prf_alg, _ = decode(encode(pbkdf2_params["prf"]), asn1Spec=AlgorithmIdentifier())
            prf_oid = str(prf_alg["algorithm"])
            if prf_oid != OID_HMAC_SHA256:
                raise PQCError(f"Unsupported HMAC algorithm: {prf_oid}")

        # Extract encryption scheme
        enc_scheme = pbes2_params["encryptionScheme"]
        enc_scheme_oid = str(enc_scheme["algorithm"])
        if enc_scheme_oid != OID_DES_EDE3_CBC:
            raise PQCError(f"Unsupported encryption scheme: {enc_scheme_oid}")

        iv = bytes(univ.OctetString(enc_scheme["parameters"]))

        # Derive key using PBKDF2HMAC
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=24,  # 3DES key length
            salt=salt,
            iterations=iterations,
        )
        key = kdf.derive(password.encode() if isinstance(password, str) else password)

        # Decrypt the private key
        encrypted_data = bytes(encrypted_key_info["encryptedData"])

        # it may happen that IV is encoded in another Octet String
        if len(iv) == decrepit_algorithms.TripleDES.block_size // 8 + 2:
            # Skip the OCTET STRING tag and length
            iv = iv[2:]

        cipher = Cipher(algorithm=decrepit_algorithms.TripleDES(key), mode=modes.CBC(iv))
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()

        # Remove PKCS#7 padding
        padding_length = decrypted_padded[-1]
        if 0 < padding_length <= 8:
            decrypted_data = decrypted_padded[:-padding_length]
        else:
            decrypted_data = decrypted_padded

        oid, key_data_decoded = decode_prk(decrypted_data)

        # re-encode key data, to match PyCryptodome's PKCS8 format
        key_data = encode(univ.OctetString(key_data_decoded))

        return oid, key_data

    except PyAsn1Error as exc:
        raise PQCError(f"Failed to parse encrypted key: {str(exc)}") from exc
    except Exception as exc:
        raise PQCError("Failed to decrypt key. Maybe the password is invalid") from exc
