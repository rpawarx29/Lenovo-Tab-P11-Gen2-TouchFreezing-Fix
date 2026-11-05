#!/usr/bin/env python3
"""
Himax TB350XU Touch Subsystem & Recovery Real-Time Monitor
Part of the Lenovo Tab P11 Gen 2 Himax Touch Engineering Project.

This tool monitors:
- Normal touch / stylus operations (coordinate reporting, contact counts)
- Driver communication errors (SPI bus read/write failures, checksum errors)
- Recovery attempts (hardware reset, exception recovery, zero-event triggers)
- Contact release invocations (finger leave reporting)
- Mode and configuration restoration (USB plug status, suspend/resume, HSEN)
- IRQ rates and hardware activity (even when touches are quiet)

READ-ONLY: Does NOT alter partitions, flash images, or reboot the device.
"""

import sys, os, time, subprocess, re, argparse
from datetime import datetime

# Regex patterns for Himax kernel messages
PATTERNS = {
    # Normal operation
    'FINGER_DATA': re.compile(r'\[HXTP\].*Finger\s+(\d+)=>.*X:(\d+),\s*Y:(\d+).*W:(\d+),\s*Z:(\d+)', re.IGNORECASE),
    'FINGER_COUNT': re.compile(r'\[HXTP\].*start hx_touch_data->finger_num=(\d+)', re.IGNORECASE),
    'STYLUS_COUNT': re.compile(r'\[HXTP\].*start hx_touch_data->stylus_num=(\d+)', re.IGNORECASE),
    'STYLUS_VALID': re.compile(r'\[HXTP\].*stylus valid=(\d+)', re.IGNORECASE),
    'STYLUS_BTN': re.compile(r'\[HXTP\].*BTN_STYLUS.*status is (\d+)', re.IGNORECASE),
    'ALL_LEAVE': re.compile(r'\[HXTP\].*All Finger leave', re.IGNORECASE),
    'POINT_LEAVE': re.compile(r'\[HXTP\].*himax_point_leave', re.IGNORECASE),
    'STYLUS_LEAVE': re.compile(r'\[HXTP\].*himax_stylus_leave', re.IGNORECASE),

    # Errors & Communication Faults
    'CHECKSUM_ERR': re.compile(r'\[HXTP\].*data_checksum not match', re.IGNORECASE),
    'BUS_ERR': re.compile(r'\[HXTP\]\[ERROR\].*bus|spi|transfer|i2c', re.IGNORECASE),
    'GENERIC_ERR': re.compile(r'\[HXTP\]\[ERROR\](.*)', re.IGNORECASE),
    'SHORT_READ': re.compile(r'short SPI|actual_length != requested', re.IGNORECASE),
    'ZERO_EVENT': re.compile(r'zero_event_count|zero event', re.IGNORECASE),

    # Recovery Actions
    'EXCP_RESET': re.compile(r'HX_EXCP_RESET_ACTIVATE|ic_excp_recovery|excp_ic_reset', re.IGNORECASE),
    'HW_RESET': re.compile(r'HX_HW_RESET_ACTIVATE|system_reset|pin_reset', re.IGNORECASE),
    'RELOAD_ACTIVE': re.compile(r'reload_to_active|program_reload', re.IGNORECASE),
    'RELEASE_BEFORE_RESET': re.compile(r'himax_report_all_leave_event.*before reset', re.IGNORECASE),

    # Mode / Power / USB Changes
    'USB_IN': re.compile(r'\[HXTP\].*USB detect status IN', re.IGNORECASE),
    'USB_OUT': re.compile(r'\[HXTP\].*USB detect status OUT', re.IGNORECASE),
    'CABLE_CHANGE': re.compile(r'\[HXTP\].*Cable status change:\s*(0x[0-9a-fA-F]+)', re.IGNORECASE),
    'SUSPEND': re.compile(r'\[HXTP\].*in Suspend|himax suspend', re.IGNORECASE),
    'RESUME': re.compile(r'\[HXTP\].*resume|Already resumed', re.IGNORECASE),
    'RESEND_CMD': re.compile(r'himax_mcu_resend_cmd_func|resend_cmd', re.IGNORECASE),
    'HSEN_STATUS': re.compile(r'HSEN|high.sense', re.IGNORECASE),
    'PEN_MODE_ON': re.compile(r'\[HXTP\].*PEN mode is on', re.IGNORECASE),
    'HALL_STATUS': re.compile(r'\[HXTP\].*hall status is:\s*(\d+)', re.IGNORECASE),
}

class TerminalColors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    CYAN = '\033[36m'
    MAGENTA = '\033[35m'
    BLUE = '\033[34m'
    WHITE = '\033[37m'
    DIM = '\033[2m'

def colorize(text, color):
    if sys.platform == 'win32' and os.environ.get('TERM') != 'xterm':
        # Enable virtual terminal processing on Windows if possible
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            return text
    return f"{color}{text}{TerminalColors.RESET}"

def run_adb(cmd_list, timeout=10):
    """Execute adb command and return stdout string."""
    try:
        res = subprocess.run(['adb'] + cmd_list, capture_output=True, text=True, timeout=timeout)
        return res.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except FileNotFoundError:
        print("[!] ERROR: adb is not found in PATH. Please install Android Platform Tools.")
        sys.exit(1)

def check_adb_device():
    """Verify an ADB device is connected and authorized."""
    out = run_adb(['devices'])
    lines = [line.strip() for line in out.splitlines() if line.strip() and not line.startswith('List')]
    if not lines:
        print("[-] No ADB devices detected. Please connect tablet and enable USB debugging.")
        return False
    dev_info = lines[0].split()
    if len(dev_info) >= 2 and dev_info[1] == 'device':
        model = run_adb(['shell', 'getprop', 'ro.product.model'])
        build = run_adb(['shell', 'getprop', 'ro.build.display.id'])
        print(f"[+] Connected to: {model} ({dev_info[0]})")
        print(f"[+] Build: {build}")
        return True
    elif len(dev_info) >= 2 and dev_info[1] == 'unauthorized':
        print("[!] Device unauthorized. Please accept the USB debugging prompt on tablet screen.")
        return False
    else:
        print(f"[!] Device state: {dev_info}")
        return False

def get_touch_snapshot():
    """Take a snapshot of current touch subsystem state."""
    print("\n" + "=" * 70)
    print(" TOUCH SUBSYSTEM DIAGNOSTIC SNAPSHOT")
    print(" Time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    # 1. Check IRQ activity in /proc/interrupts
    irq_out = run_adb(['shell', 'cat /proc/interrupts 2>/dev/null | grep -iE "himax|touch|tpd|hx83102"'])
    print("\n[*] Touch IRQ Statistics (/proc/interrupts):")
    if irq_out:
        print(irq_out)
    else:
        print("    (No matching IRQ line found for himax/touch via normal shell)")

    # 2. Check touch proc nodes
    print("\n[*] Touch Driver Proc Nodes (/proc/android_touch/):")
    proc_files = ['vendor', 'support_pen', 'edge_grid_zone', 'HSEN', 'debug_level', 'game_mode']
    for p in proc_files:
        val = run_adb(['shell', f'cat /proc/android_touch/{p} 2>/dev/null || cat /proc/{p} 2>/dev/null'])
        if val:
            print(f"    - {p}: {val}")

    # 3. Check loaded himax module
    mod_out = run_adb(['shell', 'lsmod | grep -i himax'])
    print("\n[*] Kernel Module State:")
    if mod_out:
        print(f"    {mod_out}")
    else:
        print("    himax module not listed in lsmod (may be built-in or root required)")

    # 4. Check input devices
    print("\n[*] Registered Input Devices:")
    inp_out = run_adb(['shell', 'getevent -p 2>/dev/null | grep -E "add device|name:"'])
    if inp_out:
        for line in inp_out.splitlines():
            print(f"    {line.strip()}")

    # 5. Check recent touch dmesg log
    print("\n[*] Recent Himax Touch Kernel Messages (last 20 lines):")
    dmesg_recent = run_adb(['shell', 'su -c "dmesg | grep -iE \"HXTP|himax\" | tail -n 20" 2>/dev/null || dmesg | grep -iE "HXTP|himax" | tail -n 20'])
    if dmesg_recent:
        for l in dmesg_recent.splitlines():
            print(f"    {l}")
    else:
        print("    (dmesg requires root on production user builds; run with KernelSU root granted)")

    print("\n" + "=" * 70 + "\n")

def live_monitor():
    """Stream and categorize touch events in real time."""
    print("\n" + "=" * 70)
    print(" LIVE TOUCH & RECOVERY MONITOR")
    print(" Listening for touch events, communication errors, and recovery states...")
    print(" Press Ctrl+C to stop.")
    print("=" * 70)
    print("Legend:")
    print(f"  {colorize('[TOUCH]', TerminalColors.GREEN)}    : Normal finger contact or coordinates")
    print(f"  {colorize('[STYLUS]', TerminalColors.CYAN)}   : Stylus/pen event or button action")
    print(f"  {colorize('[RELEASE]', TerminalColors.BLUE)}  : Contact lift-off / finger leave")
    print(f"  {colorize('[MODE]', TerminalColors.YELLOW)}     : USB/Charger plug, Suspend/Resume, HSEN")
    print(f"  {colorize('[ERROR]', TerminalColors.RED)}    : SPI read failure, short read, CRC error")
    print(f"  {colorize('[RECOVERY]', TerminalColors.MAGENTA)} : Controller reset, exception recovery, reinit")
    print("-" * 70 + "\n")

    # Command to stream kernel logs: prefer su if available
    has_su = run_adb(['shell', 'su -c "id" 2>/dev/null'])
    if 'uid=0' in has_su:
        adb_proc = subprocess.Popen(['adb', 'shell', 'su', '-c', 'dmesg -w | grep --line-buffered -iE "HXTP|himax|touch|stylus"'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    else:
        # Fallback to logcat or standard dmesg
        adb_proc = subprocess.Popen(['adb', 'shell', 'logcat -v time -s Himax:V HXTP:V Touch:V InputReader:I *:S'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        for line in iter(adb_proc.stdout.readline, ''):
            line = line.strip()
            if not line:
                continue

            ts = datetime.now().strftime("%H:%M:%S")

            # Match patterns
            if PATTERNS['CHECKSUM_ERR'].search(line) or PATTERNS['BUS_ERR'].search(line) or PATTERNS['SHORT_READ'].search(line):
                print(f"[{ts}] {colorize('[ERROR]    ', TerminalColors.RED + TerminalColors.BOLD)} {line}")
            elif PATTERNS['EXCP_RESET'].search(line) or PATTERNS['HW_RESET'].search(line) or PATTERNS['RELOAD_ACTIVE'].search(line):
                print(f"[{ts}] {colorize('[RECOVERY] ', TerminalColors.MAGENTA + TerminalColors.BOLD)} {line}")
            elif PATTERNS['ALL_LEAVE'].search(line) or PATTERNS['POINT_LEAVE'].search(line) or PATTERNS['STYLUS_LEAVE'].search(line):
                print(f"[{ts}] {colorize('[RELEASE]  ', TerminalColors.BLUE)} {line}")
            elif PATTERNS['USB_IN'].search(line) or PATTERNS['USB_OUT'].search(line) or PATTERNS['CABLE_CHANGE'].search(line):
                print(f"[{ts}] {colorize('[USB/MODE] ', TerminalColors.YELLOW + TerminalColors.BOLD)} {line}")
            elif PATTERNS['SUSPEND'].search(line) or PATTERNS['RESUME'].search(line) or PATTERNS['HSEN_STATUS'].search(line):
                print(f"[{ts}] {colorize('[MODE]     ', TerminalColors.YELLOW)} {line}")
            elif PATTERNS['STYLUS_COUNT'].search(line) or PATTERNS['STYLUS_BTN'].search(line) or PATTERNS['STYLUS_VALID'].search(line) or PATTERNS['PEN_MODE_ON'].search(line):
                print(f"[{ts}] {colorize('[STYLUS]   ', TerminalColors.CYAN)} {line}")
            elif PATTERNS['FINGER_DATA'].search(line) or PATTERNS['FINGER_COUNT'].search(line):
                print(f"[{ts}] {colorize('[TOUCH]    ', TerminalColors.GREEN)} {line}")
            else:
                # Other Himax output
                print(f"[{ts}] {colorize('[INFO]     ', TerminalColors.DIM)} {line}")

    except KeyboardInterrupt:
        print("\n[*] Monitoring stopped.")
    finally:
        adb_proc.terminate()

def main():
    parser = argparse.ArgumentParser(description="Himax TB350XU Touch & Recovery Monitor")
    parser.add_argument('--snapshot', action='store_true', help="Take instantaneous state snapshot and exit")
    parser.add_argument('--monitor', action='store_true', help="Start live streaming monitor")
    args = parser.parse_args()

    print("=" * 70)
    print(" Himax TB350XU Touch Recovery & Subsystem Diagnostic Monitor")
    print("=" * 70)

    if not check_adb_device():
        sys.exit(1)

    if args.snapshot:
        get_touch_snapshot()
    elif args.monitor:
        live_monitor()
    else:
        # Interactive mode
        while True:
            print("\nSelect Diagnostic Action:")
            print("  1. Live Touch & Recovery Event Monitor (Real-Time)")
            print("  2. Take Instantaneous Touch Subsystem Snapshot")
            print("  3. Check Touch Screen Input Device Events (getevent)")
            print("  4. Save Complete Diagnostic Log to File")
            print("  5. Exit")
            choice = input("\nEnter choice (1-5): ").strip()

            if choice == '1':
                live_monitor()
            elif choice == '2':
                get_touch_snapshot()
            elif choice == '3':
                print("\n[*] Listening for raw touch events on /dev/input... (Touch the screen; Ctrl+C to stop)")
                try:
                    subprocess.run(['adb', 'shell', 'getevent -l 2>/dev/null'])
                except KeyboardInterrupt:
                    print("\n[*] getevent stopped.")
            elif choice == '4':
                fname = f"touch_diagnostic_{int(time.time())}.txt"
                print(f"[*] Dumping complete report to {fname}...")
                with open(fname, 'w', encoding='utf-8') as f:
                    f.write("=== HIMAX TB350XU TOUCH DIAGNOSTIC DUMP ===\n")
                    f.write(f"Date: {datetime.now().isoformat()}\n\n")
                    # Collect snapshot
                    f.write("--- DEVICES ---\n")
                    f.write(run_adb(['devices']) + "\n\n")
                    f.write("--- PROPS ---\n")
                    f.write(run_adb(['shell', 'getprop | grep -iE "touch|himax|pen|stylus"']) + "\n\n")
                    f.write("--- INTERRUPTS ---\n")
                    f.write(run_adb(['shell', 'cat /proc/interrupts | grep -iE "himax|touch|tpd"']) + "\n\n")
                    f.write("--- PROC ANDROID TOUCH ---\n")
                    f.write(run_adb(['shell', 'ls -la /proc/android_touch/ 2>/dev/null']) + "\n\n")
                    f.write("--- DMESG TOUCH ENTRIES ---\n")
                    f.write(run_adb(['shell', 'su -c "dmesg | grep -iE \"HXTP|himax\"" 2>/dev/null || dmesg | grep -iE "HXTP|himax"']) + "\n")
                print(f"[+] Saved report to: {os.path.abspath(fname)}")
            elif choice == '5':
                break
            else:
                print("[!] Invalid option.")

if __name__ == '__main__':
    main()
