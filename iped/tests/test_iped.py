#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Tests for IPED PRINCE cipher."""

from secrets import token_bytes

import pytest

from spsdk_iped import IPED, IPEDError


def test_ref_encrypt_ctr() -> None:
    """Test reference CTR encryption vector."""
    iped = IPED(
        key=0x01,
        address=0x80003000,
        iv=0x79EAFAB3A72412A1,
        double_encrypt=True,
        use_gcm=False,
    )
    data = 0x0CF16D721BCADFCB.to_bytes(length=8, byteorder="big")
    exp = 0xCEDB66D149075929.to_bytes(length=8, byteorder="big")
    result = iped.encrypt(data=data)
    assert result == exp
    assert iped.next_address == 0x80003000 + 8


def test_ref_decrypt_ctr() -> None:
    """Test reference CTR decryption vector."""
    iped = IPED(
        key=0x01,
        address=0x80003000,
        iv=0x79EAFAB3A72412A1,
        double_encrypt=True,
        use_gcm=False,
    )
    data = 0xCEDB66D149075929
    exp = 0x0CF16D721BCADFCB
    result = iped.decrypt(data=data)
    assert result == exp.to_bytes(length=8, byteorder="big")


def test_ref_encrypt_gcm() -> None:
    """Test reference GCM encryption vector."""
    iped = IPED(
        key=0x9DC81A3B3AEF4775297C23529ACCCE35,
        address=0x80003000,
        iv=0xC5FFB28BBB2F7876,
        aad=0x0D11BB1AA784324F,
        use_gcm=True,
    )
    data = [
        0x8A64EC141794252F,
        0xDE143CBCDE2BBEBC,
        0xB30C0C6618836731,
        0xE218FAC40858B510,
    ]
    exp = [
        0x6FD8089AD7A48DF6,
        0xC90DBE898F02BA55,
        0xF5F7A65030D0693B,
        0xAD103E34E80016FC,
    ]
    final_tag = 0xE38CA1F93131FC30

    result = iped._transaction(
        decrypt=False,
        data=b"".join(d.to_bytes(length=8, byteorder="big") for d in data),
    )
    assert result == b"".join(e.to_bytes(length=8, byteorder="big") for e in exp)
    assert iped.tag == final_tag


def test_ref_decrypt_gcm() -> None:
    """Test reference GCM decryption vector."""
    iped = IPED(
        key=0x9DC81A3B3AEF4775297C23529ACCCE35,
        address=0x80003000,
        iv=0xC5FFB28BBB2F7876,
        use_gcm=True,
        aad=0x0D11BB1AA784324F,
        tag=0xE38CA1F93131FC30,
    )

    data = [
        0x6FD8089AD7A48DF6,
        0xC90DBE898F02BA55,
        0xF5F7A65030D0693B,
        0xAD103E34E80016FC,
    ]
    exp = [
        0x8A64EC141794252F,
        0xDE143CBCDE2BBEBC,
        0xB30C0C6618836731,
        0xE218FAC40858B510,
    ]
    final_tag = 0xE38CA1F93131FC30

    result = iped._transaction(
        decrypt=True,
        data=b"".join(d.to_bytes(length=8, byteorder="big") for d in data),
    )
    assert result == b"".join(e.to_bytes(length=8, byteorder="big") for e in exp)
    assert iped.tag == final_tag


def test_ctr_roundtrip() -> None:
    """Test CTR encrypt/decrypt roundtrip with random data."""
    iped = IPED(key=1, address=2, iv=3, use_gcm=False)
    plain = token_bytes(8)
    cipher = iped.encrypt(plain)
    assert plain != cipher
    plain2 = iped.decrypt(cipher, address=2)
    assert plain == plain2


def test_invalid_key_length() -> None:
    """Test that invalid key length raises error."""
    with pytest.raises(IPEDError):
        IPED(key=b"\x01" * 32, address=0, iv=0, use_gcm=False)


def test_gcm_requires_aad() -> None:
    """Test that GCM mode requires AAD parameter."""
    with pytest.raises(IPEDError):
        IPED(key=1, address=0, iv=0, use_gcm=True, aad=None)
