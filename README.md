# Lenovo Tab P11 Gen 2 (`TB350XU` / `TB350FU`)
## S231018 Ultimate Touch, Typing & Helio G99 Performance Suite (`v6.1.0-Ultimate`)

[![Release](https://img.shields.io/badge/Release-v6.1.0--Ultimate-brightgreen.svg)](docs/CHANGELOG.md)
[![Firmware](https://img.shields.io/badge/Primary%20ROM-S231018%20(Android%2014%20%7C%205.10.233)-blue.svg)](docs/S231018_ULTIMATE_VERIFICATION_REPORT.md)
[![Hardware](https://img.shields.io/badge/Chipset-MT6789%20Helio%20G99%20%7C%20HX83102J-orange.svg)](docs/ALL_VERIFIED_BUGS.md)
[![Support](https://img.shields.io/badge/Root-APatch%20%7C%20KernelSU%20%7C%20Magisk-red.svg)](#step-3-install-apatch--magisk--ksu-module)
[![License](https://img.shields.io/badge/License-GPL%202.0-yellow.svg)](docs/ROLLBACK.md)

The complete, hardware-verified two-layer fix for dropped keystrokes, touchscreen unresponsiveness, ghost/stuck multi-touch slots, disabled High-Sensitivity mode, PowerHAL clock throttling, and Precision Pen 2 stroke wobble on the **Lenovo Tab P11 Gen 2**.

> **Design Guarantee (`v6.1.0-Ultimate`):**
> - **Preserves native Display Refresh Rate settings (`60Hz / Auto / 120Hz`)** — NO forced 120Hz lock.
> - **Preserves stock hardware haptics (`soc:regulator_vibrator`)** — NO vibrator unbinding or muting.
> - **Preserves native `EDGE` IRQ mode (`0x2002`)** matching S231018 firmware — NO sticky key-release lag.

---

## 1. Exact Hardware, ROM & Software Compatibility

| Component | Verified Value / Specification |
| :--- | :--- |
| **Models** | Lenovo Tab P11 (2nd Gen) — **`TB350XU`** (LTE) & **`TB350FU`** (Wi-Fi) |
| **SoC / CPU / GPU** | MediaTek Helio G99 (`MT6789`) — 6x A55 (`500–2000 MHz`), 2x A76 (`725–2200 MHz`), Mali-G57 MC2 (`390–1100 MHz`) |
| **Primary Verified Stock ROM** | **`TB350XU_USER_S231018_2601050930_MP_ROW`** (`ro.build.display.id = TB350XU_S231018_260105_ROW`) |
| **Legacy Reference ROM** | Android 12 **`TB350XU_MT6789_USER_S020008_221025`** (`5.10.136`, documented in historical scripts) |
| **Kernel Vermagic (S231018)** | `5.10.233-android12-9-g9568a331d924 SMP preempt mod_unload modversions aarch64` |
| **Touch Controller & Panel** | Himax **`HX83102J`** (`Huaqin_BOE`, Project `Tulip_AX6298`, `FW_VER = 0xC402`, Driver `2.1.0.2_Tulip_01`) |
| **SPI / Interrupt Hardware** | `IRQ 72` (`1100a000.spi0`), `IRQ 206` (`mtk-eint 54 Edge himax_tp`), Input nodes `himax-touchscreen` & `himax-stylus` |
| **Partition & Boot State** | A/B layout (`vendor_boot_a` / `vendor_boot_b`), Unlocked bootloader (`orange`), `veritymode = enforcing` |
| **Root Environments** | **APatch** (`11282` / `0.13.9` tested), **KernelSU**, and **Magisk** (Zygisk + PIF + Shamiko stealth compatible) |

---

## 2. Two-Layer Architecture (Why Both Layers Were Needed)

Fixing either layer alone still left dropped typing keystrokes on S231018:

```text
+-----------------------------------------------------------------------------+
| LAYER 1: KERNEL DRIVER  (vendor_boot -> lib/modules/himax_mmi.ko)           |
|-----------------------------------------------------------------------------|
| [P1+P2] H1 @ 0x11938/0x119C8 : Propagate SPI read error status (no fake 1)  |
| [P3]    H2 @ 0x23650         : Reject short SPI reads (actual != len+3)     |
| [P4+P5] H3/H4 @ 0x0484C/0x04AEC : Clear all slots BEFORE SPI/excp resets    |
| [P6]    0x04BC0              : Fix prevent_notch offset (#0x3C -> #0x4C)    |
| [P7]    H5 @ 0x1A514         : Enable HSEN (0x10007F14 = 0xA55AA55A) awake  |
| [P9]    H7 @ 0x037B8         : Check p_point_num | pre_finger_mask on lift  |
| [P10]   H6 @ 0x03610/0x036AC : Emit ABS_MT_TRACKING_ID BEFORE X/Y/ATTRS     |
| [Edge]  0x23C8C..0x23CA0     : Keep native 0x2002 Edge IRQ (int_is_edge=1)  |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
| LAYER 2: ANDROID INPUT, SURFACEFLINGER & POWERHAL (magisk_module v6.1)      |
|-----------------------------------------------------------------------------|
| system.prop : Restore ro.surface_flinger.set_touch_timer_ms=2000 (was 200!) |
|               windowsmgr.max_events_per_sec=240, disable_backpressure=1     |
| /system/usr/idc/ : himax-touchscreen.idc (pressure=none, size=diameter)     |
|                    himax-stylus.idc (Pen 2 direct spots, 4096 pressure)     |
|                    (Removed obsolete duplicate himax_tp.idc)                |
| service.sh  : Backlight-based loop (0 extra forks) restores floors lost to  |
|               MTK PowerHAL (policy0>=1.2G, policy6>=1.4G, GPU>=648M,        |
|               sugov_ext down=30000us, fpsgo=0, thrm_enable=0, uclamp TA=1)  |
|               & sleeps cleanly at 500/725/390MHz on screen off              |
|               One-shot echo 0 > /proc/game_mode (no 2s SPI read flood!)    |
+-----------------------------------------------------------------------------+
```

---

## 3. Complete Summary of All 24 Investigated Bugs

Detailed instruction-level proofs live in [`docs/ALL_VERIFIED_BUGS.md`](docs/ALL_VERIFIED_BUGS.md) and [`docs/S231018_ULTIMATE_VERIFICATION_REPORT.md`](docs/S231018_ULTIMATE_VERIFICATION_REPORT.md).

| ID(s) | Area | Problem Summary | S231018 Resolution |
| :--- | :--- | :--- | :--- |
| **BUG-01** | `hx83102j_read_event_stack` | Ignored `himax_bus_read()` errors (`mov w0, #1`) | **Fixed (`H1`)** via unused `[sp+0]` |
| **BUG-02** | `himax_bus_read` | Ignored truncated `spi_message.actual_length` | **Fixed (`H2`)** -> `-EIO` + mutex unlock |
| **BUG-03** | `himax_ts_work` | Missing `himax_report_all_leave_event` before resets | **Fixed (`H3`, `H4`)** (`x19 = private_ts`) |
| **BUG-04** | `himax_ts_work` | Wrong `prevent_notch` buffer offset (`#0x3c` vs `#0x4c`) | **Fixed (`P6`)** at `0x04BC0` |
| **BUG-05** | `himax_mcu_resend_cmd_func` | High-Sensitivity (`HSEN` `0x10007F14`) never turned ON | **Fixed (`H5`)** -> `0x5A 0xA5 0x5A 0xA5` |
| **BUG-06 / 07 / 08** | FW / BSS / Mutex | Palm-stylus priority lock, `tp_usb_plug_status` padding, SPI mutex layout | **Mitigated / Verified Benign / Preserved** |
| **BUG-09** | `request_threaded_irq` | Legacy Android 12 Level-Low `0x2008` override | **Intentionally Omitted** (S231018 HW uses Edge `0x2002`) |
| **BUG-10 / 19** | `himax_report_data` | `cbz w8` skipped cleanup while `pre_finger_mask` active | **Fixed (`H7`)**: checks `w8 \| [x20, #0x90]` |
| **BUG-11 / 12 / 24** | InputReader `.idc` | `pressure.scale` 1s tap lag, smoothing filter, dead `himax_tp.idc` | **Fixed**: clean `/system/usr/idc/` overlay |
| **BUG-13 / 20** | `himax_report_data` | Coordinates (`0x35/0x36`) sent before `TRACKING_ID`; `.rela.text.himax_report_data_init` safety | **Fixed (`H6`)**: zero `0x35/0x36` drops, reloc-safe |
| **BUG-14 / 21** | Display / SurfaceFlinger | Old module `set_touch_timer_ms=200` dropped Hz between keystrokes (replacing forced 120Hz lock) | **Fixed**: restored `2000ms` timer; **no forced 120Hz lock** |
| **BUG-15 / 22** | FPSGO / MTK PowerHAL | `mtkpower@1.0-service` resets `gpu_bottom_freq`, `thrm_enable`, `scaling_min_freq`, `sugov_ext` | **Fixed**: 2s awake floor guard without fighting boosts |
| **BUG-16 / 17** | SystemUI / Pen 2 | Window blur shader stall; stylus classified as `pointer` | **Fixed**: `disable_window_blurs=1` + `himax-stylus.idc` |
| **BUG-18** | Platform Vibrator | Legacy A12 vibrator unbind/haptic mute | **Removed** (S231018 has no haptics issue; stock vibrator intact) |
| **BUG-23** | `/proc/game_mode` | Reading `/proc/game_mode` in loop triggers SPI reads & `[HXTP][ERROR]` `dmesg` spam | **Fixed**: one-shot `echo 0` at boot/wake only |

---

## 4. Complete Step-by-Step Setup Guide (S231018)

### Prerequisites
- Unlocked bootloader (`fastboot getvar unlocked` -> `yes`). **Never relock the bootloader.**
- Android 14 stock ROM **`TB350XU_USER_S231018_2601050930_MP_ROW`** (`TB350XU_S231018_260105_ROW`).
- Root manager installed (**APatch**, **KernelSU**, or **Magisk**).
- Python 3.10+ with `capstone` (`pip install capstone`) + Android `adb` & `fastboot`.

### Step 1: Build & Verify Patched `vendor_boot` Image
Place your stock `vendor_boot.img` (`0c06ebe186f39b1e...`) at the default path (or pass `--stock-vendor-boot <path>`) and run:
```bash
python tools/build_s231018_ultimate_touch.py \
  --stock-vendor-boot path/to/TB350XU_USER_S231018_2601050930_MP_ROW/image/vendor_boot.img \
  --out-img vendor_boot_TB350XU_S231018_ULTIMATE_TOUCH.img
```
Verify the built SHA-256 matches [`SHA256SUMS.txt`](SHA256SUMS.txt):
- `vendor_boot_TB350XU_S231018_ULTIMATE_TOUCH.img`: **`f570272f25a1c2354b60469cda6e163c56c149f5f84f2ebf0cddc21565c77402`**

### Step 2: Flash `vendor_boot` Safely (Active Slot First)
1. Boot into fastboot and confirm slot & lock state:
   ```cmd
   adb reboot bootloader
   fastboot devices
   fastboot getvar current-slot
   fastboot getvar unlocked
   ```
2. Flash your active slot **first** (`_a` shown; use `_b` if `current-slot: b`) and reboot to test before touching the backup slot:
   ```cmd
   fastboot flash vendor_boot_a vendor_boot_TB350XU_S231018_ULTIMATE_TOUCH.img
   fastboot reboot
   ```
   *(Or double-click/run `tools\FLASH_S231018_ULTIMATE_TOUCH.cmd`.)*
   Once confirmed working, you can optionally mirror to the inactive slot too (`fastboot flash vendor_boot_b vendor_boot_TB350XU_S231018_ULTIMATE_TOUCH.img`).

### Step 3: Install APatch / Magisk / KSU Module
Flash [`releases/TB350XU_Master_Touch_and_Performance_Fix.zip`](releases/TB350XU_Master_Touch_and_Performance_Fix.zip) (reproducible via `python tools/build_module_zip.py`, SHA-256 `8596ec6f390706df6f3802a9bf229db0928af63a206edc344d6f63e4a9c541d3`):
1. Open **APatch** / **Magisk** / **KernelSU Manager** -> **Modules** -> **Install**.
2. Select `releases/TB350XU_Master_Touch_and_Performance_Fix.zip`.
3. Reboot once so `system.prop`, `/system/usr/idc/*`, and `service.sh` activate.

*(Play Integrity & Banking Stealth Note: This module only mounts `/system/usr/idc/*.idc`, `system.prop`, and `service.sh`. It works cleanly alongside minimal Zygisk stacks such as `zygisksu` + `playintegrityfix` + `magic_mount` + `zygisk-assistant` + `zygisk_shamiko`.)*

### Step 4: Verify Live Hardware Behavior Over ADB
Run via `adb shell su`:
```sh
# 1. Verify HSEN (0x10007F14) is ACTIVE (0x5A 0xA5 0x5A 0xA5)
echo "register,r:x10007F14" > /proc/android_touch/debug && cat /proc/android_touch/debug | head -n 3

# 2. Verify Edge IRQ & loaded module
echo "int" > /proc/android_touch/debug && cat /proc/android_touch/debug
lsmod | grep himax_mmi

# 3. Verify SurfaceFlinger 2000ms touch timer & native refresh rate preserved
getprop ro.surface_flinger.set_touch_timer_ms
settings get system min_refresh_rate
settings get system peak_refresh_rate

# 4. Verify PowerHAL-resilient awake floors & clean dmesg (zero [HXTP][ERROR])
head -n 1 /sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq \
          /sys/devices/system/cpu/cpufreq/policy6/scaling_min_freq \
          /sys/devices/system/cpu/cpufreq/policy0/sugov_ext/down_rate_limit_us \
          /sys/module/ged/parameters/gpu_bottom_freq \
          /sys/kernel/fpsgo/fbt/thrm_enable \
          /dev/cpuctl/top-app/cpu.uclamp.latency_sensitive
dmesg | grep -iE "HXTP|himax" | tail -n 10

# 5. Type quickly on screen and confirm ZERO InputReader (0x35/0x36) errors
logcat -d -s InputReader:W
```

---

## 5. Rollback & Further Documentation
- Instant recovery steps: [`docs/ROLLBACK.md`](docs/ROLLBACK.md)
- Complete 24-bug forensic catalog: [`docs/ALL_VERIFIED_BUGS.md`](docs/ALL_VERIFIED_BUGS.md)
- Live S231018 verification & instruction map: [`docs/S231018_ULTIMATE_VERIFICATION_REPORT.md`](docs/S231018_ULTIMATE_VERIFICATION_REPORT.md)
- Full version history: [`docs/CHANGELOG.md`](docs/CHANGELOG.md)
- Formal manufacturer escalation report: [`docs/EXECUTIVE_ESCALATION_LETTER_TO_LENOVO.md`](docs/EXECUTIVE_ESCALATION_LETTER_TO_LENOVO.md)
- Bootloader & AVB analysis: [`docs/BOOTLOADER_AND_AVB_FEASIBILITY.md`](docs/BOOTLOADER_AND_AVB_FEASIBILITY.md)
- Real-time ADB diagnostic monitor (`tools/monitor_touch.py` / `tools/MONITOR_TOUCH_RECOVERY.cmd`)

---

## Credits
- **Author & Lead Reverse-Engineer:** Ruturaj Pawar ([@rpawarx29](https://github.com/rpawarx29))
- Hardware verification, ARM64 binary patching, and S231018 PowerHAL/InputReader stabilization completed on `TB350XU` (`HVA5R4L6`).
