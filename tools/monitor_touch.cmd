@echo off
setlocal
cd /d "%~dp0"
title Lenovo Tab P11 Gen 2 - Touch Subsystem Monitor

where adb >nul 2>&1
if errorlevel 1 (
    echo [!] adb.exe not found on PATH. Ensure Android platform-tools are available.
)

where python >nul 2>&1
if not errorlevel 1 (
    python "%~dp0monitor_touch.py"
    goto :eof
)

echo [!] Python not found. Falling back to raw ADB log stream...
adb devices
adb shell "su -c 'dmesg -w | grep -iE \"HXTP|himax|touch\"' || logcat -s InputReader:W *:S"
endlocal
