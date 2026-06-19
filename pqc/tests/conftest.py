#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Common fixtures and utilities for tests."""

import logging
import os
from typing import Any

import pytest


@pytest.fixture(scope="module")
def data_dir(request: Any) -> str:
    """Get test data directory path for the current test module.

    Constructs the absolute path to the 'data' directory located alongside
    the test file that is currently being executed.

    :param request: Pytest request fixture containing test execution context.
    :return: Absolute path to the test data directory.
    """
    logging.debug(f"data_dir for module: {request.fspath}")
    data_path = os.path.join(os.path.dirname(request.fspath), "data")
    logging.debug(f"data_dir: {data_path}")
    return data_path
