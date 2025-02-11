#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2024-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

from typing import Optional
from unittest.mock import patch

import pytest
from packaging.metadata import Metadata, RawMetadata

from codecheck.checker_dependencies import (
    DependencyInfo,
    GithubLicense,
    LicenseBase,
    LocalPackageLicense,
)


def mock_load_spdx_config():
    return {
        "BSD-3-Clause": [
            "BSD",
            "BSD-3-Clause",
        ],
        "MIT": ["MIT License"],
    }


def mock_get_package_metadata(name: str) -> Optional[Metadata]:
    data = {
        "my_dependency": Metadata.from_raw(
            RawMetadata(name="my_dependency", version="1.0", metadata_version="1.0")
        )
    }
    return data.get(name)


@patch("codecheck.checker_dependencies.get_package_metadata", mock_get_package_metadata)
def test_dependency_info_get_version():
    dep_info = DependencyInfo(name="my_dependency", home_page="github.com/my_dependency")
    version = dep_info.get_version()
    assert version.major == 1
    assert version.minor == 0
    dep_info = DependencyInfo(
        name="my_another_dependency", home_page="github.com/my_another_dependency"
    )
    version = dep_info.get_version()
    assert version is None


@patch("codecheck.checker_dependencies.get_package_metadata", mock_get_package_metadata)
def test_dependency_info_str():
    dep_info = DependencyInfo(name="my_dependency", home_page="github.com/my_dependency")
    dep_info_str = str(dep_info)
    assert "Name: my_dependency" in dep_info_str
    assert "Home page: github.com/my_dependency" in dep_info_str
    assert "Version: 1.0" in dep_info_str
    dep_info = DependencyInfo(
        name="my_another_dependency", home_page="github.com/my_another_dependency"
    )
    assert "Unknown version" in str(dep_info)


@patch("codecheck.checker_dependencies.get_package_metadata", mock_get_package_metadata)
def test_dependency_info_repr():
    assert (
        repr(DependencyInfo(name="my_dependency", home_page="github.com/my_dependency"))
        == "<DepInfo name=my_dependency,version=1.0>"
    )
    assert (
        repr(DependencyInfo(name="uninstalled_dependency", home_page="github.com/my_dependency"))
        == "<DepInfo name=uninstalled_dependency,version=Unknown version>"
    )


@patch("codecheck.checker_dependencies.load_spdx_config", mock_load_spdx_config)
@pytest.mark.parametrize(
    "licenses_cfg,expected_spdx",
    [
        (
            [{"source": "package", "license_str": "BSD", "package_name": "my_dependency"}],
            "BSD-3-Clause",
        ),
        (
            [{"source": "package", "license_str": "BSD-3-Clause", "package_name": "my_dependency"}],
            "BSD-3-Clause",
        ),
        (
            [{"source": "package", "license_str": "BSD-2-Clause", "package_name": "my_dependency"}],
            None,
        ),
        (
            [
                {
                    "source": "package",
                    "license_str": "BSD-2-Clause",
                    "package_name": "my_dependency",
                },
                {
                    "source": "github",
                    "license_str": "BSD-3-Clause",
                    "project_name": "my_dependency",
                },
            ],
            "BSD-3-Clause",
        ),
        (
            [
                {
                    "source": "package",
                    "license_str": "MIT License",
                    "package_name": "my_dependency",
                },
                {
                    "source": "github",
                    "license_str": "BSD-3-Clause",
                    "project_name": "my_dependency",
                },
            ],
            "MIT",
        ),
    ],
)
def test_dependency_info_get_spdx(licenses_cfg, expected_spdx):
    license_types = {"package": LocalPackageLicense, "github": GithubLicense}
    licenses = []
    for license_cfg in licenses_cfg:
        license_class = license_types[license_cfg.pop("source")]
        licenses.append(license_class(**license_cfg))
    dep_info = DependencyInfo(
        name="my_dependency", home_page="github.com/my_dependency", licenses=licenses
    )
    spdx = dep_info.get_spdx_license()
    if expected_spdx:
        assert isinstance(spdx, LicenseBase)
        assert spdx.get_spdx() == expected_spdx
    else:
        assert spdx is None
