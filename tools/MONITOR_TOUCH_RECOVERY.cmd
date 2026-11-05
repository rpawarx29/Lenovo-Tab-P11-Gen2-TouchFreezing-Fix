@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
title Himax TB350XU Touch Recovery Monitor

echo =====================================================================
echo   HIMAX TB350XU TOUCH SUBSYSTEM & RECOVERY MONITOR
echo   Target: Lenovo Tab P11 Gen 2 (TB350XU)
echo =====================================================================
echo.

where adb.exe >nul 2>&1
if errorlevel 1 (
    echo [!] WARNING: adb.exe not found on PATH.
    echo Please make sure Android platform-tools is installed and adb is in PATH.
    echo.
)

set "PY_BIN="
where python.exe >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%i in ('where python.exe') do (
        if not defined PY_BIN set "PY_BIN=%%i"
    )
)

if not defined PY_BIN (
    if exist "%~dp0..\extracted\Himax_Touch_Experimental_v2\Himax_Touch_Experimental_v2\runtime\python.exe" (
        set "PY_BIN=%~dp0..\extracted\Himax_Touch_Experimental_v2\Himax_Touch_Experimental_v2\runtime\python.exe"
    )
)

if defined PY_BIN (
    "%PY_BIN%" "%~dp0monitor_touch.py"
    goto end
)

echo [!] Python not detected. Running basic ADB diagnostic shell...
echo.
echo [*] Checking ADB connection:
adb devices
echo.
echo [*] Streaming Himax kernel logs (Ctrl+C to quit)...
adb shell "su -c 'dmesg -w | grep -iE \"HXTP|himax|touch\"' 2>/dev/null || logcat -s Himax:V HXTP:V InputReader:I *:S"

:end
pause
exit /b 0
