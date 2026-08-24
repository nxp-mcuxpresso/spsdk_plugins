#!/usr/bin/env python
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Tests for ML-DSA migration CLI."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from click.testing import CliRunner
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from pyasn1.codec.der.encoder import encode as asn1_encode
from pyasn1.type import univ as asn1_univ

from spsdk_pqc.__main__ import main
from spsdk_pqc.pqc_asn import KeyInfo, PrivateKeyEnvelope, PrivateKeyWithSeed, PublicKeyEnvelope
from spsdk_pqc.wrapper import MLDSAPrivateKey, PQCAlgorithm

mldsa = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.mldsa")
MLDSA65PrivateKey = mldsa.MLDSA65PrivateKey
MLDSA65PublicKey = mldsa.MLDSA65PublicKey


def _legacy_seed_private_key() -> bytes:
    """Create a legacy seed-bearing ML-DSA private key."""
    private_key = MLDSA65PrivateKey.generate()
    raw_public = private_key.public_key().public_bytes_raw()

    key_info = KeyInfo()
    key_info.setComponentByName("algorithm", asn1_univ.ObjectIdentifier("1.3.6.1.4.1.2.267.12.6.5"))

    private_with_seed = PrivateKeyWithSeed()
    private_with_seed.setComponentByName("seed", private_key.private_bytes_raw())
    private_with_seed.setComponentByName("prk", private_key.private_bytes_raw() + raw_public)

    legacy_private = PrivateKeyEnvelope()
    legacy_private.setComponentByName("version", 0)
    legacy_private.setComponentByName("info", key_info)
    prk_data = legacy_private.getComponentByName("prkData")
    prk_data.setComponentByName("prkSeed", private_with_seed)
    legacy_private.setComponentByName("prkData", prk_data)

    legacy_der = asn1_encode(legacy_private)
    return (
        b"-----BEGIN ML-DSA-65 PRIVATE KEY-----\n"
        + base64.b64encode(legacy_der)
        + b"\n-----END ML-DSA-65 PRIVATE KEY-----\n"
    )


def _legacy_public_key() -> bytes:
    """Create a legacy ML-DSA public key envelope."""
    public_key = MLDSA65PrivateKey.generate().public_key().public_bytes_raw()

    key_info = KeyInfo()
    key_info.setComponentByName("algorithm", asn1_univ.ObjectIdentifier("1.3.6.1.4.1.2.267.12.6.5"))

    legacy_public = PublicKeyEnvelope()
    legacy_public.setComponentByName("info", key_info)
    legacy_public.setComponentByName("puk", asn1_univ.BitString(hexValue=public_key.hex()))

    legacy_der = asn1_encode(legacy_public)
    return (
        b"-----BEGIN ML-DSA-65 PUBLIC KEY-----\n"
        + base64.b64encode(legacy_der)
        + b"\n-----END ML-DSA-65 PUBLIC KEY-----\n"
    )


def test_migrate_key_rejects_expanded_secret_private(tmp_path: Path) -> None:
    """Expanded-secret ML-DSA private keys should be detected but not converted."""
    key_path = tmp_path / "legacy-expanded.pem"
    output_path = tmp_path / "converted.pem"
    key_path.write_bytes(MLDSAPrivateKey(algorithm=PQCAlgorithm.ML_DSA_65).export())

    runner = CliRunner()
    result = runner.invoke(main, ["migrate-key", "-k", str(key_path), "-o", str(output_path)])

    assert result.exit_code == 1
    assert "Detected format: legacy-expanded-private" in result.output
    assert "Convertible: no" in result.output
    assert "cannot be converted" in result.output
    assert not output_path.exists()


def test_migrate_key_converts_seed_private(tmp_path: Path) -> None:
    """Seed-bearing legacy ML-DSA private keys should convert to native PKCS#8."""
    key_path = tmp_path / "legacy-seed.pem"
    output_path = tmp_path / "converted.pem"
    key_path.write_bytes(_legacy_seed_private_key())

    runner = CliRunner()
    result = runner.invoke(main, ["migrate-key", "-k", str(key_path), "-o", str(output_path)])

    assert result.exit_code == 0
    assert "Detected format: legacy-seed-private" in result.output
    converted_key = load_pem_private_key(output_path.read_bytes(), None)
    assert isinstance(converted_key, MLDSA65PrivateKey)


def test_migrate_key_converts_legacy_public(tmp_path: Path) -> None:
    """Legacy ML-DSA public keys should convert to native SubjectPublicKeyInfo."""
    key_path = tmp_path / "legacy-public.pem"
    output_path = tmp_path / "converted.pub"
    key_path.write_bytes(_legacy_public_key())

    runner = CliRunner()
    result = runner.invoke(main, ["migrate-key", "-k", str(key_path), "-o", str(output_path)])

    assert result.exit_code == 0
    assert "Detected format: legacy-public" in result.output
    converted_key = load_pem_public_key(output_path.read_bytes())
    assert isinstance(converted_key, MLDSA65PublicKey)
