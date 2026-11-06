@echo off
echo ========================================================
echo Lenovo Tab P11 Gen 2 (TB350XU) Firmware S231018
echo Flashing Touch Candidate v6 (Type-B Multi-Touch Fix)
echo ========================================================
echo.

set PLATFORM_TOOLS="E:\RUTURAJ DO NOT DELETE\platform-tools-latest-windows\platform-tools"
set IMG="%~dp0final_output\vendor_boot_TB350XU_S231018_v6_touch_protocol_fix.img"

if not exist %IMG% (
    echo Error: Image not found at %IMG%
    pause
    exit /b 1
)

echo Checking fastboot devices...
%PLATFORM_TOOLS%\fastboot.exe devices
echo.

echo Flashing vendor_boot_a...
%PLATFORM_TOOLS%\fastboot.exe flash vendor_boot_a %IMG%
if errorlevel 1 (
    echo Failed flashing vendor_boot_a!
    pause
    exit /b 1
)

echo Flashing vendor_boot_b...
%PLATFORM_TOOLS%\fastboot.exe flash vendor_boot_b %IMG%
if errorlevel 1 (
    echo Failed flashing vendor_boot_b!
    pause
    exit /b 1
)

echo.
echo ========================================================
echo Candidate v6 successfully flashed to both slots!
echo Rebooting tablet...
echo ========================================================
%PLATFORM_TOOLS%\fastboot.exe reboot
pause
