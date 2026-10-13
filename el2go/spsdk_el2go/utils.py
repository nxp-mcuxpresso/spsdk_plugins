#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Module for EL2GO Service Client utilities."""

from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs
from spsdk.crypto.hash import EnumHashAlgorithm
from spsdk.utils.config import Config

PLATFORM_DIRS = PlatformDirs("spsdk-el2go", "nxp", ensure_exists=True)
PUBLIC_KEY_CACHE_DIR = PLATFORM_DIRS.user_cache_path
PUBLIC_KEY_FILE_TEMPLATE = "public_key_{key_set_id}_{key_id}.pem"


def load_config(config_path: str | None = None, **kwargs: int | str) -> Config:
    """Load configuration from a file and update it with additional keyword arguments.

    :param config_path: Path to the configuration file. If None, an empty configuration is created.
    :param kwargs: Additional configuration parameters to update the loaded configuration.
    :return: A Config object containing the loaded and updated configuration.
    """
    if config_path is None:
        config = Config({})
    else:
        config = Config.create_from_file(config_path)
    config.update(kwargs)
    return config


@dataclass
class KeyInfo:
    """Data class to hold key information."""

    key_set_id: int
    key_id: int
    key_type: str | None = None
    hash_algorithm: EnumHashAlgorithm | None = None
    signature_algorithm: str | None = None
    signature_length: int | None = None


def get_public_key_cache_path(key_info: KeyInfo) -> Path:
    """Get the path to the cached public key file.

    :param key_info: KeyInfo object containing key details.
    :return: Path to the cached public key file as a Path object.
    """
    key_file_name = PUBLIC_KEY_FILE_TEMPLATE.format(
        key_set_id=key_info.key_set_id, key_id=key_info.key_id
    )
    return PUBLIC_KEY_CACHE_DIR / key_file_name
