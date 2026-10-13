#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Main module for EL2GO Signature Provider."""

from spsdk.crypto.keys import PublicKey
from spsdk.crypto.signature_provider import SignatureProvider

from .client import get_client_key_info


class EL2GoSP(SignatureProvider):
    """Signature Provider based on a remote signing service."""

    # identifier of this signature provider; used in yaml configuration file
    identifier = "el2go"

    def __init__(self, config_path: str | None = None, **kwargs: str) -> None:
        """Initialize the EL2GoSP."""
        super().__init__()
        self.client, self.key_info = get_client_key_info(
            config_path=config_path, full_key_info=True, **kwargs
        )

    def sign(self, data: bytes) -> bytes:
        """Return signature for data."""
        signature = self.client.sign(data=data, key_info=self.key_info)
        return signature

    @property
    def signature_length(self) -> int:
        """Return length of the signature."""
        # at this point, signature_length should be set already
        assert self.key_info.signature_length is not None
        return self.key_info.signature_length

    def verify_public_key(self, public_key: PublicKey) -> bool:
        """Verify if given public key matches private key."""
        puk = PublicKey.parse(self.client.download_public_key(key_info=self.key_info))
        return puk == public_key

    def info(self) -> str:
        """Provide information about the Signature provider."""
        return f"EL2GO SP: {self.client.base_url}, {self.key_info}"
