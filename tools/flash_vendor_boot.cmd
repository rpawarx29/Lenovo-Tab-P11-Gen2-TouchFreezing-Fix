@echo off
setlocal EnableDelayedExpansion
title TB350XU S231018 Touch Fix - Fastboot A/B Flasher

set "SCRIPT_DIR=%~dp0"
set "IMG_NAME=vendor_boot_TB350XU_S231018_touch_fix.img"

if exist "%~1" (
    set "IMG_PATH=%~1"
) else if exist "%SCRIPT_DIR%..\%IMG_NAME%" (
    set "IMG_PATH=%SCRIPT_DIR%..\%IMG_NAME%"
) else if exist "%SCRIPT_DIR%..\..\%IMG_NAME%" (
    set "IMG_PATH=%SCRIPT_DIR%..\..\%IMG_NAME%"
) else (
    echo [ERROR] Could not locate %IMG_NAME%.
    echo Run: python tools\patch_vendor_boot.py
    echo Or pass the image path as the first argument.
    exit /b 1
)

where fastboot >nul 2>&1
if %ERRORLEVEL%==0 (
    set "FASTBOOT=fastboot"
) else if exist "%SCRIPT_DIR%..\..\platform-tools-latest-windows\platform-tools\fastboot.exe" (
    set "FASTBOOT=%SCRIPT_DIR%..\..\platform-tools-latest-windows\platform-tools\fastboot.exe"
) else (
    echo [ERROR] fastboot.exe not found on PATH or workspace platform-tools.
    exit /b 1
)

echo ============================================================================
echo  Lenovo Tab P11 Gen 2 (TB350XU) - Android 14 S231018 Touch Fix Flasher
echo  Image: %IMG_PATH%
echo ============================================================================
"%FASTBOOT%" devices
for /f "tokens=2" %%S in ('"%FASTBOOT%" getvar current-slot 2^>^&1 ^| findstr /C:"current-slot:"') do set "CUR_SLOT=%%S"
for /f "tokens=2" %%U in ('"%FASTBOOT%" getvar unlocked 2^>^&1 ^| findstr /C:"unlocked:"') do set "UNLOCKED=%%U"

echo Active Slot: %CUR_SLOT%
echo Bootloader Unlocked: %UNLOCKED%
if /i not "%UNLOCKED%"=="yes" (
    echo [ABORT] Bootloader is NOT unlocked. Flashing modified vendor_boot is blocked.
    exit /b 1
)

if "%CUR_SLOT%"=="" (
    set "ACTIVE_PART=vendor_boot_a"
    set "INACTIVE_PART=vendor_boot_b"
) else (
    set "ACTIVE_PART=vendor_boot_%CUR_SLOT%"
    if /i "%CUR_SLOT%"=="a" (set "INACTIVE_PART=vendor_boot_b") else (set "INACTIVE_PART=vendor_boot_a")
)

echo.
echo [Step 1/2] Flashing active slot first (%ACTIVE_PART%) for safe verification...
"%FASTBOOT%" flash %ACTIVE_PART% "%IMG_PATH%"
if errorlevel 1 (
    echo [ERROR] Flashing %ACTIVE_PART% failed!
    exit /b 1
)

echo.
choice /M "[Step 2/2] Also flash inactive fallback slot (%INACTIVE_PART%)? (Recommend N until first boot verified)"
if errorlevel 2 goto :SKIP_B
"%FASTBOOT%" flash %INACTIVE_PART% "%IMG_PATH%"
if errorlevel 1 (
    echo [ERROR] Flashing %INACTIVE_PART% failed!
    exit /b 1
)

:SKIP_B
echo.
echo [DONE] Rebooting tablet...
"%FASTBOOT%" reboot
echo Rollback command if needed: fastboot flash %ACTIVE_PART% stock_vendor_boot.img
endlocal
