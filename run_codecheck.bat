@echo off
REM ============================================================================
REM Copyright 2026 NXP
REM
REM SPDX-License-Identifier: BSD-3-Clause
REM ============================================================================
REM Run codecheck sequentially for every SPSDK plugin in this repository.
REM
REM Usage:
REM   run_codecheck.bat            Run codecheck for all plugins.
REM   run_codecheck.bat jlink      Run codecheck only for the given plugin(s).
REM
REM The script iterates over each plugin sub-directory (identified by the
REM presence of a pyproject.toml), enters it, and runs "codecheck -f".
REM A non-zero exit code from any plugin is remembered and returned at the end,
REM but the remaining plugins are still checked so you get a full picture.
REM ============================================================================

setlocal enabledelayedexpansion

set "ROOT=%~dp0"
set "OVERALL_RC=0"
set "PLUGIN_LIST=%*"

REM If specific plugins are requested on the command line use them, otherwise
REM discover all plugin directories that contain a pyproject.toml.
if "%PLUGIN_LIST%"=="" (
    set "PLUGINS="
    for /d %%D in ("%ROOT%*") do (
        if exist "%%D\pyproject.toml" (
            set "PLUGINS=!PLUGINS! %%~nxD"
        )
    )
) else (
    set "PLUGINS=%PLUGIN_LIST%"
)

echo ============================================================================
echo Running codecheck for plugins:!PLUGINS!
echo ============================================================================

for %%P in (!PLUGINS!) do (
    set "PLUGIN_DIR=%ROOT%%%P"
    if exist "!PLUGIN_DIR!\pyproject.toml" (
        echo.
        echo ----------------------------------------------------------------------------
        echo [codecheck] %%P
        echo ----------------------------------------------------------------------------
        pushd "!PLUGIN_DIR!"
        call codecheck -f
        if errorlevel 1 (
            echo [codecheck] FAILED for plugin %%P
            set "OVERALL_RC=1"
        ) else (
            echo [codecheck] PASSED for plugin %%P
        )
        popd
    ) else (
        echo [codecheck] SKIP %%P ^(no pyproject.toml found^)
    )
)

echo.
echo ============================================================================
if "!OVERALL_RC!"=="0" (
    echo All plugins passed codecheck.
) else (
    echo One or more plugins reported codecheck findings. See output above.
)
echo ============================================================================

endlocal & exit /b %OVERALL_RC%
