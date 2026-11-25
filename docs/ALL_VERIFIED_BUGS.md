# ALL VERIFIED BUGS & DEFECTS: LENOVO TAB P11 GEN 2 TOUCH & PERFORMANCE SUBSYSTEM

- **Supported Models:** Lenovo Tab P11 Gen 2 — `TB350XU` (LTE) / `TB350FU` (Wi-Fi)
- **SoC:** MediaTek Helio G99 (`MT6789`) — 6x Cortex-A55 (`policy0`, 500–2000 MHz) + 2x Cortex-A76 (`policy6`, 725–2200 MHz), Mali-G57 MC2 (`13000000.mali`, 390–1100 MHz)
- **Touch Controller:** Himax `HX83102J` (`Huaqin_BOE`, `Tulip_AX6298`, `FW_VER = 0xC402`, Driver `2.1.0.2_Tulip_01`, SPI `1100a000.spi0`, IRQ `mtk-eint 54 Edge`)
**Analyzed Firmware Builds:**
- **Primary Verified Production Baseline (Android 14):** `TB350XU_USER_S231018_2601050930_MP_ROW` (`TB350XU_S231018_260105_ROW`), Kernel `5.10.233-android12-9-g9568a331d924`
- **Historical Archive Baseline (Android 12):** `TB350XU_USER_S020008_221025`, Kernel `5.10.136-android12-9-gf16efe7b9174`

---

## Executive Summary Matrix (BUG-01 through BUG-24)

| ID | Layer | Defect Summary | Android 12 (`5.10.136`) | Android 14 `S231018` (`5.10.233`) | Resolution (`v6.1-Ultimate`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BUG-01** | `himax_mmi.ko` | `hx83102j_read_event_stack` ignores `himax_bus_read` result and hardcodes `mov w0, #1` | `0x11A44`, `0x11AD8` | `0x11938`, `0x119C8` | **Fixed `[P1+P2]` (`H1`)**: Propagate real SPI status via unused `[sp]` |
| **BUG-02** | `himax_mmi.ko` | `himax_bus_read` never validates `spi_message.actual_length` against requested length | `0x2376C` | `0x23650` | **Fixed `[P3]` (`H2`)**: Compare `[x29, #-0x44] == w23`, branch `-EIO` + mutex unlock |
| **BUG-03** | `himax_mmi.ko` | Missing `himax_report_all_leave_event` before SPI fail / exception resets | `0x04920`, `0x04BCC` | `0x0484C`, `0x04AEC` | **Fixed `[P4+P5]` (`H3+H4`)**: Emit `0x054E8` leave reset before recovery resets |
| **BUG-04** | `himax_mmi.ko` | `prevent_notch` recovery uses wrong struct offset `ts + 0x3C` instead of `ts + 0x4C` | `0x04CC0` | `0x04BC0` | **Fixed `[P6]`**: `add x0, x8, #0x3c` -> `add x0, x8, #0x4c` |
| **BUG-05** | `himax_mmi.ko` | Dormant High-Sensitivity Mode (`HSEN`, `0x10007F14`) never activated on wake/boot | `0x1A61C` | `0x1A514` | **Fixed `[P7]` (`H5`)**: Calls `himax_mcu_set_HSEN_enable(1)` when `!ts->suspended` |
| **BUG-06** | FW / Workqueue | Stylus-priority / palm-rejection suppression if stylus-leave packet is lost | Protocol logic | Protocol logic | **Mitigated**: Guaranteed slot release via `[P4]/[P5]/[P9]` + clean `/proc/game_mode=0` |
| **BUG-07** | Symbol Layout | `mtk_charger_framework.ko` writes 32-bit int to 1-byte `tp_usb_plug_status` | `.bss + 0x04` | Verified 64-bit aligned | **Benign**: Natural alignment padding separates symbol from `private_ts` |
| **BUG-08** | Driver Mutex | Multi-packet SPI mutex granularity gap across `himax_bus_read` / `himax_ts_work` | Architecture | Architecture | **Documented**: Preserved lock hierarchy to avoid deadlocks with SPI/panel drivers |
| **BUG-09** | `himax_mmi.ko` | Forced Level-Low (`0x2008`) vs native Edge (`0x2002`) IRQ handling | Fixed `[P8a-e]` | `0x23C80..0x23CA0` | **Intentionally Omitted on S231018**: Live HW uses Edge IRQ; `0x2008` caused sticky releases |
| **BUG-10** | `himax_mmi.ko` | Finger release loop skips clearing when `p_point_num == 0` while fingers remain masked | `0x038B8` (`nop`) | `0x037B8` -> **`BUG-19` (`H7`)** | **Upgraded `[P9]` (`H7`)**: Checks `p_point_num \| pre_finger_mask` (`[x20, #0x90]`) |
| **BUG-11** | IDC Profile | Artificial pressure calibration causing 1-second tap delay / missed light taps | `/vendor/usr/idc/` | `/system/usr/idc/` | **Fixed**: `touch.pressure.calibration = none`, `touch.size.calibration = diameter` |
| **BUG-12** | IDC Profile | Framework motion smoothing filter swallows subtle rapid taps/slides | `filter.level = 1` | Raw touchscreen IDC | **Fixed**: Filtering disabled on `himax-touchscreen.idc`; `filter.level = 2` reserved for Pen 2 |
| **BUG-13** | `himax_mmi.ko` | Linux Type-B coordinate events (`0x35/0x36`) sent before `ABS_MT_TRACKING_ID` | Replaced in `v6.0` | `0x03610` -> **`BUG-20` (`H6`)** | **Fixed `[P10]` (`H6`)**: Calls `input_mt_report_slot_state` immediately after `ABS_MT_SLOT` |
| **BUG-14** | Display Policy | Strict 120Hz display lock vs dynamic refresh collapse | Locked `120.0` Hz | **Policy Changed (`BUG-21`)** | **Superseded**: Strict 120Hz lock removed; Settings 60/Auto/120Hz preserved |
| **BUG-15** | DVFS / Thermal | MTK `fpsgo` & thermal throttling starving LITTLE cluster SPI IRQ handling | `service.sh` | `service.sh` + **`BUG-22`** | **Upgraded**: `fpsgo_enable=0`, `thrm_enable=0`, `boost_ta=1` + awake enforcement daemon |
| **BUG-16** | SystemUI | Broken notification blur scrim stalling GPU compositor | `disable_window_blurs=1` | `disable_window_blurs=1` | **Fixed**: Global `disable_window_blurs = 1` + background Lenovo OTA disabled |
| **BUG-17** | IDC Profile | Precision Pen 2 classified as `pointer`, triggering mouse acceleration jitter | `himax-stylus.idc` | `himax-stylus.idc` | **Fixed**: `touch.deviceType = touchScreen`, `gestureMode = spots`, 4096-level pressure |
| **BUG-18** | Platform Driver | Hardware vibrator (`soc:regulator_vibrator`) unbinding / haptics mute | Unbound in A12 | **Absent on S231018** | **Intentionally Removed**: S231018 has no vibration issue; stock haptics 100% preserved |
| **BUG-19** | `himax_mmi.ko` | **New S231018:** `himax_report_data` exit check ignores `pre_finger_mask` (`[x20, #0x90]`) | — | `0x037B8` | **Fixed `[P9]` (`H7`)**: Loads halfword mask, ORs with `w8`, then `cbz` |
| **BUG-20** | `himax_mmi.ko` | **New S231018:** `.rela.text.himax_report_data_init` + PAC/SCS break naive Type-B patches; stock drops `0x35/0x36` | — | `0x03610`, `0x036AC` | **Fixed `[P10]` (`H6`)**: Appends reloc `sym 1496`, preserves `x8`/`x30`, fixes tail branch `#0x3594` |
| **BUG-21** | SurfaceFlinger | **New S231018:** Legacy `set_touch_timer_ms=200` drops refresh rate mid-typing (`stock=2000`) | — | `magisk_module/system.prop` | **Fixed**: Restored `ro.surface_flinger.set_touch_timer_ms=2000` (typing stays smooth!) |
| **BUG-22** | MTK PowerHAL | **New S231018:** `mtkpower@1.0-service` resets GPU/CPU/FPSGO/`sugov_ext` on hint expiry | — | Live sysfs drift | **Fixed**: 2s awake guard (`raise_if_lt`/`write_if_ne`), `sugov_ext down=30000`, `uclamp.latency_sensitive=1` |
| **BUG-23** | `procfs` / SPI | **New S231018:** Polling `/proc/game_mode` runs SPI reads & floods `dmesg` `[HXTP][ERROR]` | — | `/proc/game_mode` | **Fixed**: Removed read polling from loop; one-shot `echo 0 > /proc/game_mode` on boot/wake |
| **BUG-24** | Overlay / IDC | **New S231018:** Dead `himax_tp.idc` duplicate & non-existent `/data/system/devices/idc/` path | — | `magisk_module/` | **Fixed**: Removed `himax_tp.idc`; clean `/system/usr/idc/himax-{touchscreen,stylus}.idc` mount |

---

## Detailed Root Causes & Instruction-Level Verification (Android 14 S231018)

### 1. Kernel Driver Fixes (`lib/modules/himax_mmi.ko`, `.text = 0x249C8` -> `0x24A64`)

#### BUG-01 (`[P1 + P2]` — `hx83102j_read_event_stack`)
- **Stock S231018 Locations:** `.text + 0x11938` (`08714239 ldrb w8, [x8, #0x9c]`) and `.text + 0x119C8` (`20008052 mov w0, #1`)
- *(Android 12 S020008 baseline locations: `0x11A44` and `0x11AD8`)*
- **Root Cause:** After `bl himax_bus_read` (`0x11930`), the return value in `w0` is ignored and the epilogue unconditionally executes `mov w0, #1`. Read errors never propagate up to trigger recovery.
- **S231018 Fix (`H1` @ `0x249C8`):** Stack slot `[sp+0x00 .. sp+0x08)` was verified completely unused inside the `0x60`-byte frame (`sp+0x08..0x60` hold timestamps, stack canary, and saved registers). `H1` computes `(w0 == 0) ? 1 : 0`, stores it to `[sp]`, restores the displaced `ldrb w8, [x8, #0x9c]`, returns to `0x1193C`, and `0x119C8` executes `ldr w0, [sp]` before `add sp, sp, #0x60; autiasp; ret`.

#### BUG-02 (`[P3]` — `himax_bus_read`)
- **Stock S231018 Location:** `.text + 0x23650` (`e203132a mov w2, w19`)
- *(Android 12 S020008 location: `0x2376C`)*
- **Root Cause:** `spi_sync()` returns `0` whenever controller submission succeeds, even if `spi_message.actual_length` is shorter than `length + 3` (`w23 = w19 + 3`).
- **S231018 Fix (`H2` @ `0x249DC`):** `struct spi_message msg` is located at `x29 - 0x78`; `actual_length` (`offsetof = 0x34` on ARM64 Linux 5.10 LP64) sits at `[x29, #-0x44]`. `H2` compares `ldur w9, [x29, #-0x44]` with `w23`: on mismatch, it branches directly (`b.ne #0x23744`) to the existing `-EIO` (`mov w19, #-5`) exit path, which properly executes `mutex_unlock(private_ts + 0x210)` (`0x2366C`) before returning.

#### BUG-03 (`[P4 + P5]` — `himax_ts_work`)
- **Stock S231018 Locations:** `.text + 0x0484C` (`21008052 mov w1, #1`) and `.text + 0x04AEC` (`a0023fd6 blr x21`)
- *(Android 12 S020008 locations: `0x04920` and `0x04BCC`)*
- **Root Cause:** On read-failure reset and exception recovery paths inside `himax_ts_work`, `himax_report_all_leave_event()` (`0x054E8`) is either absent (`0x0484C`) or called too late (`0x04AEC`). Active finger slots remain stuck down in `InputReader`.
- **S231018 Fix (`H3` @ `0x249F0`, `H4` @ `0x24A00`):** Verified `x19` holds `private_ts` (`0x04158: mov x19, x0`) throughout `himax_ts_work` cleanly. Both hooks call `bl 0x054E8` (`himax_report_all_leave_event(x19)` — PAC/Shadow-Call-Stack safe) prior to executing the displaced instructions (`mov w1, #1` / `blr x21`).

#### BUG-04 (`[P6]` — `himax_ts_work` `prevent_notch` pointer)
- **Stock S231018 Location:** `.text + 0x04BC0` (`00f10091 add x0, x8, #0x3c`)
- *(Android 12 S020008 location: `0x04CC0`)*
- **Root Cause:** `himax_prevent_notch_store` (`0x0B960`) and late `himax_ts_work` (`0x04CB8`) both pass `private_ts + 0x4C`. Recovery site `0x04BC0` erroneously passed `private_ts + 0x3C`.
- **S231018 Fix:** Direct 4-byte instruction patch `add x0, x8, #0x3c` -> `add x0, x8, #0x4c` (`00310191`).

#### BUG-05 (`[P7]` — `himax_mcu_resend_cmd_func` / `HSEN`)
- **Stock S231018 Location:** `.text + 0x1A514` (`696242f9 ldr x9, [x19, #0x4c0]`)
- *(Android 12 S020008 location: `0x1A61C`)*
- **Root Cause:** Firmware register `0x10007F14` (`HSEN`, enabled value `0xA55AA55A`) defaults to `0x00000000` on stock S231018 and `HSEN` procfs control is disabled.
- **S231018 Fix (`H5` @ `0x24A10`):** Preserves `x8` (`tp_usb_plug_status`) and `x30` on stack, verifies `x19` (`private_ts`) is non-null and `[x19, #1] == 0` (`ts->suspended == 0`, verified in `himax_chip_common_suspend`/`resume`), calls `himax_mcu_set_HSEN_enable(1)` (`0x14658`), restores `x8`/`x30`, and reloads `ldr x9, [x19, #0x4c0]`. Executed automatically on wake/resume (`0x06B14`) and reset recovery.

#### BUG-09 / `[P8]` Status on S231018 (Edge vs Level Triggered Interrupts)
- **Live S231018 Hardware Finding:** `/proc/android_touch/debug` (`int`) reports `IC Interrupt type is edge trigger.` and `Driver register Interrupt : EDGE TIRGGER`. At `0x23C80..0x23CA0` inside `himax_ts_register_interrupt`, `ic_data->int_is_edge` (`[x8, #0x58]`) selects `0x2002` (`IRQF_TRIGGER_FALLING | IRQF_ONESHOT`) cleanly.
- **Why Omitted on S231018:** Unlike earlier Android 12 experiments (`v4.0`), forcing `0x2008` (`IRQF_TRIGGER_LOW`) on S231018 firmware creates an edge/level protocol mismatch that causes delayed releases and sticky keys. Keeping native `0x2002` eliminates release latency while `[P1..P5, P9, P10]` eliminate freezes and missed taps.

#### BUG-10 / BUG-19 (`[P9]` — Simultaneous Lift & Finger Mask Desync)
- **Stock S231018 Location:** `.text + 0x037B8` (`480d0034 cbz w8, #0x3960`)
- **Root Cause:** Stock checks only `p_point_num` (`w8`) before deciding whether to clear active slots. If `p_point_num == 0` while `pre_finger_mask` (`[x20, #0x90]`) still holds active bits, slot release is bypassed.
- **S231018 Fix (`H7` @ `0x24A54`):** Executes `ldrh w9, [x20, #0x90]; orr w8, w8, w9; cbz w8, #0x3960`, ensuring slot cleanup and `BTN_TOUCH = 0` always fire whenever either `p_point_num` or `pre_finger_mask` is non-zero.

#### BUG-13 / BUG-20 (`[P10]` — Linux Type-B `ABS_MT_TRACKING_ID` Ordering + S231018 Relocation Safety)
- **Stock S231018 Locations:** `.text + 0x03610` (`ldr x0, [x20, #0x170]`) and `.text + 0x036AC` (`b #0x3584`)
- **Root Cause:** `himax_report_data` emitted:
  `ABS_MT_SLOT` -> `ABS_MT_TOUCH_MAJOR (0x30)` -> `ABS_MT_WIDTH_MAJOR (0x32)` -> `ABS_MT_PRESSURE (0x3a)` -> **`ABS_MT_POSITION_X (0x35)`** -> **`ABS_MT_POSITION_Y (0x36)`** -> `input_mt_report_slot_state(..., true)` (`ABS_MT_TRACKING_ID`).
  Android's `InputReader` discarded `0x35/0x36` arriving before a valid `TRACKING_ID`, logging `W InputReader: Received unexpected event (0x35/0x36)` and dropping rapid keystrokes. Furthermore, on S231018, `.rela.text` is named `.rela.text.himax_report_data_init` (section index 24), and overwriting relocation-bearing sites breaks kernel module loading (`CFI` / `PAC` / `GOT`).
- **S231018 Fix (`H6` @ `0x24A34` + `0x036AC -> 0x03594`):**
  1. Intercepts zero-relocation instruction `0x03610` (immediately after `ABS_MT_SLOT` `0x2f` and `ldr x8, [x27]` `g_target_report_data`).
  2. Saves `x8` and `x30` on stack, loads `x0 = input_dev`, `w1 = 0 (MT_TOOL_FINGER)`, `w2 = w24 (active)`, calls `input_mt_report_slot_state` via an appended `R_AARCH64_CALL26` entry (`sym 1496`) in `.rela.text.himax_report_data_init`.
  3. Restores `x8`, `x30`, reloads `x0 = input_dev`, returns to `0x03614` to emit `0x30`, `0x32 (WIDTH_MAJOR)`, `0x3a`, `0x35`, `0x36` cleanly under the now-valid `TRACKING_ID`.
  4. Redirects loop tail `0x036AC` from `b #0x3584` to `b #0x3594`, skipping the redundant late `input_mt_report_slot_state`.

---

### 2. Userspace, PowerHAL, SurfaceFlinger & Input Subsystem Fixes (`v6.1-Ultimate`)

#### BUG-21: SurfaceFlinger 200ms Touch Timer Regression (Fixed without Locking 120Hz)
- **Root Cause:** Earlier module versions set `ro.surface_flinger.set_touch_timer_ms=200`, overriding S231018's native `2000` ms timer. Any pause longer than 200ms between keypresses dropped SurfaceFlinger from 120Hz toward 60Hz.
- **Fix:** `system.prop` sets `ro.surface_flinger.set_touch_timer_ms=2000`, `ro.surface_flinger.set_idle_timer_ms=1000`, `windowsmgr.max_events_per_sec=240`, `debug.sf.disable_backpressure=1` — keeping Settings `60Hz / Auto / 120Hz` completely intact.

#### BUG-22: MTK PowerHAL (`mtkpower@1.0-service`) Overwriting Awake Clocks & `fpsgo`
- **Root Cause:** On S231018, one-shot boot/wake scripts are overwritten seconds later when MTK PowerHAL finishes an `APP_TOUCH` or `ACT_SWITCH` hint (resetting `gpu_bottom_freq` -> `390000`, `fpsgo/fbt/thrm_enable` -> `1`, `policy6/scaling_min_freq` -> `725000`, `sugov_ext/down_rate_limit_us` -> `10000`, `top-app/cpu.uclamp.latency_sensitive` -> `0`).
- **Fix:** `service.sh` polls `/sys/class/leds/lcd-backlight/brightness` directly in shell (`0` extra subprocesses per poll) every `2s` awake / `5s` asleep:
  - Uses `raise_if_lt` (`policy0 >= 1200000`, `policy6 >= 1400000`, `gpu_bottom_freq >= 648000`, `gpu_cust_boost_freq >= 948000`) so temporary higher PowerHAL app-launch bursts are never downgraded.
  - Enforces `sugov_ext/up_rate_limit_us = 0`, `sugov_ext/down_rate_limit_us = 30000` (eliminating frequency collapse between consecutive typing taps), `fpsgo_enable = 0`, `thrm_enable = 0`, `boost_ta = 1`, `top-app/cpu.uclamp.latency_sensitive = 1`.
  - Automatically drops back to deep sleep (`500000` / `725000` / `390000` / `thrm_enable = 1` / `latency_sensitive = 0`) when the display turns off.

#### BUG-23: `/proc/game_mode` Periodic SPI Read Error
- **Root Cause:** Reading `/proc/game_mode` triggers `himax_mcu_read_game_mode()`, issuing SPI bus reads and logging `[HXTP] himax_mcu_read_game_mode , now palm mode 0.` + `[HXTP][ERROR] mode not match, pls check!` on every poll.
- **Fix:** Removed `/proc/game_mode` reading from the periodic loop; executes one-shot `echo 0 > /proc/game_mode` only at boot/wake (`tmp_data[0]=90, mode=0, retry_cnt=0`, zero SPI bus contention while typing).

#### BUG-24: Duplicate `himax_tp.idc` & Obsolete `/data/system/devices/idc/`
- **Root Cause:** Legacy module releases carried an unused `himax_tp.idc` alongside `himax-touchscreen.idc` / `himax-stylus.idc` and copied files to `/data/system/devices/idc/` (unused on Android 14).
- **Fix:** Deleted `himax_tp.idc`; clean `himax-touchscreen.idc` and `himax-stylus.idc` mount directly into `/system/usr/idc/` (`dumpsys input` verified).

#### Excluded Legacy Mitigations on S231018 (`BUG-14`, `BUG-18`)
- **Stock Hardware Vibration (`BUG-18` Removed):** S231018 exhibits zero vibrator-induced SPI noise. `/sys/class/leds/vibrator` (`soc:regulator_vibrator`) and native haptics are completely untouched.
- **Native Refresh Rate Toggle (`BUG-14` Removed):** `settings put system min_refresh_rate` / `peak_refresh_rate` are never locked, letting the user freely toggle `60Hz / Auto / 120Hz` in Android Settings.
