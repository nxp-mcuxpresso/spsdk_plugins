#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Companion application for Keyfactor Signature Provider configuration and management."""

import os
import sys

import click

from spsdk_keyfactor.provider import KeyfactorSP


@click.group(name="nxp-keyfactor")
def main() -> None:
    """Companion application for SPSDK Keyfactor Signature Provider plugin."""


@main.command(name="get-template")
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    help="Output file path for the configuration template",
    show_default=True,
    default=os.path.expanduser("~/.keyfactor.env").replace("\\", "/"),
)
def get_template(output: str) -> None:
    """Generate environment file template used by the plugin."""
    if os.path.exists(output):
        overwrite = click.confirm(f"File {output} already exists. Overwrite?", abort=True)
        if not overwrite:
            return
    with open(output, "w", encoding="utf-8") as f:
        f.write(
            """# Keyfactor Signature Provider Configuration Template
# Authentication Type Options:
# - client_certificate_pkcs12: Use PKCS12 client certificate
# - client_certificate_key: Use separate client certificate and key

# Authentication Type
KEYFACTOR_AUTH_TYPE=client_certificate_pkcs12

# Authentication Value (depends on auth type)
# For PKCS12: Path to .p12 file and password (password can be in a file)
# For separate cert, key: Path to certificate and key file
KEYFACTOR_AUTH_VALUE=FirstName.LastName.p12,pass.txt

# Keyfactor Host Configuration
KEYFACTOR_HOST=https://pq-sign.keyfactoriot.com

# Keyfactor Host Verification Certificate
# This certificate can be obtained via "openssl client_s" or web browser (lock icon near address bar)
KEYFACTOR_HOST_VERIFY="SignServer/ejbcakfdemocom.pem"

# Specify prehash algorithm (SHA-256, SHA-384, SHA-512)
KEYFACTOR_PREHASH=SHA-512

# Optional: Specify signature length if not provided, it will be automatically detected
KEYFACTOR_SIGNATURE_LENGTH=0

# Optional: Specify worker ID if not set in config
KEYFACTOR_WORKER=3
"""
        )
    click.echo(f"Configuration template generated to: {output}")


@main.command(name="get-puk", no_args_is_help=True)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False),
    help=(
        "Path to the Keyfactor environment file. "
        "Default search paths: $KEYFACTOR_DOTENV_PATH, .keyfactor.env, ~/.keyfactor.env, ~/.config/.keyfactor.env"
    ),
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    required=True,
    help="Output file path for the public key",
)
@click.option("-w", "--worker", type=str, required=True, help="Keyfactor worker identifier")
def get_puk(output: str, config: str, worker: str) -> None:
    """Retrieve public key from Keyfactor server for given worker."""
    sp = KeyfactorSP(env_file=config, worker=worker)
    sp.sign(bytes([0] * 32))  # Dummy sign to retrieve public key
    if sp.signer_certificate:
        puk = sp.signer_certificate.get_public_key()
        puk.save(output)


if __name__ == "___main__":
    sys.exit(main())
