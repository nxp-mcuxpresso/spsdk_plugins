#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Main module for EL2GO SB Key Derivation Provider."""

from spsdk.sbfile.utils.key_derivator import SB31KeyDerivator

from .client import get_client_key_info


class EL2GoKDP(SB31KeyDerivator):
    """Key Derivation Provider based on a remote signing service."""

    # identifier of this key derivation provider; used in yaml configuration file
    identifier = "el2go"

    def __init__(self, config_path: str | None = None, **kwargs: str) -> None:
        """Initialize the EL2GoSP."""
        super().__init__()
        self.client, self.key_info = get_client_key_info(
            config_path=config_path, full_key_info=False, **kwargs
        )

    def remote_cmac(self, data: bytes) -> bytes:
        """Calculate CMAC using the implementation-specific method."""
        return self.client.cmac(data=data, key_info=self.key_info)

    def info(self) -> str:
        """Provide information about the Key Derivation provider."""
        return f"EL2GO SB key derivator: {self.client.base_url}, {self.key_info}"
