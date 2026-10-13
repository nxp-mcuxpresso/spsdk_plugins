#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Module for EL2GO Service Client."""

import base64
import logging
import uuid

from spsdk.crypto.hash import EnumHashAlgorithm, get_hash
from spsdk.crypto.keys import PublicKey
from spsdk.el2go.client import EL2GOClient
from spsdk.utils.config import Config

from .utils import KeyInfo, get_public_key_cache_path, load_config

logger = logging.getLogger("spsdk.el2go_service_client")


KEY_TYPES = ["ecc_p256", "ecc_p384", "ecc_p512", "rsa_2048", "rsa_3072", "rsa_4096"]
KEY_TO_HASH_ALGORITHM = {
    "ecc_p256": EnumHashAlgorithm.SHA256,
    "ecc_p384": EnumHashAlgorithm.SHA384,
    "ecc_p512": EnumHashAlgorithm.SHA512,
    "rsa_2048": EnumHashAlgorithm.SHA256,
    "rsa_3072": EnumHashAlgorithm.SHA384,
    "rsa_4096": EnumHashAlgorithm.SHA512,
}
KEY_TO_EL2GO_SIGNATURE_ALGORITHM = {
    "ecc_p256": "ECDSA",
    "ecc_p384": "ECDSA",
    "ecc_p512": "ECDSA",
    "rsa_2048": "RSASSA_PKCS_v1_5",
    "rsa_3072": "RSASSA_PKCS_v1_5",
    "rsa_4096": "RSASSA_PKCS_v1_5",
}
KEY_TO_SIGNATURE_LENGTH = {
    "ecc_p256": 64,
    "ecc_p384": 96,
    "ecc_p512": 132,
    "rsa_2048": 256,
    "rsa_3072": 384,
    "rsa_4096": 512,
}


class EL2GOServiceClient(EL2GOClient):
    """Extended Client for interacting with the EL2GO services."""

    def __init__(
        self,
        api_key: str,
        url: str = "https://api.edgelock2go.com",
        timeout: int = 60,
    ) -> None:
        """Initialize EL2GO Service Client.

        :param api_key: API key for authentication with the EL2GO service.
        :param url: Base URL for the EL2GO API endpoints.
        :param timeout: Timeout in seconds for HTTP requests to the EL2GO service.
        """
        super().__init__(api_key=api_key, url=url, timeout=timeout)

    @classmethod
    def from_config(cls, config: Config) -> "EL2GOServiceClient":
        """Create an instance of EL2GOServiceClient from a configuration object.

        :param config: Configuration object containing API credentials and settings.
        :return: An instance of EL2GOServiceClient initialized with the provided configuration.
        """
        api_key = config.load_secret("api_key")
        url = config.get_str("url", "https://api.edgelock2go.com")
        timeout = config.get_int("timeout", 60)
        return cls(
            api_key=api_key,
            url=url,
            timeout=timeout,
        )

    def sign(self, data: bytes, key_info: KeyInfo) -> bytes:
        """Sign the provided data using the EL2GO Service Client.

        :param data: Data to be signed, provided as bytes.
        :param key_info: KeyInfo object containing key details for signing.

        :return: The signature as bytes.
        """
        logger.info(
            f"Signing data using key_set_id={key_info.key_set_id}, key_id={key_info.key_id}"
        )
        endpoint = f"/api/v1/keysets/{key_info.key_set_id}/keys/{key_info.key_id}/sign-hash"
        logger.debug(f"Signing endpoint: {endpoint}")

        # at this point, hash should be set already
        assert key_info.hash_algorithm is not None, "Hash algorithm must be specified in KeyInfo."

        hashed_data = get_hash(data, key_info.hash_algorithm)

        logger.debug(f"Using hash algorithm: {key_info.hash_algorithm.name}")
        logger.debug(f"Length of pre-hashed data: {len(hashed_data)} bytes")
        logger.debug(f"Data to be signed (pre-hashed): {hashed_data.hex()}")

        data_to_sign = base64.b64encode(hashed_data).decode()
        json_data = {
            "payload": data_to_sign,
            "signatureAlgorithm": key_info.signature_algorithm,
        }
        logger.debug(f"JSON data to be sent for signing: {json_data}")
        response = self._handle_el2go_request(
            method=self.Method.POST,
            url=endpoint,
            json_data=json_data,
        )
        logger.debug(f"Received response from signing request: {response.json_body}")
        if response.status_code != 200:
            logger.error(f"Failed to sign data: {response.json_body}")
            raise RuntimeError(
                f"Failed to sign data: {response.status_code} - {response.json_body}"
            )
        signature = base64.b64decode(response.json_body["signature"])
        logger.debug(f"Received signature (raw): {signature.hex()}")
        return signature

    def download_public_key(self, key_info: KeyInfo, force_download: bool = False) -> bytes:
        """Download the public key associated with the specified key set and key ID.

        :param key_info: KeyInfo object containing key details for downloading the public key.

        :param force_download: If True, force download even if cached key exists.
        :return: The public key as bytes.
        """
        if not force_download:
            key_file_path = get_public_key_cache_path(key_info=key_info)
            if key_file_path.exists():
                logger.info(f"Using cached public key from: {key_file_path}")
                return key_file_path.read_bytes()

        endpoint = (
            f"/api/v1/keysets/{key_info.key_set_id}/keys/{key_info.key_id}/download-public-key"
        )
        logger.info(
            f"Downloading public key: key_set_id={key_info.key_set_id}, key_id={key_info.key_id}"
        )
        logger.debug(f"Public key download endpoint: {endpoint}")

        accept_header_backup = self.headers.get("Accept")
        try:
            self.headers["Accept"] = "application/octet-stream"

            self.correlation_id = str(uuid.uuid4())
            logger.info(f"EL2G-Correlation-ID: {self.correlation_id}")
            self.headers["EL2G-Correlation-ID"] = self.correlation_id
            api_response = super()._handle_request(
                method=self.Method.GET, url=endpoint, param_data=None, json_data=None
            )
            api_response.raise_for_status()

            # Assuming the public key is returned as a string
            public_key_str = api_response.text
            public_key_bytes = public_key_str.encode()

            logger.debug(f"Received response from public key request:\n{api_response.text}")

            key_file_path = get_public_key_cache_path(key_info=key_info)
            key_file_path.write_bytes(public_key_bytes)
            logger.info(f"Public key saved to: {key_file_path}")

            return public_key_bytes

        finally:
            if accept_header_backup is not None:
                self.headers["Accept"] = accept_header_backup
            else:
                del self.headers["Accept"]

    def cmac(self, data: bytes, key_info: KeyInfo) -> bytes:
        """Compute CMAC for the provided data using the EL2GO Service Client.

        :param data: Data for which to compute the CMAC, provided as bytes.
        :param key_info: KeyInfo object containing key details for CMAC computation.

        :return: The computed CMAC as bytes.
        """
        logger.info(
            f"Computing CMAC for data using key_set_id={key_info.key_set_id}, key_id={key_info.key_id}"
        )
        endpoint = f"/api/v1/keysets/{key_info.key_set_id}/keys/{key_info.key_id}/cmac"
        logger.debug(f"CMAC endpoint: {endpoint}")

        json_data = {"payload": base64.b64encode(data).decode()}
        logger.debug(f"JSON data to be sent for CMAC computation: {json_data}")
        response = self._handle_el2go_request(
            method=self.Method.POST,
            url=endpoint,
            json_data=json_data,
        )
        logger.debug(f"Received response from CMAC request: {response.json_body}")
        if response.status_code != 200:
            logger.error(f"Failed to compute CMAC: {response.json_body}")
            raise RuntimeError(
                f"Failed to compute CMAC: {response.status_code} - {response.json_body}"
            )
        cmac_value = base64.b64decode(response.json_body["cmacPayload"])
        logger.debug(f"Received CMAC (raw): {cmac_value.hex()}")
        return cmac_value

    def get_key_info(self, key_set_id: int, key_id: int) -> KeyInfo:
        """Retrieve the public key type from the EL2GO service.

        :param key_set_id: ID of the key set.
        :param key_id: ID of the key.
        :return: The public key type as a string.
        """
        logger.info(f"Retrieving public key type for key_set_id={key_set_id}, key_id={key_id}")
        key_info = KeyInfo(key_set_id=key_set_id, key_id=key_id)
        key_data = self.download_public_key(key_info=key_info)
        public_key = PublicKey.parse(key_data)
        key_type = ""

        # the mypy issues below shall be fixed in SPSDK
        if "RSA" in repr(public_key):
            key_type = f"rsa_{public_key.key_size}"  # type: ignore[attr-defined]
        elif "EC" in repr(public_key):
            key_type = f"ecc_p{public_key.key_size}"  # type: ignore[attr-defined]
        if key_type not in KEY_TYPES:
            raise ValueError(f"Invalid key type retrieved: {key_type}. Must be one of {KEY_TYPES}.")

        hash_algorithm = KEY_TO_HASH_ALGORITHM[key_type]
        signature_algorithm = KEY_TO_EL2GO_SIGNATURE_ALGORITHM[key_type]
        signature_length = KEY_TO_SIGNATURE_LENGTH[key_type]

        return KeyInfo(
            key_set_id=key_set_id,
            key_id=key_id,
            key_type=key_type,
            hash_algorithm=hash_algorithm,
            signature_algorithm=signature_algorithm,
            signature_length=signature_length,
        )


def get_client_key_info(
    config_path: str | None = None, full_key_info: bool = True, **kwargs: str
) -> tuple[EL2GOServiceClient, KeyInfo]:
    """Get the key information from the EL2GO service based on the provided configuration.

    :param config_path: Path to the configuration file. If None, an empty configuration is created.
    :param full_key_info: Whether to retrieve full key information.
    :param kwargs: Additional configuration parameters to update the loaded configuration.
    :return: A tuple containing the EL2GOServiceClient and a KeyInfo object.
    """
    config = load_config(config_path, **kwargs)
    client = EL2GOServiceClient.from_config(config)
    key_set_id = config.get_int("key_set_id")
    key_id = config.get_int("key_id")
    if full_key_info:
        key_info = client.get_key_info(key_set_id=key_set_id, key_id=key_id)
    else:
        key_info = KeyInfo(key_set_id=key_set_id, key_id=key_id)
    return client, key_info
