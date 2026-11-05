@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
title Himax TB350XU Final Combined Candidate Builder v3.0

echo =====================================================================
echo   HIMAX TB350XU FINAL COMBINED CANDIDATE BUILDER
echo   Target: Lenovo Tab P11 Gen 2 (TB350XU)
echo =====================================================================
echo.

set "PY_BIN="

rem 1. Check system python
where python.exe >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%i in ('where python.exe') do (
        if not defined PY_BIN set "PY_BIN=%%i"
    )
)

rem 2. Check bundled runtime from extracted packages
if not defined PY_BIN (
    if exist "%~dp0..\extracted\Himax_Touch_Experimental_v2\Himax_Touch_Experimental_v2\runtime\python.exe" (
        set "PY_BIN=%~dp0..\extracted\Himax_Touch_Experimental_v2\Himax_Touch_Experimental_v2\runtime\python.exe"
    )
)
if not defined PY_BIN (
    if exist "%~dp0..\extracted\Himax_SPI_Recovery_Experimental_v1\Himax_SPI_Recovery_Experimental_v1\runtime\python.exe" (
        set "PY_BIN=%~dp0..\extracted\Himax_SPI_Recovery_Experimental_v1\Himax_SPI_Recovery_Experimental_v1\runtime\python.exe"
    )
)

if not defined PY_BIN (
    echo [ERROR] Python not found on PATH or in bundled package runtime.
    echo Please install Python 3.10+ or extract the runtime package.
    pause
    exit /b 1
)

echo [*] Using Python interpreter: "%PY_BIN%"
echo [*] Executing BUILD_FINAL.py...
echo.

"%PY_BIN%" "%~dp0BUILD_FINAL.py"

if errorlevel 1 (
    echo.
    echo [!] Build encountered an error. Check build_log.txt for details.
    pause
    exit /b 1
)

echo.
echo [*] Build completed successfully.
echo [*] Output: vendor_boot_himax_combined_final_candidate.img
echo [*] Check SHA256SUMS.txt and BUILD_REPORT_final.json.
echo.
pause
exit /b 0
