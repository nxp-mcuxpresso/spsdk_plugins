#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
import os
import pytest
import datetime

import tomli_w

PY_VALID_COPYRIGHT = f"""#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright {datetime.datetime.now().year} NXP
#
# SPDX-License-Identifier: BSD-3-Clause

print("Test me")"""

C_VALID_COPYRIGHT = f"""/*
 * Copyright {datetime.datetime.now().year} NXP
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */
#include <stdio.h>

int main() {{
    printf("Test me");
    return 0;
}}"""


PY_INVALID_COPYRIGHT_YEAR = f"""#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright {datetime.datetime.now().year - 1} NXP
#
# SPDX-License-Identifier: BSD-3-Clause

print("Test me")"""

C_INVALID_COPYRIGHT_YEAR = f"""/*
 * Copyright {datetime.datetime.now().year -1} NXP
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */
#include <stdio.h>

int main() {{
    printf("Test me");
    return 0;
}}"""

PY_MISSING_COPYRIGHT = f"""#!/usr/bin/env python
# -*- coding: UTF-8 -*-

print("Test me")"""


@pytest.fixture
def valid_py_file(tmp_path):
    path = os.path.join(tmp_path, f"valid.py")
    with open(path, mode="w") as f:
        f.write(PY_VALID_COPYRIGHT)
    return path


@pytest.fixture
def valid_c_file(tmp_path):
    path = os.path.join(tmp_path, f"valid.c")
    with open(path, mode="w") as f:
        f.write(C_VALID_COPYRIGHT)
    return path


@pytest.fixture
def invalid_year_c_file(tmp_path):

    path = os.path.join(tmp_path, f"invalid_year.c")
    with open(path, mode="w") as f:
        f.write(C_INVALID_COPYRIGHT_YEAR)
    return path


@pytest.fixture
def invalid_year_py_file(tmp_path):

    path = os.path.join(tmp_path, f"invalid_year.py")
    with open(path, mode="w") as f:
        f.write(PY_INVALID_COPYRIGHT_YEAR)
    return path


@pytest.fixture
def missing_copyright_py_file(tmp_path):

    path = os.path.join(tmp_path, f"missing_copyright.py")
    with open(path, mode="w") as f:
        f.write(PY_MISSING_COPYRIGHT)
    return path


@pytest.fixture
def pyproject_toml(tmp_path, request):
    data = {"tool": {"copyright": {}}}
    copyright_cfg = data["tool"]["copyright"]
    if "excluded_files" in request.param:
        copyright_cfg["excluded_files"] = request.param["excluded_files"]
    if "ignored_results" in request.param:
        copyright_cfg["ignored_results"] = request.param["ignored_results"]
    pyproject_toml = os.path.join(tmp_path, "pyproject.toml")
    with open(pyproject_toml, "wb") as f:
        tomli_w.dump(data, f)
    return pyproject_toml
