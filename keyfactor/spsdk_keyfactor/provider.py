#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Main module for Keyfactor Signature Provider."""

import base64
import json
import logging
import os
from enum import Enum
from typing import Optional, Union

import requests
import requests.adapters
import requests_pkcs12
from dotenv import load_dotenv
from spsdk.crypto.certificate import Certificate
from spsdk.crypto.hash import EnumHashAlgorithm, get_hash
from spsdk.crypto.keys import PublicKey, PublicKeyRsa
from spsdk.crypto.signature_provider import SignatureProvider
from spsdk.exceptions import SPSDKError
from spsdk.utils.misc import load_secret

logger = logging.getLogger(__name__)


class KeyfactorPluginError(SPSDKError):
    """Keyfactor Plugin error."""


class KeyfactorHTTPError(SPSDKError):
    """Keyfactor HTTP Error."""


class KeyfactorAuthType(str, Enum):
    """Keyfactor authentication types."""

    NONE = "none"
    CLIENT_CERTIFICATE_PKCS12 = "client_certificate_pkcs12"
    CLIENT_CERTIFICATE_KEY = "client_certificate_key"


class KeyfactorSP(SignatureProvider):
    """Signature Provider based on a remote signing service."""

    DEFAULT_DOTENV_PATH = ".keyfactor.env"

    # identifier of this signature provider; used in yaml configuration file
    identifier = "keyfactor"

    # pylint: disable=unused-argument
    def __init__(
        self,
        env_file: Optional[str] = None,
        worker: Optional[Union[str, int]] = None,
        **kwargs: str,
    ) -> None:
        """Initialize the KeyfactorSP."""
        self._config_dir = os.path.dirname(env_file) if env_file else None
        self._load_dotenv(env_file=env_file)

        self.host = os.getenv("KEYFACTOR_HOST")
        if self.host is None:
            raise KeyfactorPluginError("Keyfactor host not provided.")
        if not self.host.startswith("http"):
            self.host = f"https://{self.host}"

        self.worker = str(worker) if worker else os.getenv("KEYFACTOR_WORKER")
        if self.worker is None:
            raise KeyfactorPluginError("Keyfactor worker not provided.")

        self.session = requests.Session()
        self._setup_session_auth()

        self.signer_certificate: Certificate
        self.prehash = self._get_prehash()
        # simply get the signature length from the environment
        # actual signature length will be self-corrected by the signer certificate
        self._signature_length = int(os.getenv("KEYFACTOR_SIGNATURE_LENGTH", "0"))

        super().__init__()

    def _load_dotenv(
        self,
        env_file: Optional[str] = None,
    ) -> None:
        """Fetch configuration from environment variables."""
        env_file_candidates = [
            env_file,
            os.environ.get("KEYFACTOR_DOTENV_PATH"),
            self.DEFAULT_DOTENV_PATH,
            os.path.expanduser(f"~/{self.DEFAULT_DOTENV_PATH}"),
            os.path.expanduser(f"~/.config/keyfactor/{self.DEFAULT_DOTENV_PATH}"),
        ]
        for candidate in env_file_candidates:
            if candidate and os.path.exists(candidate):
                logger.debug(f"Loading Keyfactor configuration from '{candidate}'.")
                load_dotenv(candidate)
                self._config_dir = os.path.dirname(candidate)
                break

    def _get_auth_type(self) -> KeyfactorAuthType:
        auth_type_str = os.getenv("KEYFACTOR_AUTH_TYPE", KeyfactorAuthType.NONE.value)
        auth_type = KeyfactorAuthType(auth_type_str)
        if auth_type == KeyfactorAuthType.NONE:
            logger.warning("No authentication method used.")
        return auth_type

    def _setup_session_auth(self) -> None:
        host_verify = os.getenv("KEYFACTOR_HOST_VERIFY", "false")
        if host_verify.casefold() in ["true", "false"]:
            self.session.verify = bool(host_verify)
        else:
            if not os.path.exists(host_verify) and self._config_dir:
                host_verify = os.path.join(self._config_dir, host_verify)
            self.session.verify = host_verify

        auth_type = self._get_auth_type()
        if auth_type == KeyfactorAuthType.NONE:
            return

        auth_value_str = os.getenv("KEYFACTOR_AUTH_VALUE")
        if not auth_value_str:
            raise KeyfactorPluginError("Keyfactor auth value not provided.")
        try:
            cert, key = auth_value_str.split(",")
            if not os.path.exists(cert) and self._config_dir:
                cert = os.path.join(self._config_dir, cert)
            if not os.path.exists(key) and self._config_dir:
                key = os.path.join(self._config_dir, key)
        except ValueError as exc:
            raise KeyfactorPluginError(
                "Keyfactor auth value must be in format 'cert_path,key_path'."
            ) from exc

        assert isinstance(self.host, str)
        if auth_type == KeyfactorAuthType.CLIENT_CERTIFICATE_KEY:
            self.session.mount(self.host, requests.adapters.HTTPAdapter())
            self.session.auth = (cert, key)
            return

        if auth_type == KeyfactorAuthType.CLIENT_CERTIFICATE_PKCS12:
            password = load_secret(key)
            self.session.mount(
                self.host,
                requests_pkcs12.Pkcs12Adapter(pkcs12_filename=cert, pkcs12_password=password),
            )
            return

        raise KeyfactorPluginError(f"Unsupported Keyfactor auth type '{auth_type}'.")

    def _get_prehash(self) -> EnumHashAlgorithm:
        prehash_str = os.getenv("KEYFACTOR_PREHASH")
        if prehash_str:
            return EnumHashAlgorithm.from_label(prehash_str.replace("-", ""))

        logger.warning("No prehash algorithm provided. Trying to determine it from the signature.")
        self.prehash = EnumHashAlgorithm.NONE
        try:
            self.sign(bytes(32))
            return self.prehash
        except KeyfactorPluginError:
            # signature check failed with no prehash
            # get the recommended hash from the signer certificate
            return self.signer_certificate.get_public_key().default_hash_algorithm

    def sign(self, data: bytes) -> bytes:
        """Return signature for data."""
        payload: dict = {"encoding": "BASE64"}

        if self.prehash and self.prehash != EnumHashAlgorithm.NONE:
            data_out = get_hash(data=data, algorithm=self.prehash)
            payload["metaData"] = {
                "USING_CLIENTSUPPLIED_HASH": "true",
                "CLIENTSIDE_HASHDIGESTALGORITHM": self.prehash.name.upper(),
            }
        else:
            data_out = data

        payload["data"] = base64.b64encode(data_out).decode(encoding="utf-8")

        url = f"{self.host}/signserver/rest/v1/workers/{self.worker}/process"

        logger.info(f"Invoking: {url}")
        logger.debug(f"Data: {json.dumps(payload, indent=2)}")
        response = self.session.post(url=url, json=payload, timeout=60)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            message: str = json.loads(response.content)
            raise KeyfactorHTTPError(f"HTTP error: {exc}\n{json.dumps(message, indent=2)}") from exc
        response_data: dict[str, str] = response.json()
        logger.debug(json.dumps(response_data, indent=2))

        self.signer_certificate = Certificate.parse(
            base64.b64decode(response_data["signerCertificate"])
        )
        signature = base64.b64decode(response_data["data"])

        puk = self.signer_certificate.get_public_key()
        is_rsa = isinstance(puk, PublicKeyRsa)

        if not puk.verify_signature(signature, data):
            if not is_rsa:
                raise KeyfactorPluginError(
                    "Signature verification failed. "
                    "Please check your KEYFACTOR_PREHASH and/or SIGNATUREALGORITHM settings."
                )
            if not puk.verify_signature(signature, data, pss_padding=True):
                raise KeyfactorPluginError(
                    "Signature verification failed. "
                    "Please check your KEYFACTOR_PREHASH and/or SIGNATUREALGORITHM settings."
                )

        return signature

    @property
    def signature_length(self) -> int:
        """Return length of the signature."""
        if self._signature_length:
            return self._signature_length

        # self-correction if signature length is not set (=0)
        if self.signer_certificate is None:
            # sign some data to get the signer certificate
            self.sign(bytes(32))

        self._signature_length = self.signer_certificate.get_public_key().signature_size
        return self._signature_length

    def verify_public_key(self, public_key: PublicKey) -> bool:
        """Verify if given public key matches private key."""
        if self.signer_certificate is None:
            # sign some data to get the signer certificate
            self.sign(bytes(32))

        return self.signer_certificate.get_public_key() == public_key

    def info(self) -> str:
        """Provide information about the Signature provider."""
        return f"Keyfactor SP: worker={self.worker}, host={self.host}"
