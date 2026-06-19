#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from spsdk_pqc.utils import PQCPrivateKey, PrivateKey, split_hybrid_key


@pytest.mark.parametrize("key_file", ["hybrid.pem", "hybrid.der"])
def test_split_hybrid_pem(data_dir: str, key_file: str) -> None:
    """Test splitting hybrid key into classic and PQC portions."""
    hybrid_key_path = f"{data_dir}/{key_file}"

    with open(hybrid_key_path, "rb") as f:
        hybrid_data = f.read()

    prk1, prk2, _ = split_hybrid_key(hybrid_data, password="test")

    assert prk1 is not None
    assert prk2 is not None
    assert isinstance(prk1, PrivateKey)
    assert isinstance(prk2, PQCPrivateKey)

    classic_key_path = f"{data_dir}/ecc.pem"
    pqc_key_path = f"{data_dir}/dil.pem"

    classic_key = PrivateKey.load(classic_key_path)
    pqc_key = PrivateKey.load(pqc_key_path)

    assert prk1 == classic_key
    assert prk2.private_data == pqc_key.key.private_data
