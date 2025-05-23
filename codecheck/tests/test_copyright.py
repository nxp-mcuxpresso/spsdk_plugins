#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
import os
from typing import Type

import pytest

from codecheck.checker_copyright_year import (
    CheckResult,
    CopyrightChecker,
    CSourceFile,
    JavaScriptSourceFile,
    PythonSourceFile,
    SourceFile,
    TypeScriptSourceFile,
    XmlSourceFile,
    YamlSourceFile,
    YearRange,
    YearRanges,
)


def test_year_range():
    with_end_range = YearRange(from_year=2008, to_year=2010)
    assert not with_end_range.is_year_in_range(2007)
    assert with_end_range.is_year_in_range(2008)
    assert with_end_range.is_year_in_range(2009)
    assert with_end_range.is_year_in_range(2010)
    assert not with_end_range.is_year_in_range(2011)
    with_end_range = YearRange(from_year=2008)
    assert not with_end_range.is_year_in_range(2007)
    assert with_end_range.is_year_in_range(2008)
    assert not with_end_range.is_year_in_range(2009)


def test_year_range_to_string():
    with_end_range = str(YearRange(from_year=2008, to_year=2010))
    assert with_end_range == "2008-2010"
    with_end_range = str(YearRange(from_year=2008))
    assert with_end_range == "2008"


def test_year_ranges():
    year_ranges = YearRanges(
        [
            YearRange(from_year=2008, to_year=2010),
            YearRange(from_year=2012),
            YearRange(from_year=2014, to_year=2015),
        ]
    )
    with_end_range = str(year_ranges)
    assert with_end_range == "2008-2010,2012,2014-2015"
    year_ranges = YearRanges(
        [
            YearRange(from_year=2012),
            YearRange(from_year=2014, to_year=2015),
            YearRange(from_year=2008, to_year=2010),
        ]
    )
    assert with_end_range == "2008-2010,2012,2014-2015"


@pytest.mark.parametrize(
    "extension,source_class",
    [
        (
            "py",
            PythonSourceFile,
        ),
        (
            "yaml",
            YamlSourceFile,
        ),
        (
            "yml",
            YamlSourceFile,
        ),
        (
            "xml",
            XmlSourceFile,
        ),
        (
            "c",
            CSourceFile,
        ),
        (
            "js",
            JavaScriptSourceFile,
        ),
        (
            "ts",
            TypeScriptSourceFile,
        )
    ],
)
def test_get_source_file_by_file_type(extension, source_class):

    klass = SourceFile.get_source_file_by_file_type(extension)
    assert source_class == klass


def test_get_source_file_by_file_type_unsupported():

    with pytest.raises(ValueError):
        SourceFile.get_source_file_by_file_type("unsupported")


def test_copyright_check_py(valid_py_file, invalid_year_py_file):
    assert CopyrightChecker().check_file(valid_py_file)
    assert not CopyrightChecker().check_file(invalid_year_py_file)


def test_copyright_check_c(valid_c_file, invalid_year_c_file):
    assert CopyrightChecker().check_file(valid_c_file)
    assert not CopyrightChecker().check_file(invalid_year_c_file)


def test_copyright_index(valid_py_file):
    source = PythonSourceFile(file_path=valid_py_file)
    assert source.get_copyright_index() == 3


def test_fix_copyright(invalid_year_py_file, missing_copyright_py_file):
    source = PythonSourceFile(file_path=invalid_year_py_file)
    assert source.check() == CheckResult.INVALID_YEAR
    source.fix()
    assert source.check() == CheckResult.SUCCEEDED
    source = PythonSourceFile(file_path=missing_copyright_py_file)
    assert source.check() == CheckResult.NO_COPYRIGHT
    source.fix()
    assert source.check() == CheckResult.SUCCEEDED


def test_copyright_check_file_not_found():

    python_source = PythonSourceFile("/this/file/does/not/exist.py")
    assert python_source.check() == CheckResult.FILE_NOT_FOUND


@pytest.mark.parametrize("pyproject_toml", [{"excluded_files": ["invalid_year.py"]}], indirect=True)
def test_pyproject_toml_excluded_files(
    pyproject_toml: str, invalid_year_py_file: str, missing_copyright_py_file: str
):
    checker = CopyrightChecker(os.path.dirname(pyproject_toml))

    assert checker.check_files([invalid_year_py_file]) == 0
    assert checker.check_files([invalid_year_py_file, missing_copyright_py_file]) == 1


@pytest.mark.parametrize("pyproject_toml", [{"ignored_results": ["INVALID_YEAR"]}], indirect=True)
def test_pyproject_toml_ignored_results_files(
    pyproject_toml: str, invalid_year_py_file: str, missing_copyright_py_file: str
):
    checker = CopyrightChecker(os.path.dirname(pyproject_toml))

    assert checker.check_file(invalid_year_py_file)
    assert not checker.check_file(missing_copyright_py_file)


@pytest.mark.parametrize(
    "source_class,ref_comment",
    [
        (
            PythonSourceFile,
            "# Copyright 2025 NXP\n#\n# SPDX-License-Identifier: BSD-3-Clause",
        ),
        (
            YamlSourceFile,
            "# Copyright 2025 NXP\n#\n# SPDX-License-Identifier: BSD-3-Clause",
        ),
        (
            XmlSourceFile,
            "<!--\n  Copyright 2025 NXP\n  \n  SPDX-License-Identifier: BSD-3-Clause\n-->",
        ),
        (
            CSourceFile,
            " * Copyright 2025 NXP\n *\n * SPDX-License-Identifier: BSD-3-Clause",
        ),
        (
            JavaScriptSourceFile,
            " * Copyright 2025 NXP\n *\n * SPDX-License-Identifier: BSD-3-Clause",
        ),
        (
            TypeScriptSourceFile,
            " * Copyright 2025 NXP\n *\n * SPDX-License-Identifier: BSD-3-Clause",
        ),
    ],
)
def test_comment_text(source_class: Type[SourceFile], ref_comment: str):
    text_to_comment = "Copyright 2025 NXP\n\nSPDX-License-Identifier: BSD-3-Clause"
    comment = source_class.comment_text(text_to_comment)
    assert comment == ref_comment


@pytest.mark.parametrize(
    "ref_text, fixed_text",
    [
        ("ABC", "ABC\n"),
        ("ABC\n", "ABC\n"),
        ("ABC\n\n", "ABC\n\n"),
    ],
)
def test_fix_trailing_newline(ref_text, fixed_text):
    fixed = SourceFile.fix_trailing_newline(ref_text)
    assert fixed == fixed_text
