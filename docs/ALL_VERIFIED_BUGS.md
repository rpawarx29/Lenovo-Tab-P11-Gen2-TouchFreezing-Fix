# Verified Touch, Typing & Performance Bugs (`S231018` Android 14)

- **Target Hardware:** Lenovo Tab P11 Gen 2 (`TB350XU` LTE / `TB350FU` Wi-Fi)
- **SoC:** MediaTek Helio G99 (`MT6789`) — `policy0` (6x A55, 500–2000 MHz), `policy6` (2x A76, 725–2200 MHz), Mali-G57 MC2 (`13000000.mali`, 390–1100 MHz)
- **Touch Controller:** Himax `HX83102J` (`Huaqin_BOE`, `Tulip_AX6298`, `FW_VER = 0xC402`, Driver `2.1.0.2_Tulip_01`)
- **Stock ROM Analyzed:** `TB350XU_USER_S231018_2601050930_MP_ROW` (`TB350XU_S231018_260105_ROW`), Kernel vermagic `5.10.233-android12-9-g9568a331d924` *(MediaTek GKI 5.10 kernel branch running Android 14 S231018)*

---

## Summary Table (`BUG-01` through `BUG-24`)

| ID | Subsystem | Defect / Finding on S231018 | Location | Status & Fix |
| :--- | :--- | :--- | :--- | :--- |
| **BUG-01** | `himax_mmi.ko` | `hx83102j_read_event_stack` ignores `himax_bus_read` errors and returns hardcoded `mov w0, #1` | `.text + 0x11938`, `0x119C8` | **Fixed (`H1` / `P1+P2`)** |
| **BUG-02** | `himax_mmi.ko` | `himax_bus_read` skips `spi_message.actual_length` check after `spi_sync` returns `0` | `.text + 0x23650` | **Fixed (`H2` / `P3`)** |
| **BUG-03** | `himax_mmi.ko` | Missing `himax_report_all_leave_event` prior to SPI read-fail / exception resets | `.text + 0x0484C`, `0x04AEC` | **Fixed (`H3+H4` / `P4+P5`)** |
| **BUG-04** | `himax_mmi.ko` | `prevent_notch` recovery uses wrong pointer offset `ts + 0x3C` instead of `ts + 0x4C` | `.text + 0x04BC0` | **Fixed (`P6`)** |
| **BUG-05** | `himax_mmi.ko` | High-Sensitivity Mode (`HSEN`, `0x10007F14`) stays `0x00000000` on boot & resume | `.text + 0x1A514` | **Fixed (`H5` / `P7`)** |
| **BUG-06** | Controller FW | Firmware palm/stylus priority can stall finger packets if leave packets are missed | Packet parser / recovery | **Mitigated** by `H3`/`H4`/`H7` + clean `game_mode=0` |
| **BUG-07** | Symbol Layout | `mtk_charger_framework` writes 32-bit int to 1-byte `tp_usb_plug_status` | `.bss` alignment padding | **Verified Benign** (aligned padding before `private_ts`) |
| **BUG-08** | Driver Mutex | Multi-packet SPI mutex spans inside `himax_ts_work` vs bus reads | `private_ts + 0x210` | **Preserved Safely** (unlock verified on `-EIO` in `H2`) |
| **BUG-09** | `request_threaded_irq` | Older Level-Low (`0x2008`) IRQ experiment vs native hardware `EDGE` mode | `0x23C80..0x23CA0` | **Intentionally Omitted** on S231018 (uses native `0x2002` Edge IRQ) |
| **BUG-10** | `himax_mmi.ko` | Finger lift path only checks `p_point_num`, leaving stuck slots if masked | `.text + 0x037B8` | **Fixed (`H7` / `P9`)** (`p_point_num \| pre_finger_mask`) |
| **BUG-11** | `InputReader` IDC | Stock pressure scaling (`pressure.scale`) drops light/fast finger taps | `/system/usr/idc/` | **Fixed** (`touch.pressure.calibration = none`) |
| **BUG-12** | `InputReader` IDC | Motion smoothing filter dampens quick taps and small typing slides | `/system/usr/idc/` | **Fixed** (raw unfiltered touchscreen IDC) |
| **BUG-13** | `himax_mmi.ko` | Type-B `X/Y` coordinates emitted before `ABS_MT_TRACKING_ID` | `.text + 0x03610`, `0x036AC` | **Fixed (`H6` / `P10`)** (see `BUG-20` below) |
| **BUG-14** | Display Policy | Forced 120Hz lock workaround vs native refresh rate toggle | System settings | **Excluded by Choice**; fixed via `BUG-21` (`touch_timer=2000`) |
| **BUG-15** | DVFS / Thermal | MTK `fpsgo` & thermal limits throttling CPUs under touch load | `/sys/kernel/fpsgo/` | **Fixed** (`fpsgo_enable=0`, `thrm_enable=0`, `boost_ta=1`) |
| **BUG-16** | SystemUI / OTA | Broken blur scrim (`disable_window_blurs=0`) + Lenovo OTA stalls GPU | Global settings / PM | **Fixed** (`disable_window_blurs=1`, OTA disabled) |
| **BUG-17** | `InputReader` IDC | Precision Pen 2 classified as `pointer`, adding mouse jitter on diagonal lines | `himax-stylus.idc` | **Fixed** (`touchScreen` + `spots` + 12-bit scale + `filter.level=2`) |
| **BUG-18** | Platform Vibrator | Legacy `soc:regulator_vibrator` unbind / haptics mute | `/sys/class/leds/vibrator` | **Removed** (issue absent on S231018; stock haptics intact) |
| **BUG-19** | `himax_mmi.ko` | **S231018:** `himax_report_data` exit skips cleanup when `pre_finger_mask` non-zero | `0x037B8` -> `0x24A54` | **Fixed (`H7`)**: loads `ldrh w9, [x20, #0x90]` & ORs with `w8` |
| **BUG-20** | `himax_mmi.ko` | **S231018:** `.rela.text.himax_report_data_init` + PAC/SCS break naive slot fixes; stock drops `0x35/0x36` | `0x03610`, `0x036AC` | **Fixed (`H6`)**: appends reloc `sym 1496`, preserves `x8`/`x30`, tail -> `0x03594` |
| **BUG-21** | SurfaceFlinger | **S231018:** `set_touch_timer_ms=200` drops display cadence mid-typing (`stock=2000`) | `system.prop` | **Fixed**: restored `ro.surface_flinger.set_touch_timer_ms=2000` |
| **BUG-22** | MTK PowerHAL | **S231018:** `mtkpower@1.0-service` resets GPU/CPU/`thrm_enable`/`sugov_ext` after hints | Sysfs runtime drift | **Fixed**: 2s awake floor guard (`raise_if_lt`) + `down_rate_limit_us=30000` |
| **BUG-23** | `procfs` / SPI | **S231018:** Reading `/proc/game_mode` in loop triggers SPI reads & `[HXTP][ERROR]` dmesg spam | `/proc/game_mode` | **Fixed**: one-shot `echo 0 > /proc/game_mode` on boot/wake only |
| **BUG-24** | Overlay / IDC | **S231018:** Unused `himax_tp.idc` duplicate & non-existent `/data/system/devices/idc/` | `magisk_module/` | **Fixed**: removed `himax_tp.idc`; `/system/usr/idc/` only |

---

## Kernel Driver Fixes (`lib/modules/himax_mmi.ko` on S231018)

Original `.text` length: `0x249C8` (`149,960` bytes). Appended trampolines `H1..H7` occupy `0x249C8..0x24A64` (`+156` bytes).
Every inline overwrite sits at an instruction with **zero existing relocation entries** in `.rela.text.himax_report_data_init`.

### 1. BUG-01 (`[P1 + P2]` — `hx83102j_read_event_stack`)
- **Sites:** `.text + 0x11938` (`08714239 ldrb w8, [x8, #0x9c]`) -> `H1` (`0x249C8`), `.text + 0x119C8` (`mov w0, #1` -> `ldr w0, [sp]`)
- **Root Cause:** After `bl himax_bus_read` (`0x11930`), the return value in `w0` is ignored and the function always exits returning `1` (`true`), letting `himax_ts_work` parse uninitialized/stale stack data instead of triggering bus recovery.
- **Resolution:** Verified `[sp+0x00 .. sp+0x08)` is completely unused inside `hx83102j_read_event_stack`'s `0x60`-byte frame (`[sp+0x08..0x28]` store `timespec64`, `[sp+0x28..0x60]` hold stack canary and callee-saved registers). `H1` stores `(w0 == 0) ? 1 : 0` into `[sp]`, executes the displaced `ldrb`, and returns to `0x1193C`; epilogue `0x119C8` loads `[sp]` into `w0` cleanly before `autiasp; ret`.

### 2. BUG-02 (`[P3]` — `himax_bus_read`)
- **Site:** `.text + 0x23650` (`e203132a mov w2, w19`) -> `H2` (`0x249DC`)
- **Root Cause:** `spi_sync()` returns `0` whenever controller submission succeeds, even if DMA terminated short (`spi_message.actual_length < length + 3`).
- **Resolution:** In `himax_bus_read`, `struct spi_message msg` is at `x29 - 0x78` and `actual_length` sits at `offset 0x34` (`[x29, #-0x44]`), while `w23` holds `w19 + 3`. `H2` checks `ldur w9, [x29, #-0x44]; cmp w9, w23` and branches (`b.ne #0x23744`) to the `-5` (`-EIO`) error return path, which properly executes `mutex_unlock(private_ts + 0x210)` (`0x2366C`) without leaking locks.

### 3. BUG-03 (`[P4 + P5]` — `himax_ts_work`)
- **Sites:** `.text + 0x0484C` (`mov w1, #1`) -> `H3` (`0x249F0`), `.text + 0x04AEC` (`blr x21`) -> `H4` (`0x24A00`)
- **Root Cause:** On SPI read-failure reset and exception recovery, `himax_report_all_leave_event()` (`0x054E8`) is skipped or runs only after reset finishes, stranding held touch slots inside Android `InputReader`.
- **Resolution:** Verified `x19` holds `private_ts` (`0x04158: mov x19, x0`) continuously across `0x04158..0x04C74`. Both hooks call `himax_report_all_leave_event(x19)` (`bl 0x054E8`, PAC/Shadow-Call-Stack safe) before running the displaced reset logic.

### 4. BUG-04 (`[P6]` — `himax_ts_work` `prevent_notch`)
- **Site:** `.text + 0x04BC0` (`00f10091 add x0, x8, #0x3c` -> `00310191 add x0, x8, #0x4c`)
- **Root Cause:** Cross-checking `himax_prevent_notch_store` (`0x0B960`) and `0x04CB8` confirmed `cmd_param_buf` starts at `private_ts + 0x4C`, whereas exception recovery at `0x04BC0` erroneously passed `private_ts + 0x3C`.

### 5. BUG-05 (`[P7]` — `himax_mcu_resend_cmd_func` `HSEN`)
- **Site:** `.text + 0x1A514` (`696242f9 ldr x9, [x19, #0x4c0]`) -> `H5` (`0x24A10`)
- **Root Cause:** Firmware high-sensitivity register `0x10007F14` remains `0x00000000` on stock S231018 and procfs `/proc/android_touch/HSEN` is disabled.
- **Resolution:** `H5` saves `x8` (`tp_usb_plug_status`) and `x30`, checks `x19 != 0` and `[x19, #1] == 0` (`ts->suspended` verified in `himax_chip_common_suspend`/`resume`), calls `himax_mcu_set_HSEN_enable(1)` (`0x14658`), restores `x8`/`x30`, and reloads `x9 = [x19, #0x4c0]`. Live inspection confirmed `0x10007F14 = 0x5A 0xA5 0x5A 0xA5` on boot and after suspend/resume.

### 6. BUG-09 / `[P8]` Intentionally Omitted on S231018 (`EDGE` vs `LEVEL` IRQ)
- `/proc/android_touch/debug` (`int`) and `himax_ts_register_interrupt` (`0x23C80..0x23CA0`) confirm S231018 firmware uses `IC Interrupt type is edge trigger` (`int_is_edge = 1`, `0x2002`). Forcing `0x2008` (`IRQF_TRIGGER_LOW`) creates a mismatch with IC edge pulsing and causes delayed touch releases. Native `0x2002` is preserved cleanly.

### 7. BUG-10 & BUG-19 (`[P9]` — Dual Finger Mask Release)
- **Site:** `.text + 0x037B8` (`cbz w8, #0x3960`) -> `H7` (`0x24A54`)
- **Resolution:** Instead of blindly NOPing the check, `H7` runs `ldrh w9, [x20, #0x90]` (`pre_finger_mask`), ORs it with `w8` (`p_point_num`), and only branches to `#0x3960` when both are `0`. Simultaneous rapid finger lifts reliably emit slot teardown and `BTN_TOUCH = 0`.

### 8. BUG-13 & BUG-20 (`[P10]` — Type-B Event Ordering & S231018 ELF Relocations)
- **Sites:** `.text + 0x03610` (`ldr x0, [x20, #0x170]`) -> `H6` (`0x24A34`), `.text + 0x036AC` (`b #0x3584` -> `b #0x3594`)
- **Root Cause:** Stock `himax_report_data` dispatched `ABS_MT_SLOT` -> `0x30 (TOUCH_MAJOR)` -> `0x32 (WIDTH_MAJOR)` -> `0x3a (PRESSURE)` -> `0x35 (X)` -> `0x36 (Y)` **before** `input_mt_report_slot_state(dev, MT_TOOL_FINGER, active)`. Android's `InputReader` discarded `0x35/0x36` arriving while slot tracking ID was `-1` (`W InputReader: Received unexpected event (0x35/0x36)`), dropping rapid keystrokes.
- **Resolution:** `H6` saves `x8` (`g_target_report_data`) and `x30`, invokes `input_mt_report_slot_state(dev, 0, w24)` immediately after `ABS_MT_SLOT` via an appended `R_AARCH64_CALL26` relocation (`sym 1496`) in `.rela.text.himax_report_data_init`, restores `x8`/`x30`, reloads `x0`, and returns to `0x03614` to emit all attributes and coordinates cleanly. Redirecting `0x036AC` to `0x03594` skips the duplicate late `slot_state` call without shifting existing relocations.

---

## Userspace, PowerHAL & Display Fixes (`v2.0-S231018` Module)

### BUG-21: Restored SurfaceFlinger `2000ms` Touch Timer (Without Locking 120Hz)
- **Cause:** Earlier module configurations overrode `ro.surface_flinger.set_touch_timer_ms` from stock `2000` ms down to `200` ms, causing display refresh pacing to collapse toward 60Hz between keystrokes during normal typing cadences (>200ms).
- **Fix:** `system.prop` restores `ro.surface_flinger.set_touch_timer_ms=2000` alongside `ro.surface_flinger.set_idle_timer_ms=1000`, `windowsmgr.max_events_per_sec=240`, and `debug.sf.disable_backpressure=1`. Android Settings refresh rate (`60Hz / Auto / 120Hz`) stays completely unlocked.

### BUG-22: MediaTek `mtkpower@1.0-service` Overwriting Sysfs Tuning
- **Cause:** S231018 MTK PowerHAL resets `gpu_bottom_freq` (`390000`), `gpu_cust_upbound_freq` (`1003000`), `fpsgo/fbt/thrm_enable` (`1`), `policy6/scaling_min_freq` (`725000`), `sugov_ext/down_rate_limit_us` (`10000`), and `top-app/cpu.uclamp.latency_sensitive` (`0`) shortly after touch/launch boosts finish.
- **Fix:** `service.sh` polls `/sys/class/leds/lcd-backlight/brightness` directly in shell every `2s` awake (`5s` asleep) without spawning subshells/dumpsys per cycle:
  - Uses `raise_if_lt` (`policy0 >= 1200000`, `policy6 >= 1400000`, `gpu_bottom_freq >= 648000`, `gpu_cust_boost_freq >= 948000`) so temporary higher PowerHAL bursts are never downgraded.
  - Enforces `sugov_ext/up_rate_limit_us=0`, `sugov_ext/down_rate_limit_us=30000` (anti-microstutter between typing taps), `fpsgo_enable=0`, `thrm_enable=0`, `boost_ta=1`, `top-app/cpu.uclamp.latency_sensitive=1`.
  - Automatically drops back to low-power standby (`500000`/`725000`/`390000`, `thrm_enable=1`, `latency_sensitive=0`) whenever the screen turns off.

### BUG-23: `/proc/game_mode` Periodic SPI Read Error
- **Cause:** Reading `/proc/game_mode` inside a loop triggers `himax_mcu_read_game_mode()`, hitting the touch SPI bus every 2 seconds and flooding `dmesg` with `[HXTP][ERROR] mode not match, pls check!`.
- **Fix:** Moved `echo 0 > /proc/game_mode` to one-shot boot/wake setup (`apply_awake_static`), producing zero periodic SPI traffic (`tmp_data[0]=90, mode=0, retry_cnt=0`).

### BUG-11, BUG-12, BUG-17, BUG-24: Clean IDC Overlays (Touchscreen & Precision Pen 2)
- Removed legacy duplicate `himax_tp.idc` and unused `/data/system/devices/idc/` copy assumptions.
- `himax-touchscreen.idc` disables broken pressure scaling (`touch.pressure.calibration = none`, `touch.size.calibration = diameter`, `touch.wake = 1`).
- `himax-stylus.idc` configures Precision Pen 2 as direct digitizer (`touch.deviceType = touchScreen`, `touch.gestureMode = spots`, 12-bit linear scale `0.000244140625`, `touch.filter.level = 2`).

### Intentionally Preserved Hardware Behavior (`BUG-14`, `BUG-18`)
- **Stock Haptics (`BUG-18` Removed):** Hardware vibration (`soc:regulator_vibrator`) induces zero touch errors on S231018 and is never disabled or muted.
- **Native Refresh Rate Settings (`BUG-14` Removed):** Refresh rate is never pinned to `120.0` Hz.
