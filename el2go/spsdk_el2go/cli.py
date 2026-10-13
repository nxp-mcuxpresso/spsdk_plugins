#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Helper application for EL2GO Service Providers."""

import os
import sys

import click

from spsdk_el2go.client import EL2GOServiceClient, KeyInfo
from spsdk_el2go.utils import load_config


@click.group()
def main() -> None:
    """EL2GO CLI tool."""


@main.command(name="download-public-key", no_args_is_help=True)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True),
    required=True,
    help="Path to the configuration file.",
)
@click.option(
    "-ks",
    "--key-set-id",
    type=int,
    help="Key set ID for the public key to download. (override config file value)",
)
@click.option(
    "-k",
    "--key-id",
    type=int,
    help="Key ID for the public key to download. (override config file value)",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    required=True,
    help="Path to save the downloaded public key.",
)
@click.option(
    "-fd",
    "--force-download",
    is_flag=True,
    default=False,
    help="Force download even if cached key exists.",
)
def download_public_key(
    config: str, output: str, force_download: bool, key_id: int | None, key_set_id: int | None
) -> None:
    """Download public key from EL2GO service."""
    click.echo("Downloading public key from EL2GO service...")

    config_data = load_config(config)
    client = EL2GOServiceClient.from_config(config_data)
    key_set_id = key_set_id or config_data.get_int("key_set_id")
    key_id = key_id or config_data.get_int("key_id")
    key_info = KeyInfo(key_set_id=key_set_id, key_id=key_id)
    public_key = client.download_public_key(key_info=key_info, force_download=force_download)

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    with open(output, "wb") as f:
        f.write(public_key)
    click.echo(f"Public key downloaded: {output}")


@main.command(name="get-template", no_args_is_help=True)
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    required=True,
    help="Path to save the configuration file template.",
)
def get_template(output: str) -> None:
    """Generate a configuration file template for EL2GO service."""
    click.echo("Generating configuration file template...")

    template = """
# Configuration file for EL2GO Code Signing service

# Base URL of the EL2GO service
url: https://api.edgelock2go.com

# API key for authenticating with the EL2GO service
# Options how to provide the API key:
# 1. Directly in the configuration file (not recommended for security reasons)
# 2. Environment variable (starting with $ e.g.: $MY_EL2GO_API_KEY)
# 3. Path to a file containing the API key (e.g.: ~/.el2go/api_key)
# 4. Environment variable pointing to a file containing the API key (e.g.: $MY_EL2GO_API_KEY_FILE)
api_key: ~/.el2go/api_key

# Key set ID and key ID for sign/encryption operations
# IDs are shown in the EL2GO web interface under "Code Signing" section
key_set_id: 12
key_id: 123
"""

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        f.write(template)
    click.echo(f"Configuration file template generated: {output}")


if __name__ == "__main__":
    sys.exit(main())
