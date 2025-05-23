#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""ASN.1 encoding/decoding of PQC keys."""


import base64

from pyasn1.codec.der.decoder import decode
from pyasn1.codec.der.encoder import encode
from pyasn1.error import PyAsn1Error
from pyasn1.type import namedtype, univ

from spsdk_pqc.errors import PQCError


class KeyInfo(univ.Sequence):
    """Information about the key.

    KeyInfo ::= SEQUENCE {
        algorithm      OBJECT IDENTIFIER,
        parameter      ANY DEFINED BY algorithm OPTIONAL
    }
    """


KeyInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType("algorithm", univ.ObjectIdentifier()),
    namedtype.OptionalNamedType("parameter", univ.Any()),
)


class PrivateKey(univ.OctetString):
    """Raw private key data.

    PrivateKey ::= OCTET STRING
    """


class PrivateKeyWithSeed(univ.Sequence):
    """Private key with seed.

    PrivateKeyWithSeed ::= SEQUENCE {
        seed    OCTET STRING,
        prk     OCTET STRING
    }
    """


PrivateKeyWithSeed.componentType = namedtype.NamedTypes(
    namedtype.NamedType("seed", univ.OctetString()),
    namedtype.NamedType("prk", univ.OctetString()),
)


class PrivateKeyEnvelope(univ.Sequence):
    """Encoded envelope for private key.

    PrivateKeyEnvelope ::= SEQUENCE {
        version        INTEGER,
        info           KeyInfo,
        prkData        CHOICE {
            prk	PrivateKey,
            prkSeed PrivateKeyWithSeed
        }
    }
    """


PrivateKeyEnvelope.componentType = namedtype.NamedTypes(
    namedtype.NamedType("version", univ.Integer()),
    namedtype.NamedType("info", KeyInfo()),
    namedtype.NamedType(
        "prkData",
        univ.Choice(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType("prk", PrivateKey()),
                namedtype.NamedType("prkSeed", PrivateKeyWithSeed()),
            )
        ),
    ),
)


class PublicKey(univ.BitString):
    """Raw public key data.

    PublicKey ::= BIT STRING
    """


class PublicKeyEnvelope(univ.Sequence):
    """Encoded envelope for public key.

    PublicKeyEnvelope ::= SEQUENCE {
       info           KeyInfo,
        puk            PublicKey
    }
    """


PublicKeyEnvelope.componentType = namedtype.NamedTypes(
    namedtype.NamedType("info", KeyInfo()),
    namedtype.NamedType("puk", PublicKey()),
)


def decode_puk(data: bytes) -> tuple[str, bytes]:
    """Decode public key from PEM/DER encoded data."""
    try:
        data = pem_2_der(data=data)
        result, _ = decode(data, asn1Spec=PublicKeyEnvelope())
        info = str(result["info"]["algorithm"])
        puk = result["puk"].asOctets()
        return info, bytes(puk)
    except PyAsn1Error as exc:
        raise PQCError(str(exc)) from exc


def encode_puk(data: bytes, oid: str, pem: bool = True, algorithm_name: str = "PQC") -> bytes:
    """Encode public key to PEM/DER format."""
    try:
        key_data = {
            "info": {
                "algorithm": univ.ObjectIdentifier(oid),
                "parameter": bytes(),
            },
            "puk": univ.BitString(hexValue=data.hex()),
        }
        key = bytes(encode(key_data, asn1Spec=PublicKeyEnvelope()))
        if pem:
            return der_2_pem(data=key, private=False, algorithm=algorithm_name)
        return key
    except PyAsn1Error as exc:
        raise PQCError(str(exc)) from exc


def decode_prk(data: bytes) -> tuple[str, bytes]:
    """Decode private key from PEM/DER encoded data."""
    try:
        data = pem_2_der(data=data)
        result, _ = decode(data, asn1Spec=PrivateKeyEnvelope())
        info = str(result["info"]["algorithm"])
        prk_component = result["prkData"].getComponent()
        try:
            result2, _ = decode(prk_component, asn1Spec=PrivateKey())
            return info, bytes(result2)
        except PyAsn1Error:
            pass
        result2, _ = decode(prk_component, asn1Spec=PrivateKeyWithSeed())
        return info, bytes(result2["prk"])
    except PyAsn1Error as exc:
        raise PQCError(str(exc)) from exc


def encode_prk(data: bytes, oid: str, pem: bool = True, algorithm_name: str = "PQC") -> bytes:
    """Encode private key to PEM/DER format."""
    try:
        key_data = {
            "version": univ.Integer(0),
            "info": {
                "algorithm": univ.ObjectIdentifier(oid),
                "parameter": bytes(),
            },
            "prkData": {
                "prk": univ.OctetString(encode(PrivateKey(data))),
            },
        }
        key = bytes(encode(key_data, asn1Spec=PrivateKeyEnvelope()))
        if pem:
            return der_2_pem(data=key, private=True, algorithm=algorithm_name)
        return key
    except PyAsn1Error as exc:
        raise PQCError(str(exc)) from exc


def pem_2_der(data: bytes) -> bytes:
    """Transform PEM encoding to DER."""
    lines = data.splitlines()
    if lines[0].startswith(b"-----") and lines[-1].startswith(b"-----"):
        inner_data = b"".join(lines[1:-1])
        return base64.b64decode(inner_data)
    return data


def der_2_pem(data: bytes, private: bool, algorithm: str) -> bytes:
    """Transform DER encoding to PEM."""
    b64_data = base64.b64encode(data)
    inner_text = f"{algorithm.upper()} {'PRIVATE' if private else 'PUBLIC'}"
    lines = []
    lines.append(f"-----BEGIN {inner_text} KEY-----".encode("utf-8"))
    lines.extend([b64_data[i : i + 64] for i in range(0, len(b64_data), 64)])
    lines.append(f"-----END {inner_text} KEY-----".encode("utf-8"))
    return b"\n".join(lines) + b"\n"
