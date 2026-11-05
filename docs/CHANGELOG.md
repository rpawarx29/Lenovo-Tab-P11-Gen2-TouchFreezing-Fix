# CHANGELOG: LENOVO TAB P11 GEN 2 TOUCHSCREEN SUBSYSTEM
**Target Device:** Lenovo Tab P11 Gen 2 (TB350XU)  
**Component:** `vendor_boot.img` / `himax_mmi.ko`  

---

## [v3.0 Final Unified Candidate] - 2026-11-05
### Added
- **Single Integrated Candidate:** Built `vendor_boot_himax_combined_final_candidate.img` containing the full verified union of all valid patches.
- **Independent Full Binary Audit:** Disassembled all 37,552 instructions of `.text`; mapped 428 functions, CFI jump tables, and 12,332 relocations.
- **Real-Time Touch Subsystem Monitor:** Added `MONITOR_TOUCH_RECOVERY.cmd` and `monitor_touch.py` to stream, categorize, and diagnose touch events, communication errors, and recovery states without root or rebooting.
- **Reproducible Windows Builder:** Added `BUILD_FINAL.cmd` and `BUILD_FINAL.py` with standalone Python/LZ4 support.
- **Exhaustive 35-Point Freezing Analysis:** Documented in `TOUCH_FREEZE_ROOT_CAUSE_ANALYSIS.md`, detailing the stylus-priority / palm-rejection suppression mechanics.
- **Bootloader & AVB Feasibility Report:** Thoroughly documented AVB chain and verified that bootloader relocking with modified images is unsafe and causes hard-bricks.

### Verified & Consolidated
- **[P1] SPI Read Status Propagation:** Intercepts `hx83102j_read_event_stack` bus read result, sets boolean success flag on stack.
- **[P2] Real Status Return:** Replaced hardcoded `mov w0, #1` with `ldr w0, [sp]` at function return.
- **[P3] Short Transfer Rejection:** Added `actual_length` comparison against expected length in `himax_bus_read()`, returning `-EIO` on truncated transfers.
- **[P4] Contact Release Before Read-Fail Reset:** Dispatches `himax_report_all_leave_event()` before read-failure hardware reset.
- **[P5] Contact Release Before Exception Recovery:** Dispatches `himax_report_all_leave_event()` before firmware exception reinitialization.
- **[P6] Prevent-Notch Buffer Offset Correction:** Fixed pointer from `ts + 0x3C` to packed 4-byte buffer `ts + 0x4C` at `.text + 0x04CC0`.
- **[P7] High-Sensitivity Mode on Resend:** Calls `himax_mcu_set_HSEN_enable(1)` dynamically during active settings resend following wake or recovery.

---

## [v2.0 Experimental Recovery & High-Sensitivity] - 2026-11-05
### Added
- Separate `vendor_boot_himax_recovery_v2.img` and `vendor_boot_himax_highsense_v2.img`.
- Introduced patch [P6] for `fp_set_prevent_notch` buffer pointer correction.
- Introduced patch [P7] for dormant HSEN register activation.
- Created preliminary analysis scripts.

---

## [v1.0 Experimental SPI Recovery] - 2026-11-05
### Added
- Initial experimental image `vendor_boot_himax_spi_recovery_experimental_v1.img`.
- Implemented core SPI error propagation (`[P1]`, `[P2]`).
- Implemented short SPI length check (`[P3]`).
- Implemented finger contact release before reset (`[P4]`, `[P5]`).

---

## [Factory Stock Baseline]
- Firmware Build: TB350XU / Android 12 / Kernel 5.10.136.
- Original driver `himax_mmi.ko` SHA-256: `e9dc21ba90f42c0a136140c6e8e2838608146d6e20323c21ff237650349a1827`.
- Original `vendor_boot.img` SHA-256: `24fe1068b0b46a15480521a1df810ed23db55091371524264842a79064a2cfc6`.
- Sufferer of intermittent finger-only freezes while stylus continues working.
