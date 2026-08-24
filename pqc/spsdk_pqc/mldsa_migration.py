#!/usr/bin/env python
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Helpers for inspecting and converting ML-DSA keys to native cryptography format."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING, Any, TypeAlias, TypeGuard, cast

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_der_private_key,
    load_der_public_key,
    load_pem_private_key,
    load_pem_public_key,
)
from pyasn1.codec.der.decoder import decode
from pyasn1.error import PyAsn1Error

from spsdk_pqc import pqc_asn
from spsdk_pqc.errors import PQCError
from spsdk_pqc.wrapper import KEY_INFO, PQCAlgorithm

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.mldsa import (
        MLDSA44PrivateKey,
        MLDSA44PublicKey,
        MLDSA65PrivateKey,
        MLDSA65PublicKey,
        MLDSA87PrivateKey,
        MLDSA87PublicKey,
    )

    MLDSAPrivateKeyClass: TypeAlias = type[
        MLDSA44PrivateKey | MLDSA65PrivateKey | MLDSA87PrivateKey
    ]
    MLDSAPublicKeyClass: TypeAlias = type[MLDSA44PublicKey | MLDSA65PublicKey | MLDSA87PublicKey]
    MLDSAPrivateKeyType: TypeAlias = MLDSA44PrivateKey | MLDSA65PrivateKey | MLDSA87PrivateKey
    MLDSAPublicKeyType: TypeAlias = MLDSA44PublicKey | MLDSA65PublicKey | MLDSA87PublicKey
    MLDSAKeyType: TypeAlias = MLDSAPrivateKeyType | MLDSAPublicKeyType
else:
    MLDSAPrivateKeyClass: TypeAlias = type[Any]
    MLDSAPublicKeyClass: TypeAlias = type[Any]
    MLDSAPrivateKeyType: TypeAlias = Any
    MLDSAPublicKeyType: TypeAlias = Any
    MLDSAKeyType: TypeAlias = Any

MLDSA_UNSUPPORTED_REASON = (
    "Native ML-DSA conversion requires cryptography with ML-DSA support. "
    "Install a newer cryptography version that provides "
    "'cryptography.hazmat.primitives.asymmetric.mldsa'."
)


@dataclass
class _NativeMLDSAClassCache:
    """Cache for optional native ML-DSA classes from cryptography."""

    initialized: bool = False
    private_key_classes: dict[int, MLDSAPrivateKeyClass] = field(default_factory=dict)
    public_key_classes: dict[int, MLDSAPublicKeyClass] = field(default_factory=dict)


_MLDSA_CLASS_CACHE = _NativeMLDSAClassCache()


def _load_mldsa_module() -> ModuleType | None:
    """Import cryptography ML-DSA module when available."""
    try:
        return import_module("cryptography.hazmat.primitives.asymmetric.mldsa")
    except ImportError:
        return None


def _init_native_mldsa_classes() -> None:
    """Initialize ML-DSA class mappings lazily to support older cryptography versions."""
    if _MLDSA_CLASS_CACHE.initialized:
        return
    _MLDSA_CLASS_CACHE.initialized = True

    module = _load_mldsa_module()
    if module is None:
        return

    try:
        _MLDSA_CLASS_CACHE.private_key_classes = {
            2: cast(MLDSAPrivateKeyClass, module.MLDSA44PrivateKey),
            3: cast(MLDSAPrivateKeyClass, module.MLDSA65PrivateKey),
            5: cast(MLDSAPrivateKeyClass, module.MLDSA87PrivateKey),
        }
        _MLDSA_CLASS_CACHE.public_key_classes = {
            2: cast(MLDSAPublicKeyClass, module.MLDSA44PublicKey),
            3: cast(MLDSAPublicKeyClass, module.MLDSA65PublicKey),
            5: cast(MLDSAPublicKeyClass, module.MLDSA87PublicKey),
        }
    except AttributeError:
        _MLDSA_CLASS_CACHE.private_key_classes = {}
        _MLDSA_CLASS_CACHE.public_key_classes = {}


def _get_private_key_classes() -> dict[int, MLDSAPrivateKeyClass]:
    """Return native ML-DSA private-key classes by level."""
    _init_native_mldsa_classes()
    return _MLDSA_CLASS_CACHE.private_key_classes


def _get_public_key_classes() -> dict[int, MLDSAPublicKeyClass]:
    """Return native ML-DSA public-key classes by level."""
    _init_native_mldsa_classes()
    return _MLDSA_CLASS_CACHE.public_key_classes


def _native_mldsa_supported() -> bool:
    """Return whether cryptography provides native ML-DSA support."""
    return bool(_get_private_key_classes()) and bool(_get_public_key_classes())


MLDSA_ALGORITHM_LABELS = {
    2: "ML-DSA-44",
    3: "ML-DSA-65",
    5: "ML-DSA-87",
}
MLDSA_STANDARD_OIDS = {
    "2.16.840.1.101.3.4.3.17": 2,
    "2.16.840.1.101.3.4.3.18": 3,
    "2.16.840.1.101.3.4.3.19": 5,
}
MLDSA_LEGACY_OIDS = {
    "1.3.6.1.4.1.2.267.12.4.4": 2,
    "1.3.6.1.4.1.2.267.12.6.5": 3,
    "1.3.6.1.4.1.2.267.12.8.7": 5,
}
MLDSA_OIDS = MLDSA_STANDARD_OIDS | MLDSA_LEGACY_OIDS
MLDSA_ALGORITHM_TO_LEVEL = {label: level for level, label in MLDSA_ALGORITHM_LABELS.items()}
MLDSA_PRIVATE_LENGTHS = {
    KEY_INFO[PQCAlgorithm.ML_DSA_44].private_key_size: 2,
    KEY_INFO[PQCAlgorithm.ML_DSA_65].private_key_size: 3,
    KEY_INFO[PQCAlgorithm.ML_DSA_87].private_key_size: 5,
}
MLDSA_PRIVATE_WITH_PUBLIC_LENGTHS = {
    KEY_INFO[PQCAlgorithm.ML_DSA_44].data_size: 2,
    KEY_INFO[PQCAlgorithm.ML_DSA_65].data_size: 3,
    KEY_INFO[PQCAlgorithm.ML_DSA_87].data_size: 5,
}
MLDSA_PUBLIC_LENGTHS = {
    KEY_INFO[PQCAlgorithm.ML_DSA_44].public_key_size: 2,
    KEY_INFO[PQCAlgorithm.ML_DSA_65].public_key_size: 3,
    KEY_INFO[PQCAlgorithm.ML_DSA_87].public_key_size: 5,
}


@dataclass(frozen=True)
class MLDSAKeyMigrationInfo:
    """Description of an ML-DSA key migration outcome."""

    format_name: str
    level: int | None
    is_private: bool
    is_convertible: bool
    reason: str
    requires_algorithm: bool = False

    @property
    def algorithm(self) -> str | None:
        """Return human-readable ML-DSA algorithm name."""
        if self.level is None:
            return None
        return MLDSA_ALGORITHM_LABELS[self.level]


def _normalize_mldsa_pem(data: bytes) -> bytes:
    """Normalize ML-DSA-specific PEM labels to generic PKCS#8/SPKI labels."""
    normalized = data
    for level in ("44", "65", "87"):
        normalized = (
            normalized.replace(
                f"-----BEGIN ML-DSA-{level} PRIVATE KEY-----".encode(),
                b"-----BEGIN PRIVATE KEY-----",
            )
            .replace(
                f"-----END ML-DSA-{level} PRIVATE KEY-----".encode(), b"-----END PRIVATE KEY-----"
            )
            .replace(
                f"-----BEGIN ML-DSA-{level} PUBLIC KEY-----".encode(), b"-----BEGIN PUBLIC KEY-----"
            )
            .replace(
                f"-----END ML-DSA-{level} PUBLIC KEY-----".encode(), b"-----END PUBLIC KEY-----"
            )
        )
    return normalized


def _is_mldsa_private_key(key: object) -> TypeGuard[MLDSAPrivateKeyType]:
    """Check whether a key is a native ML-DSA private key."""
    return any(isinstance(key, key_cls) for key_cls in _get_private_key_classes().values())


def _is_mldsa_public_key(key: object) -> TypeGuard[MLDSAPublicKeyType]:
    """Check whether a key is a native ML-DSA public key."""
    return any(isinstance(key, key_cls) for key_cls in _get_public_key_classes().values())


def _get_private_level(key: MLDSAPrivateKeyType) -> int:
    """Return level for native ML-DSA private key."""
    return next(
        level for level, key_cls in _get_private_key_classes().items() if isinstance(key, key_cls)
    )


def _get_public_level(key: MLDSAPublicKeyType) -> int:
    """Return level for native ML-DSA public key."""
    return next(
        level for level, key_cls in _get_public_key_classes().items() if isinstance(key, key_cls)
    )


def _load_native_private_key(data: bytes) -> MLDSAPrivateKeyType | None:
    """Load a native ML-DSA private key with cryptography if possible."""
    normalized = _normalize_mldsa_pem(data)
    try:
        loaded = (
            load_pem_private_key(normalized, None)
            if normalized.startswith(b"-----BEGIN ")
            else load_der_private_key(normalized, None)
        )
    except (UnsupportedAlgorithm, TypeError, ValueError):
        return None
    if _is_mldsa_private_key(loaded):
        return loaded
    return None


def _load_native_public_key(data: bytes) -> MLDSAPublicKeyType | None:
    """Load a native ML-DSA public key with cryptography if possible."""
    normalized = _normalize_mldsa_pem(data)
    try:
        loaded = (
            load_pem_public_key(normalized)
            if normalized.startswith(b"-----BEGIN ")
            else load_der_public_key(normalized)
        )
    except (UnsupportedAlgorithm, TypeError, ValueError):
        return None
    if _is_mldsa_public_key(loaded):
        return loaded
    return None


def _get_level_from_oid(oid: str) -> int:
    """Translate an ML-DSA OID into the NIST security level."""
    try:
        return MLDSA_OIDS[oid]
    except KeyError as exc:
        raise PQCError(f"Unsupported ML-DSA OID: {oid}") from exc


def _get_level_from_algorithm(algorithm: str | None) -> int | None:
    """Translate algorithm name from CLI to NIST security level."""
    if algorithm is None:
        return None
    try:
        return MLDSA_ALGORITHM_TO_LEVEL[algorithm.upper()]
    except KeyError as exc:
        raise PQCError(f"Unsupported ML-DSA algorithm override: {algorithm}") from exc


def _inspect_legacy_private_key(data: bytes) -> tuple[MLDSAKeyMigrationInfo, bytes] | None:
    """Inspect a legacy ML-DSA private-key envelope."""
    try:
        envelope, _ = decode(pqc_asn.pem_2_der(data), asn1Spec=pqc_asn.PrivateKeyEnvelope())
        level = _get_level_from_oid(str(envelope["info"]["algorithm"]))
        private_component = envelope["prkData"].getComponent()
        try:
            if isinstance(private_component, pqc_asn.PrivateKey):
                expanded_key = private_component
            else:
                expanded_key, _ = decode(bytes(private_component), asn1Spec=pqc_asn.PrivateKey())
            return (
                MLDSAKeyMigrationInfo(
                    format_name="legacy-expanded-private",
                    level=level,
                    is_private=True,
                    is_convertible=False,
                    reason=(
                        "Expanded-secret legacy ML-DSA private keys cannot be converted to native "
                        "cryptography format automatically. Regenerate the keypair."
                    ),
                ),
                bytes(expanded_key),
            )
        except (PyAsn1Error, TypeError):
            if isinstance(private_component, pqc_asn.PrivateKeyWithSeed):
                private_with_seed = private_component
            else:
                private_with_seed, _ = decode(
                    bytes(private_component), asn1Spec=pqc_asn.PrivateKeyWithSeed()
                )
            return (
                MLDSAKeyMigrationInfo(
                    format_name="legacy-seed-private",
                    level=level,
                    is_private=True,
                    is_convertible=_native_mldsa_supported(),
                    reason=(
                        "Seed-bearing legacy ML-DSA private key can be converted to native format."
                        if _native_mldsa_supported()
                        else MLDSA_UNSUPPORTED_REASON
                    ),
                ),
                bytes(private_with_seed["seed"]),
            )
    except (PyAsn1Error, ValueError, PQCError):
        return None


def _inspect_legacy_public_key(data: bytes) -> tuple[MLDSAKeyMigrationInfo, bytes] | None:
    """Inspect a legacy ML-DSA public-key envelope."""
    try:
        oid, public_data = pqc_asn.decode_puk(data)
        level = _get_level_from_oid(oid)
        return (
            MLDSAKeyMigrationInfo(
                format_name="legacy-public",
                level=level,
                is_private=False,
                is_convertible=_native_mldsa_supported(),
                reason=(
                    "Legacy ML-DSA public key can be converted to native SubjectPublicKeyInfo."
                    if _native_mldsa_supported()
                    else MLDSA_UNSUPPORTED_REASON
                ),
            ),
            public_data,
        )
    except PQCError:
        return None


def inspect_mldsa_key(data: bytes, algorithm: str | None = None) -> MLDSAKeyMigrationInfo:
    """Classify an ML-DSA key and determine whether native conversion is possible."""
    native_private = _load_native_private_key(data)
    if native_private:
        return MLDSAKeyMigrationInfo(
            format_name="native-private",
            level=_get_private_level(native_private),
            is_private=True,
            is_convertible=True,
            reason="Key is already in native ML-DSA private-key format.",
        )

    native_public = _load_native_public_key(data)
    if native_public:
        return MLDSAKeyMigrationInfo(
            format_name="native-public",
            level=_get_public_level(native_public),
            is_private=False,
            is_convertible=True,
            reason="Key is already in native ML-DSA public-key format.",
        )

    legacy_private = _inspect_legacy_private_key(data)
    if legacy_private:
        return legacy_private[0]

    legacy_public = _inspect_legacy_public_key(data)
    if legacy_public:
        return legacy_public[0]

    if len(data) in MLDSA_PRIVATE_LENGTHS or len(data) in MLDSA_PRIVATE_WITH_PUBLIC_LENGTHS:
        level = MLDSA_PRIVATE_LENGTHS.get(
            len(data), MLDSA_PRIVATE_WITH_PUBLIC_LENGTHS.get(len(data))
        )
        return MLDSAKeyMigrationInfo(
            format_name="raw-expanded-private",
            level=level,
            is_private=True,
            is_convertible=False,
            reason=(
                "Raw expanded-secret ML-DSA private keys cannot be converted to native cryptography "
                "format automatically. Regenerate the keypair."
            ),
        )

    if len(data) in MLDSA_PUBLIC_LENGTHS:
        level = _get_level_from_algorithm(algorithm)
        is_convertible = level is not None and _native_mldsa_supported()
        return MLDSAKeyMigrationInfo(
            format_name="raw-public",
            level=level,
            is_private=False,
            is_convertible=is_convertible,
            reason=(
                "Raw ML-DSA public key requires --algorithm to resolve its security level."
                if level is None
                else (
                    "Raw ML-DSA public key can be converted with the provided algorithm."
                    if is_convertible
                    else MLDSA_UNSUPPORTED_REASON
                )
            ),
            requires_algorithm=level is None,
        )

    raise PQCError("Unable to recognize the input as an ML-DSA key supported by migrate-key.")


def _export_native_key(key: MLDSAKeyType, encoding: str) -> bytes:
    """Export a native ML-DSA key in PEM or DER encoding."""
    output_encoding = Encoding.PEM if encoding == "PEM" else Encoding.DER
    if _is_mldsa_private_key(key):
        return key.private_bytes(
            encoding=output_encoding,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )
    assert _is_mldsa_public_key(key)
    return key.public_bytes(encoding=output_encoding, format=PublicFormat.SubjectPublicKeyInfo)


def convert_mldsa_key(data: bytes, encoding: str, algorithm: str | None = None) -> bytes:
    """Convert a supported ML-DSA key into native cryptography encoding."""
    native_private = _load_native_private_key(data)
    if native_private:
        return _export_native_key(native_private, encoding)

    native_public = _load_native_public_key(data)
    if native_public:
        return _export_native_key(native_public, encoding)

    legacy_private = _inspect_legacy_private_key(data)
    if legacy_private:
        info, private_data = legacy_private
        if not info.is_convertible:
            raise PQCError(info.reason)
        assert info.level is not None
        native_private_key = _get_private_key_classes()[info.level].from_seed_bytes(private_data)
        return _export_native_key(native_private_key, encoding)

    legacy_public = _inspect_legacy_public_key(data)
    if legacy_public:
        info, public_data = legacy_public
        if not info.is_convertible:
            raise PQCError(info.reason)
        assert info.level is not None
        native_public_key = _get_public_key_classes()[info.level].from_public_bytes(public_data)
        return _export_native_key(native_public_key, encoding)

    if len(data) in MLDSA_PUBLIC_LENGTHS:
        level = _get_level_from_algorithm(algorithm)
        if level is None:
            raise PQCError("Raw ML-DSA public key conversion requires --algorithm.")
        if not _native_mldsa_supported():
            raise PQCError(MLDSA_UNSUPPORTED_REASON)
        if MLDSA_PUBLIC_LENGTHS[len(data)] != level:
            raise PQCError(
                f"Raw key length {len(data)} does not match the requested algorithm {algorithm}."
            )
        native_public_key = _get_public_key_classes()[level].from_public_bytes(data)
        return _export_native_key(native_public_key, encoding)

    raw_private = inspect_mldsa_key(data)
    if raw_private.is_private and not raw_private.is_convertible:
        raise PQCError(raw_private.reason)
    raise PQCError("Unable to convert the provided key.")
