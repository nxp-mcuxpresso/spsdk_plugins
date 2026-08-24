#!/usr/bin/env python
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Compatibility tests for ML-DSA migration command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from spsdk_pqc import mldsa_migration
from spsdk_pqc.__main__ import main
from spsdk_pqc.wrapper import KEY_INFO, PQCAlgorithm


def test_migrate_key_without_native_mldsa_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Report missing native support when conversion needs cryptography ML-DSA classes."""
    key_path = tmp_path / "raw.pub"
    output_path = tmp_path / "converted.pub"
    key_path.write_bytes(bytes(KEY_INFO[PQCAlgorithm.ML_DSA_65].public_key_size))

    monkeypatch.setattr(mldsa_migration, "_native_mldsa_supported", lambda: False)

    runner = CliRunner()
    inspect_result = runner.invoke(
        main,
        ["migrate-key", "-k", str(key_path), "-a", "ML-DSA-65"],
    )

    assert inspect_result.exit_code == 0
    assert "Detected format: raw-public" in inspect_result.output
    assert "Convertible: no" in inspect_result.output
    assert (
        "Native ML-DSA conversion requires cryptography with ML-DSA support."
        in inspect_result.output
    )

    convert_result = runner.invoke(
        main,
        ["migrate-key", "-k", str(key_path), "-a", "ML-DSA-65", "-o", str(output_path)],
    )

    assert convert_result.exit_code == 1
    assert (
        "Native ML-DSA conversion requires cryptography with ML-DSA support."
        in convert_result.output
    )
    assert not output_path.exists()
