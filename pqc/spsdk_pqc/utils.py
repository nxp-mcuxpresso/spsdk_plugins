#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Various utilities used throughout the plugin."""

from getpass import getpass
from typing import Optional, no_type_check

from Crypto.IO import PEM, PKCS8
from Crypto.Util import asn1
from spsdk.crypto.keys import PrivateKey, PrivateKeyEcc, PublicKeyEcc, SPSDKEncoding

from spsdk_pqc.wrapper import DilithiumPrivateKey, MLDSAPrivateKey, PQCPrivateKey, PQCPublicKey

CLASSIC_FIRST_OIDS = [
    "1.3.9999.2.7.1",  # p256_dilithium2
    "1.3.9999.2.7.3",  # p384_dilithium3
    "1.3.9999.2.7.4",  # p521_dilithium5
    "1.3.9999.7.1",  # p256_mldsa44
    "1.3.9999.7.3",  # p384_mldsa65
    "1.3.9999.7.4",  # p521_mldsa87
    "1.3.9999.7.5",  # p256_mldsa44
    "1.3.9999.7.7",  # p384_mldsa65
    "1.3.9999.7.8",  # p521_mldsa87
]

DILITHIUM_LEVEL_OID = {
    2: "1.3.9999.2.7.1",  # p256_dilithium2
    3: "1.3.9999.2.7.3",  # p384_dilithium3
    5: "1.3.9999.2.7.4",  # p521_dilithium5
}

MLDSA_FIRST_OIDS = [
    "2.16.840.1.114027.80.8.1.4",  # mldsa44_p256
    "2.16.840.1.114027.80.8.1.8",  # mldsa65_p256
    "2.16.840.1.114027.80.8.1.11",  # mldsa87_p384
]

MLDSA_LEVEL_OID = {
    2: "2.16.840.1.114027.80.8.1.4",  # mldsa44_p256
    3: "2.16.840.1.114027.80.8.1.8",  # mldsa65_p256
    5: "2.16.840.1.114027.80.8.1.11",  # mldsa87_p384
}


def unwrap_pkcs8(data: bytes, password: Optional[str] = None) -> tuple[str, bytes, Optional[str]]:
    """Unwrap PKCS8 encoded private key with optional password."""
    try:
        result = PKCS8.unwrap(data, passphrase=password)
        return result[0], result[1], password
    except ValueError:
        pass
    password = getpass("Password to encrypted private key: ")
    result = PKCS8.unwrap(data, passphrase=password)
    return result[0], result[1], password


@no_type_check  # mypy is super confused by pycryptodome
def split_hybrid_key(
    data: bytes, password: Optional[str] = None
) -> tuple[PrivateKey, PQCPrivateKey, Optional[str]]:
    """Split hybrid key into classic and PQC private keys.

    This function unwraps a PKCS8 encoded hybrid key and extracts the individual private keys.
    """
    der_data, *_ = PEM.decode(data.decode("utf-8"))
    oid, plain_data, password = unwrap_pkcs8(der_data, password=password)
    if oid in CLASSIC_FIRST_OIDS:
        prk_data = asn1.DerOctetString().decode(plain_data).payload
        offset_bytes, prk_data = prk_data[:4], prk_data[4:]
        pqc_key_offset = int.from_bytes(offset_bytes, byteorder="big")
        classic = PrivateKey.parse(prk_data)
        if not test_key(classic):
            raise ValueError("Sanity check for legacy key failed")
        pqc = PQCPrivateKey.parse(prk_data[pqc_key_offset:])
        if not test_key(pqc):
            raise ValueError("Sanity check for pqc key failed")
        return classic, pqc, password

    if oid in MLDSA_FIRST_OIDS:
        seq = asn1.DerSequence().decode(plain_data)
        if len(seq) != 2:
            raise ValueError("Invalid MLDSA hybrid key structure")
        assert seq[0] and seq[1]
        classic = PrivateKey.parse(seq[1])
        if not test_key(classic):
            raise ValueError("Sanity check for legacy key failed")
        pqc = PQCPrivateKey.parse(seq[0])
        if not test_key(pqc):
            raise ValueError("Sanity check for pqc key failed")
        return classic, pqc, password

    raise ValueError(f"Unsupported Hybrid key OID: {oid}")


@no_type_check  # mypy is super confused by pycryptodome
def combine_hybrid_key(
    classic_prk: PrivateKeyEcc, pqc_prk: PQCPrivateKey, password: Optional[str] = None
) -> bytes:
    """Combine classic and PQC private keys into a hybrid key.

    This function creates a PKCS8 encoded hybrid key from individual private keys.
    """
    oid = check_compatibility(classic=classic_prk, pqc=pqc_prk)
    if oid in CLASSIC_FIRST_OIDS:
        classic_key_data = classic_prk.export(encoding=SPSDKEncoding.DER)
        inner_data = len(classic_key_data).to_bytes(length=4, byteorder="big")
        inner_data += classic_key_data
        inner_data += pqc_prk.private_data
        if pqc_prk.public_data:
            inner_data += pqc_prk.public_data
        inner_os = asn1.DerOctetString(inner_data).encode()
        # wrap does accepts None as password
        return PKCS8.wrap(
            private_key=inner_os,
            key_oid=oid,
            passphrase=password,
        )
    if oid in MLDSA_FIRST_OIDS:
        inner_seq = asn1.DerSequence(
            [
                pqc_prk.export(pem=False),
                classic_prk.export(encoding=SPSDKEncoding.DER),
            ]
        )
        inner_data = inner_seq.encode()
        return PKCS8.wrap(private_key=inner_data, key_oid=oid, passphrase=password)

    raise ValueError(f"Unsupported hybrid type (classic {type(classic_prk)} ,PQC {type(pqc_prk)})")


def check_compatibility(classic: PrivateKeyEcc, pqc: PQCPrivateKey) -> str:
    """Check if ECC and PQC keys are compatible for a hybrid/composite key."""
    if isinstance(pqc, DilithiumPrivateKey):
        assert isinstance(pqc, DilithiumPrivateKey)
        # pylint: disable=too-many-boolean-expressions
        if (
            (classic.key_size == 256 and pqc.level != 2)
            or (classic.key_size == 384 and pqc.level != 3)
            or (classic.key_size == 521 and pqc.level != 5)
        ):
            raise ValueError(f"Can't combine {type(classic)} and {type(pqc)}")
        return DILITHIUM_LEVEL_OID[pqc.level]

    if isinstance(pqc, MLDSAPrivateKey):
        if classic.key_size == 256 and pqc.level in [2, 3]:
            return MLDSA_LEVEL_OID[pqc.level]
        if classic.key_size == 384:
            if pqc.level == 3:
                return "1.3.9999.7.7"
            if pqc.level == 5:
                return MLDSA_LEVEL_OID[5]
        if classic.key_size == 521:
            if pqc.level == 5:
                return "1.3.9999.7.8"
        raise ValueError(f"Can't combine {repr(classic)} and {repr(pqc)}")

    raise ValueError(f"Unsupported hybrid type (classic {repr(classic)} ,PQC {repr(pqc)})")


def test_key(private_key: PrivateKey) -> bool:
    """Simple key test using sign-verify."""
    message = b"sample message"
    sign = private_key.sign(data=message)
    public_key = private_key.get_public_key()
    if isinstance(public_key, PublicKeyEcc):
        return public_key.verify_signature(sign, message)
    if isinstance(public_key, PQCPublicKey):
        return public_key.verify(sign, message)
    raise ValueError(f"Unsupported key type: {type(public_key)}")
