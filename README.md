# Lenovo Tab P11 Gen 2 (`TB350XU` / `TB350FU`) — Touch & Typing Fix (`Android 14 S231018`)

[![ROM](https://img.shields.io/badge/ROM-Android%2014%20(S231018)-blue.svg)](docs/S231018_VERIFICATION_REPORT.md)
[![Hardware](https://img.shields.io/badge/SoC-MediaTek%20Helio%20G99%20%7C%20HX83102J-orange.svg)](docs/ALL_VERIFIED_BUGS.md)
[![Root](https://img.shields.io/badge/Root-APatch%20%7C%20KernelSU%20%7C%20Magisk-green.svg)](#step-3-install-root-module)
[![License](https://img.shields.io/badge/License-GPL%202.0-lightgrey.svg)](docs/ROLLBACK.md)

Complete kernel (`vendor_boot` -> `himax_mmi.ko`) and userspace (`APatch` / `Magisk` / `KernelSU` module) fix for touchscreen freezes, dropped typing keystrokes, disabled High-Sensitivity mode (`HSEN`), PowerHAL clock resets, and Precision Pen 2 stroke wobble on the **Lenovo Tab P11 Gen 2** running stock **Android 14 S231018**.

**Core Behavior Preserved:**
- Native Settings refresh rate selector (`60Hz / Auto / 120Hz`) remains unlocked (no forced 120Hz lock).
- Stock hardware vibration (`soc:regulator_vibrator`) remains enabled and untouched.
- Native `EDGE` interrupt trigger (`0x2002`) matching S231018 firmware is preserved (no forced Level-Low sticky releases).

---

## 1. Supported Hardware & Software

| Item | Verified Specification |
| :--- | :--- |
| **Models** | Lenovo Tab P11 (2nd Gen) — `TB350XU` (LTE) & `TB350FU` (Wi-Fi) |
| **SoC / Clusters / GPU** | MediaTek Helio G99 (`MT6789`) — `policy0` (6x A55, 500–2000 MHz), `policy6` (2x A76, 725–2200 MHz), Mali-G57 MC2 (`13000000.mali`, 390–1100 MHz) |
| **Target Stock ROM** | `TB350XU_USER_S231018_2601050930_MP_ROW` (`TB350XU_S231018_260105_ROW`, Android 14) |
| **Kernel Vermagic** | `5.10.233-android12-9-g9568a331d924 SMP preempt mod_unload modversions aarch64` *(MTK GKI 5.10 kernel branch running Android 14 S231018)* |
| **Touch Controller & Panel** | Himax `HX83102J`, `Huaqin_BOE`, Project `Tulip_AX6298`, `FW_VER = 0xC402`, Driver `2.1.0.2_Tulip_01` |
| **SPI & Interrupt Lines** | `IRQ 72` (`1100a000.spi0`), `IRQ 206` (`mtk-eint 54 Edge himax_tp`), nodes `himax-touchscreen` & `himax-stylus` |
| **Partitions & Boot State** | A/B layout (`vendor_boot_a` / `vendor_boot_b`), unlocked bootloader (`orange`), `veritymode = enforcing` |
| **Tested Root Stack** | APatch (`11282` / `0.13.9`), compatible with KernelSU & Magisk; tested alongside `zygisksu`, `playintegrityfix`, `magic_mount`, `zygisk-assistant`, and `zygisk_shamiko` |

---

## 2. Architecture (Two Required Layers)

Both layers are needed together on S231018: patching only the userspace module leaves kernel `InputReader (0x35/0x36)` drops and disabled `HSEN`; patching only `vendor_boot` leaves the `200ms` SurfaceFlinger timer regression and PowerHAL resetting GPU/CPU/`thrm_enable` floors after app switches.

```text
Layer 1 — Kernel Driver (vendor_boot -> lib/modules/himax_mmi.ko)
  [P1+P2 / H1] 0x11938, 0x119C8 : Propagate SPI read error status instead of hardcoded return 1
  [P3 / H2]    0x23650          : Reject truncated SPI reads (actual_length != len + 3 -> -EIO + unlock)
  [P4+P5/H3+H4]0x0484C, 0x04AEC : Clear all active touch slots before SPI / exception resets
  [P6]         0x04BC0          : Fix prevent_notch recovery buffer offset (#0x3C -> #0x4C)
  [P7 / H5]    0x1A514          : Enable High-Sensitivity mode (0x10007F14 = 0xA55AA55A) on boot & resume
  [P9 / H7]    0x037B8          : Check both p_point_num and pre_finger_mask ([x20, #0x90]) on lift
  [P10 / H6]   0x03610, 0x036AC : Emit input_mt_report_slot_state before coordinates & attributes
  [Native IRQ] 0x23C8C..0x23CA0 : Preserve hardware Edge trigger mode (0x2002)

Layer 2 — Android Input, Display & PowerHAL (magisk_module -> tb350xu-s231018-touch-fix.zip)
  system.prop : Restore ro.surface_flinger.set_touch_timer_ms=2000 (was 200ms)
                windowsmgr.max_events_per_sec=240, ro.surface_flinger.set_idle_timer_ms=1000,
                debug.sf.disable_backpressure=1
  /system/usr/idc/ : himax-touchscreen.idc (pressure.calibration=none, size.calibration=diameter)
                     himax-stylus.idc (Precision Pen 2 touchScreen/spots, 4096 pressure, filter=2)
  service.sh  : Zero-fork backlight poll (2s awake / 5s asleep) restores drifted awake floors
                (policy0 >= 1200000, policy6 >= 1400000, sugov_ext down=30000us, gpu_bottom >= 648000,
                 fpsgo_enable=0, thrm_enable=0, top-app/cpu.uclamp.latency_sensitive=1)
                without downgrading active PowerHAL boosts; sleeps at 500/725/390MHz when screen off;
                sets /proc/game_mode=0 once per wake (no 2s SPI read loop or dmesg spam)
```

---

## 3. Summary of All 24 Verified Issues

Full disassembly offsets, relocation details, and live telemetry are documented in [`docs/ALL_VERIFIED_BUGS.md`](docs/ALL_VERIFIED_BUGS.md) and [`docs/S231018_VERIFICATION_REPORT.md`](docs/S231018_VERIFICATION_REPORT.md).

| Bug ID(s) | Subsystem | Finding / Root Cause on S231018 | Resolution |
| :--- | :--- | :--- | :--- |
| **BUG-01** | `hx83102j_read_event_stack` | Ignores `himax_bus_read()` result and returns `1` | Fixed (`H1` via `[sp+0]`) |
| **BUG-02** | `himax_bus_read` | Skips `spi_message.actual_length` validation | Fixed (`H2` -> `-EIO` + unlock) |
| **BUG-03** | `himax_ts_work` | Missing pre-reset contact cleanup before resets | Fixed (`H3`, `H4` -> `0x054E8`) |
| **BUG-04** | `himax_ts_work` | Wrong `prevent_notch` struct offset (`#0x3c`) | Fixed (`P6` -> `#0x4c`) |
| **BUG-05** | `himax_mcu_resend_cmd_func` | `HSEN` (`0x10007F14`) stays `0x00000000` | Fixed (`H5` -> `0x5A 0xA5 0x5A 0xA5`) |
| **BUG-06 / 07 / 08** | FW / BSS / Mutex | Palm-pen priority lock, symbol alignment, SPI mutex scope | Mitigated / Benign / Preserved |
| **BUG-09** | `request_threaded_irq` | Older Level-Low (`0x2008`) override vs hardware `EDGE` mode | Intentionally omitted on S231018 |
| **BUG-10 / 19** | `himax_report_data` | Release branch checked `p_point_num` only (`pre_finger_mask` ignored) | Fixed (`H7`: ORs `[x20, #0x90]`) |
| **BUG-11 / 12 / 24** | InputReader `.idc` | Pressure threshold lag, motion smoothing, dead `himax_tp.idc` | Fixed in `/system/usr/idc/` |
| **BUG-13 / 20** | `himax_report_data` | `0x35/0x36` sent before tracking ID; `.rela.text.himax_report_data_init` safety | Fixed (`H6` + `sym 1496` reloc) |
| **BUG-14 / 21** | SurfaceFlinger | Old module `set_touch_timer_ms=200` dropped refresh between taps | Fixed (`2000ms`); native RR kept |
| **BUG-15 / 22** | FPSGO / MTK PowerHAL | `mtkpower@1.0-service` resets clocks, GPU, `thrm_enable`, and `sugov_ext` | Fixed (2s awake guard loop) |
| **BUG-16 / 17** | SystemUI / Pen 2 | Window blur shader stall; stylus treated as `pointer` | Fixed (`disable_window_blurs=1` + IDC) |
| **BUG-18** | Vibrator Driver | Legacy `soc:regulator_vibrator` unbind / haptics mute | Removed (S231018 haptics are clean) |
| **BUG-23** | `/proc/game_mode` | Reading `/proc/game_mode` in loop floods SPI & `[HXTP][ERROR]` logs | Fixed (one-shot `echo 0` on wake) |

---

## 4. Step-by-Step Installation Guide (`S231018`)

### Prerequisites
- Stock Android 14 ROM **`TB350XU_USER_S231018_2601050930_MP_ROW`** (`TB350XU_S231018_260105_ROW`).
- Unlocked bootloader (`fastboot getvar unlocked` = `yes`). **Never relock the bootloader with patched images.**
- Python 3.10+ with `capstone` and `lz4` (`pip install capstone lz4`) plus Android `adb` and `fastboot`.
- Root manager installed (**APatch**, **KernelSU**, or **Magisk**).

### Step 1: Build & Verify `vendor_boot` Image
From stock `TB350XU_USER_S231018_2601050930_MP_ROW\image\vendor_boot.img` (`0c06ebe1...`):
```bash
python tools/patch_vendor_boot.py \
  --stock-vendor-boot "TB350XU_USER_S231018_2601050930_MP_ROW/image/vendor_boot.img" \
  --out-img "vendor_boot_TB350XU_S231018_touch_fix.img"
```
Confirm the SHA-256 matches [`SHA256SUMS.txt`](SHA256SUMS.txt):
- `vendor_boot_TB350XU_S231018_touch_fix.img` = `f570272f25a1c2354b60469cda6e163c56c149f5f84f2ebf0cddc21565c77402`

### Step 2: Flash `vendor_boot` (Active Slot First)
1. Reboot to fastboot and check current active slot:
   ```cmd
   adb reboot bootloader
   fastboot devices
   fastboot getvar current-slot
   fastboot getvar unlocked
   ```
2. Flash the active slot first (`_a` shown; use `_b` if `current-slot: b`) and boot to test while leaving the other slot as an untouched fallback:
   ```cmd
   fastboot flash vendor_boot_a vendor_boot_TB350XU_S231018_touch_fix.img
   fastboot reboot
   ```
   *(Or use `tools\flash_vendor_boot.cmd` interactively.)*
   After verifying touch/typing works cleanly, you can optionally mirror the image to `vendor_boot_b` too.

### Step 3: Install Root Module
1. Use [`releases/tb350xu-s231018-touch-fix.zip`](releases/tb350xu-s231018-touch-fix.zip) (or regenerate identically with `python tools/pack_module.py`).
2. In **APatch** / **Magisk** / **KernelSU Manager** -> **Modules** -> **Install**, flash `tb350xu-s231018-touch-fix.zip`.
3. Reboot once so `system.prop`, `/system/usr/idc/*.idc`, and `service.sh` load (`customize.sh` automatically schedules removal of older `helio_g99_oc` or `tb350xu_master_touch_fix` module folders if present).

### Step 4: Verify Live Hardware & Input Behavior
Via `adb shell su`:
```sh
# 1. Confirm HSEN (0x10007F14) is ACTIVE (0x5A 0xA5 0x5A 0xA5)
echo "register,r:x10007F14" > /proc/android_touch/debug && cat /proc/android_touch/debug | head -n 3

# 2. Confirm native Edge trigger mode and loaded driver
echo "int" > /proc/android_touch/debug && cat /proc/android_touch/debug
lsmod | grep himax_mmi

# 3. Confirm 2000ms SurfaceFlinger touch timer and unlocked Settings refresh rate
getprop ro.surface_flinger.set_touch_timer_ms
settings get system min_refresh_rate
settings get system peak_refresh_rate

# 4. Confirm PowerHAL-resistant awake floors and clean kernel log
head -n 1 /sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq \
          /sys/devices/system/cpu/cpufreq/policy6/scaling_min_freq \
          /sys/devices/system/cpu/cpufreq/policy0/sugov_ext/down_rate_limit_us \
          /sys/module/ged/parameters/gpu_bottom_freq \
          /sys/kernel/fpsgo/fbt/thrm_enable \
          /dev/cpuctl/top-app/cpu.uclamp.latency_sensitive
dmesg | grep -iE "HXTP|himax" | tail -n 10

# 5. Confirm zero InputReader coordinate ordering warnings after typing
logcat -d -s InputReader:W
```

---

## 5. Documentation & Tools Index
- Bug inventory (`BUG-01..BUG-24`): [`docs/ALL_VERIFIED_BUGS.md`](docs/ALL_VERIFIED_BUGS.md)
- Live hardware verification report: [`docs/S231018_VERIFICATION_REPORT.md`](docs/S231018_VERIFICATION_REPORT.md)
- Rollback & recovery guide: [`docs/ROLLBACK.md`](docs/ROLLBACK.md)
- Bootloader & AVB analysis: [`docs/BOOTLOADER_AND_AVB_FEASIBILITY.md`](docs/BOOTLOADER_AND_AVB_FEASIBILITY.md)
- Sensitivity / `HSEN` analysis: [`docs/SENSITIVITY_RESEARCH_AND_TUNING.md`](docs/SENSITIVITY_RESEARCH_AND_TUNING.md)
- USB power & resume flow: [`docs/USB_POWER_AND_RESUME_ANALYSIS.md`](docs/USB_POWER_AND_RESUME_ANALYSIS.md)
- Changelog: [`docs/CHANGELOG.md`](docs/CHANGELOG.md)
- Live touch log monitor: [`tools/monitor_touch.py`](tools/monitor_touch.py) / [`tools/monitor_touch.cmd`](tools/monitor_touch.cmd)
