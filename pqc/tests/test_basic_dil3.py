#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

from spsdk_pqc import DilithiumPrivateKey, DilithiumPublicKey


def test_private_key():
    private = DilithiumPrivateKey(level=3)
    assert private.key_size == 4000 * 8
    assert len(private.public_data) == 1952


def test_sign_verify():
    private = DilithiumPrivateKey(level=3)
    public = DilithiumPublicKey(private.public_data)
    message = b"Message to sign"

    signature = private.sign(data=message)
    assert len(signature) == 3293

    is_valid = public.verify(data=message, signature=signature)
    assert is_valid
