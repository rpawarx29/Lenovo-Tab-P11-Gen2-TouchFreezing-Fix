# CHANGELOG: LENOVO TAB P11 GEN 2 TOUCHSCREEN & PERFORMANCE SUITE

- **Target Devices:** Lenovo Tab P11 Gen 2 (`TB350XU` / `TB350FU`)
- **Chipset:** MediaTek Helio G99 (`MT6789`)
- **Partitions / Layers:** `vendor_boot` (`lib/modules/himax_mmi.ko`) + APatch/Magisk/KSU (`tb350xu_master_touch_fix`)

---

## [v6.1.0-Ultimate] - 2026-11-25 (Verified Live on S231018 `TB350XU_S231018_260105_ROW`)
### Added & Fixed (Kernel `himax_mmi.ko`, Linux `5.10.233-android12-9-g9568a331d924`, Driver `2.1.0.2_Tulip_01`)
- **Complete S231018 Binary Patch Builder (`tools/build_s231018_ultimate_touch.py`):** Rebuilds stock S231018 `vendor_boot.img` cleanly with zero corrupted relocations, full PAC/Shadow-Call-Stack (`x18`)/CFI preservation, and recomputed AVB `HashDescriptor` + footer.
- **[P10 / H6] True S231018 Linux Type-B Event Ordering Fix (`0x03610` + `0x036AC` -> `0x03594`):** Eliminates `W InputReader: Received unexpected event (0x35/0x36)` typing drops by saving `x8`/`x30`, emitting `input_mt_report_slot_state(dev, MT_TOOL_FINGER, active)` via an appended `R_AARCH64_CALL26` relocation in `.rela.text.himax_report_data_init` immediately after `ABS_MT_SLOT`, and keeping `WIDTH_MAJOR`/`PRESSURE`/`POSITION_X/Y` intact.
- **[P9 / H7] Dual Finger-Mask Lift Check (`0x037B8` -> `0x24A54`):** Tests `p_point_num | pre_finger_mask` (`[x20, #0x90]`) so simultaneous multi-finger lifts never leave stuck contacts.
- **[P1+P2 / H1], [P3 / H2], [P4+P5 / H3+H4], [P6], [P7 / H5] Ported & Verified on S231018:** SPI error propagation via `[sp+0]`, `spi_message.actual_length` bounds check (`-EIO` + mutex unlock), early `himax_report_all_leave_event` on resets, `prevent_notch` struct offset `#0x3C -> #0x4C`, and wake/resume `HSEN` activation (`0x10007F14 = 0xA55AA55A`).
- **Hardware-Matched Edge IRQ Preserved (`P8` Intentionally Omitted):** Verified via `/proc/android_touch/debug` (`int`) that S231018 uses native Edge triggering (`0x2002`, `int_is_edge=1`); removing the legacy `0x2008` override eliminates sticky key-release lag.

### Added & Fixed (APatch / Magisk / KSU Module `v6.1-Ultimate`)
- **Restored SurfaceFlinger Touch Timer (`200ms` -> `2000ms`):** Reverted the regression in `system.prop` (`ro.surface_flinger.set_touch_timer_ms=2000`) so rapid typing never drops display refresh between keystrokes while keeping Settings `60Hz / Auto / 120Hz` unlocked.
- **PowerHAL-Resilient `service.sh` Daemon (`BUG-22`):** Uses zero-fork backlight monitoring (`/sys/class/leds/lcd-backlight/brightness`) every `2s` awake / `5s` asleep to keep `policy0 >= 1200000`, `policy6 >= 1400000`, `sugov_ext/down_rate_limit_us=30000`, `gpu_bottom_freq >= 648000`, `fpsgo_enable=0`, `thrm_enable=0`, and `top-app/cpu.uclamp.latency_sensitive=1` after `mtkpower@1.0-service` hints expire—without downgrading active launch bursts and cleanly sleeping at `500/725/390 MHz` when screen is off.
- **Eliminated `/proc/game_mode` SPI Polling Error (`BUG-23`):** Moved `echo 0 > /proc/game_mode` to one-shot boot/wake initialization, removing periodic SPI reads and `[HXTP][ERROR] mode not match, pls check!` `dmesg` spam.
- **Removed Dead `himax_tp.idc` & Legacy Vibrator Unbinding (`BUG-18`, `BUG-24`):** Keeps `/system/usr/idc/himax-touchscreen.idc` and `himax-stylus.idc` cleanly mounted; preserves stock `soc:regulator_vibrator` hardware haptics intact.
- **Added Deterministic Packager & Safe Flasher:** Added `tools/build_module_zip.py`, `releases/TB350XU_Master_Touch_and_Performance_Fix.zip`, `tools/FLASH_S231018_ULTIMATE_TOUCH.cmd`, `.gitattributes` (LF enforcement), and `docs/S231018_ULTIMATE_VERIFICATION_REPORT.md`.

---

## [v6.0.0-Pristine] - 2026-11-06 to 2026-11-24
- Initial Android 14 (`S231018`) Type-B reordering prototype, `himax-stylus.idc` (`Precision Pen 2`), `ALL_VERIFIED_BUGS.md` (16/18 bugs), `build_v6_s231018.py`, `build_pristine_lenovo_pro_touch.py`, and executive Lenovo escalation report.
- Superseded by **v6.1.0-Ultimate** due to `ro.surface_flinger.set_touch_timer_ms=200` typing drops, `mtkpower` resetting sysfs floors, `0x0360c` relocation/offset edge cases, forced 120Hz lock, and unnecessary vibrator unbinding on S231018.

---

## [v4.0] - 2026-11-05 (Android 12 `S020008` / Kernel `5.10.136`)
- Full binary audit of `5.10.136` `himax_mmi.ko` (`e9dc21ba...`): `[P1..P9]` including `[P8a-e]` level-triggered experiment (`0x2008`) on Android 12 firmware (`vendor_boot.img` `24fe1068...`).

## [v1.0 - v3.0] - 2026-11-05
- Initial SPI read status propagation (`[P1]`, `[P2]`), `actual_length` transfer check (`[P3]`), pre-reset leave events (`[P4]`, `[P5]`), `prevent_notch` pointer fix (`[P6]`), `HSEN` wake activation (`[P7]`), `BUILD_FINAL.py`, and `monitor_touch.py`.
