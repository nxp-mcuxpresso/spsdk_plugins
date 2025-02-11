#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Main module for PKCS11SP."""

import os
from functools import cached_property
from typing import Any, Optional, Tuple

from asn1crypto.keys import ECDomainParameters
from spsdk.crypto.hash import EnumHashAlgorithm, get_hash
from spsdk.crypto.keys import PublicKey
from spsdk.crypto.signature_provider import SignatureProvider
from spsdk.exceptions import SPSDKError
from spsdk.utils.misc import load_secret

import pkcs11


# pylint: disable=too-many-arguments,too-many-instance-attributes,too-many-positional-arguments
class PKCS11SP(SignatureProvider):
    """Signature Provider using a PKCS#11 interface."""

    # identifier of this signature provider; used in yaml configuration file
    identifier = "pkcs11"

    def __init__(
        self,
        so_path: str,
        user_pin: str,
        token_label: Optional[str] = None,
        token_serial: Optional[str] = None,
        key_label: Optional[str] = None,
        key_id: Optional[str] = None,
        pss_padding: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize PKCS11 interface.

        :param so_path: Path to PKCS#11 library.
            It might be a full path, or just library name, if the path to library is in PATH env variable.
        :param user_pin: User PIN. It can be a path to a file, or ENV variable
        :param token_label: PKCS#11 Token label, defaults to None
        :param token_serial: PKCS#11 Token serial number, defaults to None
        :param key_label: Key Label, defaults to None
        :param key_id: Key ID, defaults to None
        :raises SPSDKError: PKCS#11 library was not found
        :raises SPSDKError: TOKEN_LABEL or TOKEN_ID is not specified
        :raises SPSDKError: KEY_LABEL or KEY_ID is not specified
        :raises SPSDKError: TOKEN or KEY was not found in the HSM
        """
        if not token_label and not token_serial:
            raise SPSDKError("Missing 'token_label' or 'token_serial', or both")
        self.token_label = token_label
        self.token_serial = token_serial
        if not key_label and not key_id:
            raise SPSDKError("Missing 'key_label' or 'key_id', or both")
        self.key_label = key_label
        self.key_id = key_id
        self.pss_padding = pss_padding
        lib = pkcs11.lib(self._get_so_path(so_path))
        self.token: pkcs11.Token = lib.get_token(
            token_label=self.token_label, token_serial=token_serial
        )
        if not self.token:
            raise SPSDKError(
                f"Could not find Token with token_label={self.token}, token_serial={self.token_serial}"
            )
        self.user_pin = load_secret(user_pin)
        try:
            with self.token.open(user_pin=self.user_pin) as session:
                session: pkcs11.Session  # type: ignore[no-redef]  # this is just for intellisense
                key: pkcs11.PrivateKey = session.get_key(
                    object_class=pkcs11.ObjectClass.PRIVATE_KEY, label=self.key_label
                )
            if not key:
                raise SPSDKError(
                    f"Could not find Private key with label={self.key_label}, id={self.key_id}"
                )
        except (pkcs11.PKCS11Error, RuntimeError) as e:
            raise SPSDKError(f"Problem opening a session: {e.__class__.__name__} {e}") from e

        # extra keyword arguments are currently not used
        self.kwargs = kwargs

        super().__init__()

    @staticmethod
    def _get_so_path(path: str) -> str:
        path = os.path.expanduser(os.path.expandvars(path))
        if os.path.isfile(path):
            return path
        for env_path in os.environ["PATH"]:
            candidate = os.path.join(env_path, path)
            if os.path.isabs(candidate):
                return candidate
        raise SPSDKError(f"Could not find PKCS11 library {path}")

    @classmethod
    def _get_key_length(cls, key: pkcs11.PrivateKey) -> int:
        if key.key_type == pkcs11.KeyType.RSA:
            return key.key_length // 8
        if key.key_type == pkcs11.KeyType.EC:
            ec_params = ECDomainParameters.load(key[pkcs11.Attribute.EC_PARAMS])
            return ec_params.key_size
        raise SPSDKError(f"Unsupported KeyType: {key.key_type}")

    @classmethod
    def _get_hash_alg(cls, key: pkcs11.PrivateKey) -> EnumHashAlgorithm:
        if key.key_type == pkcs11.KeyType.RSA:
            return EnumHashAlgorithm.SHA256
        if key.key_type == pkcs11.KeyType.EC:
            # key.key_length doesn't work for EC keys
            key_length = cls._get_key_length(key=key)
            hash_size = {32: 256, 48: 384, 66: 512}[key_length]
            return EnumHashAlgorithm.from_label(f"sha{hash_size}")
        raise SPSDKError(f"Unsupported KeyType: {key.key_type}")

    @classmethod
    def _get_pkcs1_1_5_padding(cls, digest: bytes, key_length: int) -> bytes:
        hash_id = b"\x30\x31\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x01\x05\x00\x04\x20"
        padding_len = key_length - len(hash_id) - len(digest) - 3
        padding = b"\xff" * padding_len
        return b"\x00\x01" + padding + b"\x00" + hash_id + digest

    def sign(self, data: bytes) -> bytes:
        """Return the signature for data."""
        with self.token.open(user_pin=self.user_pin) as session:
            session: pkcs11.Session  # type: ignore[no-redef]  # this is just for intellisense
            key: pkcs11.PrivateKey = session.get_key(
                object_class=pkcs11.ObjectClass.PRIVATE_KEY, label=self.key_label, id=self.key_id
            )
            if not key:
                raise SPSDKError(
                    f"Could not find Private key with label={self.key_label}, id={self.key_id}"
                )

            # some HSMs don't offer signing with hashing in one go, thus we pre-hash the data
            hash_alg = self._get_hash_alg(key=key)
            digest = get_hash(data=data, algorithm=hash_alg)
            mechanism = pkcs11.Mechanism.ECDSA
            mechanism_param: Optional[Tuple] = None

            if key.key_type == pkcs11.KeyType.RSA:
                if self.pss_padding:
                    mechanism = pkcs11.Mechanism.RSA_PKCS_PSS
                    mechanism_param = (pkcs11.Mechanism.SHA256, pkcs11.MGF.SHA256, 32)
                else:
                    mechanism = pkcs11.Mechanism.RSA_X_509
                    digest = self._get_pkcs1_1_5_padding(
                        digest=digest, key_length=self._get_key_length(key=key)
                    )
            try:
                if mechanism_param:
                    return key.sign(digest, mechanism=mechanism, mechanism_param=mechanism_param)
                return key.sign(digest, mechanism=mechanism)
            except (pkcs11.PKCS11Error, RuntimeError) as e:
                raise SPSDKError(f"Problem with PKCS#11 sining: {e.__class__.__name__} {e}") from e

    @cached_property
    def signature_length(self) -> int:
        """Return length of the signature."""
        with self.token.open(user_pin=self.user_pin) as session:
            session: pkcs11.Session  # type: ignore[no-redef]  # this is just for intellisense
            key: pkcs11.PrivateKey = session.get_key(
                object_class=pkcs11.ObjectClass.PRIVATE_KEY, label=self.key_label, id=self.key_id
            )
            if not key:
                raise SPSDKError(
                    f"Could not found Private key with label={self.key_label}, id={self.key_id}"
                )
            if key.key_type == pkcs11.KeyType.RSA:
                return self._get_key_length(key=key)
            if key.key_type == pkcs11.KeyType.EC:
                return self._get_key_length(key=key) * 2
        raise SPSDKError(f"Unsupported KeyType: {key.key_type}")

    def verify_public_key(self, public_key: PublicKey) -> bool:
        """Verify if given public key matches private key."""
        # HSM may not have the public key available under same label as the private key
        # thus we simply sing an arbitrary message and verify the signature
        sample_data = b"sample data"
        signature = self.sign(data=sample_data)
        return public_key.verify_signature(signature=signature, data=sample_data)

    def info(self) -> str:
        """Provide information about the Signature provider."""
        return f"PKCS#11 SP using {self.token}"
