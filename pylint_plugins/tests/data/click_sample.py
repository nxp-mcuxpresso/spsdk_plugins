#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

import click
from click import Choice


@click.command()
# this is ok, because options are numbers, but we can't detect it
@click.option("-f", "--flag", type=click.Choice(["1", "2"]))
# this is ok, because options are numbers, but we can't detect it
@click.option("-f", "--flag", type=Choice(["1", "2"], case_sensitive=True))

# this is ok
@click.option("-o", "--other", type=click.Choice(["aaa", "bbb"], case_sensitive=False))
# this is bad
@click.option("-a", "--answer", type=click.Choice(["yes", "no"]))
def main():
    pass


if __name__ == "__main__":
    main()
