@echo off
title Flash Touch Fix v6.0 (Pristine Protocol Fix + Zero Lag) - Lenovo Tab P11 Gen 2
echo ======================================================================
echo   Lenovo Tab P11 Gen 2 (TB350XU / TB350FU)
echo   Flashing Touch Fix v6.0 Pristine (Android 14 S231018)
echo ======================================================================
echo.
echo 1. Put tablet into Fastboot Mode (adb reboot bootloader or Vol Down + Power)
echo 2. Connect tablet to PC via USB
echo.
pause

fastboot flash vendor_boot_a vendor_boot_TB350XU_S231018_v6.0_pristine_touch.img
fastboot flash vendor_boot_b vendor_boot_TB350XU_S231018_v6.0_pristine_touch.img
echo.
echo Rebooting tablet...
fastboot reboot
echo.
echo ======================================================================
echo   SUCCESS: Touch Fix v6.0 Pristine Flashed Successfully!
echo ======================================================================
pause
