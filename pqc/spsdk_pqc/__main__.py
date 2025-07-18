#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""CLI script for basic crypto operations."""

import sys
from pathlib import Path
from typing import Union

import click
from spsdk.crypto.keys import PrivateKeyEcc
from typing_extensions import Literal

from spsdk_pqc.pqc_asn import der_2_pem
from spsdk_pqc.utils import combine_hybrid_key, split_hybrid_key
from spsdk_pqc.wrapper import (
    KEY_INFO,
    DilithiumPublicKey,
    MLDSAPublicKey,
    PQCAlgorithm,
    PQCError,
    PQCPrivateKey,
    PQCPublicKey,
)


@click.group(name="pqctool", no_args_is_help=True)
def main() -> None:
    """Tool for basic crypto operation using PQC keys."""


@main.command(name="gen-key", no_args_is_help=True)
@click.option(
    "-a",
    "--algorithm",
    type=click.Choice([alg.value for alg in PQCAlgorithm], case_sensitive=False),
    required=True,
    help="Select PQC algorithm.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False),
    required=True,
    help="Path where to store private key. Public key's suffix will be .pub.",
)
@click.option(
    "-e",
    "--encoding",
    type=click.Choice(["PEM", "DER"], case_sensitive=False),
    default="PEM",
    show_default=True,
    help="Key file encoding.",
)
def get_key(algorithm: PQCAlgorithm, output: str, encoding: Literal["PEM", "DER"]) -> None:
    """Generate key pair. Public key will be generated as well with suffix '.pub'."""
    prk = PQCPrivateKey(algorithm=algorithm)
    Path(output).write_bytes(prk.export(pem=encoding == "PEM"))
    puk = prk.get_public_key()
    Path(output).with_suffix(".pub").expanduser().write_bytes(puk.export(pem=encoding == "PEM"))


@main.command(name="sign", no_args_is_help=True)
@click.option(
    "-k",
    "--key",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to private key.",
)
@click.option(
    "-d",
    "--data",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to data to sign.",
)
@click.option(
    "-s",
    "--signature",
    type=click.Path(dir_okay=False),
    required=True,
    help="Path where to store the signature.",
)
def sign(key: str, data: str, signature: str) -> None:
    """Sign data using private key."""
    key_data = Path(key).expanduser().read_bytes()
    tbs_data = Path(data).expanduser().read_bytes()
    prk = PQCPrivateKey.parse(key_data)
    sign_data = prk.sign(tbs_data)
    out_path = Path(signature).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(sign_data)


@main.command(name="verify", no_args_is_help=True)
@click.option(
    "-k",
    "--key",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to public (private) key.",
)
@click.option(
    "-d",
    "--data",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to data that was signed.",
)
@click.option(
    "-s",
    "--signature",
    type=click.Path(dir_okay=False),
    required=True,
    help="Path to signature.",
)
def verify(key: str, data: str, signature: str) -> int:
    """Verify signature using public key."""
    key_data = Path(key).expanduser().read_bytes()
    try:
        puk = PQCPublicKey.parse(key_data)
    except PQCError:
        puk = PQCPrivateKey.parse(key_data).get_public_key()

    assert isinstance(puk, PQCPublicKey)
    sign_data = Path(signature).expanduser().read_bytes()
    tbs_data = Path(data).expanduser().read_bytes()
    result = puk.verify(signature=sign_data, data=tbs_data)
    click.echo(f"Signature {'matches' if result else 'DOES NOT MATCH!'}")
    return int(result)


@main.command(name="encode", no_args_is_help=True)
@click.option(
    "-k",
    "--key",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to key file to encode.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False),
    required=True,
    help="Path to (re)encoded key file.",
)
@click.option(
    "-e",
    "--encoding",
    type=click.Choice(["PEM", "DER"], case_sensitive=False),
    default="PEM",
    show_default=True,
    help="Key file encoding.",
)
def encode(key: str, encoding: Literal["PEM", "DER"], output: str) -> int:
    """Encode key using PEM/DER encoding."""
    key_data = Path(key).expanduser().read_bytes()

    key_obj: Union[PQCPrivateKey, PQCPublicKey, None] = None

    try:
        key_obj = PQCPrivateKey.parse(key_data)
        save_key(key=key_obj, encoding=encoding, output=output)
        return 0
    except PQCError:
        pass

    raw_public_sizes = [v.public_key_size for v in KEY_INFO.values()]

    if len(key_data) in raw_public_sizes:
        click.echo("Key length indicates a PQC Public key")
        click.echo(
            "Currently there's no way to distinguish between ML-DSA and Dilithium Public keys"
        )
        answer = click.confirm("Is it a ML-DSA key? (no means Dilithium)", default=True)
        if answer:
            puk = MLDSAPublicKey(public_data=key_data)
        else:
            puk = DilithiumPublicKey(public_data=key_data)  # type: ignore
        save_key(key=puk, encoding=encoding, output=output)
        return 0

    try:
        puk = PQCPublicKey.parse(data=key_data)  # type: ignore
        save_key(key=puk, encoding=encoding, output=output)
        return 0
    except PQCError:
        pass

    click.secho("Unable to determine PQC Key type", fg="red")
    return 1


@main.command(name="split", no_args_is_help=True)
@click.option(
    "-h",
    "--hybrid",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to PEM-encoded Hybrid PQC key.",
)
@click.option(
    "-p",
    "--password",
    help="Password to Hybrid key (if needed and not provided, you'll prompted later)",
)
@click.option("-kp", "--keep-password", is_flag=True, help="Keep the partial keys encrypted.")
@click.option(
    "-c",
    "--classic",
    required=True,
    type=click.Path(dir_okay=False),
    help="Path where to store the DER-encoded Classic portion of hybrid key.",
)
@click.option(
    "-q",
    "--pqc",
    required=True,
    type=click.Path(dir_okay=False),
    help="Path where to store the DER-encoded PQC portion of hybrid key.",
)
def split(hybrid: str, password: str, keep_password: bool, classic: str, pqc: str) -> None:
    """Split Hybrid PQC key into classic and PQC keys."""
    data = Path(hybrid).read_bytes()
    prk1, prk2, password = split_hybrid_key(data, password=password)
    click.echo(f"Saving DER-encoded Classic key to: {classic}")
    prk1.save(classic, password=password if keep_password else None)
    click.echo(f"Saving DER-encoded PQC key to: {pqc}")
    save_key(prk2, encoding="DER", output=pqc)


@main.command(name="combine", no_args_is_help=True)
@click.option(
    "-c",
    "--classic",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the classic key.",
)
@click.option(
    "-q",
    "--pqc",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the PQC key.",
)
@click.option(
    "-p",
    "--password",
    # required=True,
    help="Password to Hybrid key",
)
@click.option(
    "-h",
    "--hybrid",
    type=click.Path(dir_okay=False),
    required=True,
    help="Path where to store the PEM-encoded Hybrid PQC key.",
)
def combine(classic: str, pqc: str, password: str, hybrid: str) -> None:
    """Combine classic and PQC keys into Hybrid PQC key."""
    prk1 = PrivateKeyEcc.parse(Path(classic).read_bytes())
    prk2 = PQCPrivateKey.parse(Path(pqc).read_bytes())
    hybrid_data = combine_hybrid_key(classic_prk=prk1, pqc_prk=prk2, password=password)
    click.echo(f"Saving PEM-encoded Hybrid key to: {hybrid}")
    Path(hybrid).write_bytes(
        der_2_pem(hybrid_data, private=True, algorithm="ENCRYPTED" if password else "")
    )


def save_key(
    key: Union[PQCPrivateKey, PQCPublicKey], encoding: Literal["PEM", "DER"], output: str
) -> None:
    """Store key using the selected encoding."""
    key_data = key.export(pem=encoding == "PEM")
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(key_data)
    click.get_current_context().exit()


if __name__ == "__main__":
    sys.exit(main())
