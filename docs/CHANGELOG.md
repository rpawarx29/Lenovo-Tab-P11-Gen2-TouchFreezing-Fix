# Changelog — Lenovo Tab P11 Gen 2 (`S231018` Android 14)

- **Device:** Lenovo Tab P11 Gen 2 (`TB350XU` / `TB350FU`)
- **Stock ROM Baseline:** `TB350XU_USER_S231018_2601050930_MP_ROW` (`TB350XU_S231018_260105_ROW`)

---

## `v2.0-S231018` (2026-11-25) — Verified Complete Kernel + Userspace Suite
### Kernel (`vendor_boot` -> `lib/modules/himax_mmi.ko`)
- Replaced legacy patch scripts with unified reproducible builder [`tools/patch_vendor_boot.py`](../tools/patch_vendor_boot.py) backed by clean library [`tools/vendor_boot_image.py`](../tools/vendor_boot_image.py).
- Implemented S231018 hooks `H1..H7` (`[P1..P7, P9, P10]`) on stock `himax_mmi.ko` (`5.10.233-android12-9-g9568a331d924`, driver `2.1.0.2_Tulip_01`):
  - **Type-B ordering (`H6`):** Appends `R_AARCH64_CALL26` relocation for `input_mt_report_slot_state` (`sym 1496`) in `.rela.text.himax_report_data_init`, eliminating `InputReader` `0x35/0x36` typing drops while preserving PAC/SCS/CFI and keeping `WIDTH_MAJOR`/`PRESSURE`/`X/Y` intact.
  - **Dual finger mask (`H7`):** Checks both `p_point_num` and `pre_finger_mask` (`[x20, #0x90]`) on release (`0x037B8`).
  - **SPI reliability (`H1`, `H2`, `H3`, `H4`, `P6`):** Propagates read errors via unused `[sp+0]`, checks `spi_message.actual_length` (`-EIO` + mutex unlock), calls `himax_report_all_leave_event` prior to resets, and fixes `prevent_notch` struct offset `#0x3C -> #0x4C`.
  - **High-Sensitivity mode (`H5`):** Activates `HSEN` (`0x10007F14 = 0xA55AA55A`) whenever awake (`!ts->suspended`), verified live on boot & resume.
  - **Native `EDGE` IRQ preserved (`0x2002`):** Dropped the older Level-Low (`0x2008`) override that caused delayed key releases on S231018.

### APatch / Magisk / KernelSU Module (`magisk_module/` -> `releases/tb350xu-s231018-touch-fix.zip`)
- Restored `ro.surface_flinger.set_touch_timer_ms=2000` in `system.prop` (fixes mid-typing 200ms refresh drops while keeping native Settings `60Hz / Auto / 120Hz` unlocked).
- Rewrote `service.sh` with a zero-fork `/sys/class/leds/lcd-backlight/brightness` loop (`2s` awake / `5s` asleep) using `raise_if_lt` to prevent `mtkpower@1.0-service` PowerHAL resets of GPU/CPU/`thrm_enable`/`sugov_ext`/`uclamp.latency_sensitive` without fighting active launch bursts.
- Moved `echo 0 > /proc/game_mode` to one-shot boot/wake initialization, removing periodic SPI reads and `[HXTP][ERROR]` kernel log spam.
- Removed unused `himax_tp.idc`, removed vibrator unbinding (stock haptics intact), and added deterministic packager [`tools/pack_module.py`](../tools/pack_module.py) + safe A/B flasher [`tools/flash_vendor_boot.cmd`](../tools/flash_vendor_boot.cmd).
- Added `.gitattributes` (LF enforcement on shell/prop/idc/py/md) and pruned legacy & experimental docs/scripts.

---

## Earlier S231018 Milestones
- Initial S231018 `vendor_boot` Type-B reordering prototype, `himax-stylus.idc` (`Precision Pen 2`), and early `.idc` calibration research.
