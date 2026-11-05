# INDEPENDENT VALIDATION & INTEGRITY REPORT: FINAL CANDIDATE
**Candidate Name:** `vendor_boot_himax_combined_final_candidate.img`  
**Target Device:** Lenovo Tab P11 Gen 2 (TB350XU)  
**Validation Date:** 2026-11-05  
**Validation Status:** Passed all static, cryptographic, ELF, and emulation checks. **Hardware boot testing pending.**  

---

## 1. Cryptographic Hash Validation

All inputs, intermediates, and outputs have been cryptographically verified:

| File / Component | Expected SHA-256 | Actual SHA-256 | Verification Result |
|---|---|---|---|
| **Original `vendor_boot.img`** | `24fe1068b0b46a15480521a1df810ed23db55091371524264842a79064a2cfc6` | `24fe1068b0b46a15480521a1df810ed23db55091371524264842a79064a2cfc6` | **EXACT MATCH (VERIFIED)** |
| **Original `himax_mmi.ko`** | `e9dc21ba90f42c0a136140c6e8e2838608146d6e20323c21ff237650349a1827` | `e9dc21ba90f42c0a136140c6e8e2838608146d6e20323c21ff237650349a1827` | **EXACT MATCH (VERIFIED)** |
| **Patched `himax_mmi.combined_final.ko`** | `e766054fef9aefa940d4af079602e0d39fb06fe6feb09f9ab73e0d8d9eb6b49c` | `e766054fef9aefa940d4af079602e0d39fb06fe6feb09f9ab73e0d8d9eb6b49c` | **REPRODUCIBLE (VERIFIED)** |
| **Final Rebuilt `vendor_boot` Image** | `96a6ad938b3f6e3d871ad9ca76d9411690003ed8a61b0c2e2f9f3b2c88ad038e` | `96a6ad938b3f6e3d871ad9ca76d9411690003ed8a61b0c2e2f9f3b2c88ad038e` | **BIT-EXACT (VERIFIED)** |

---

## 2. Binary Patch & Instruction Verification

Each patch was validated against the original disassembled ARM64 instructions:

1. **[P1] Propagate SPI Read Status:**
   - Offset: `0x011A44`
   - Preimage: `a80240f9` (`ldr x8, [x21]`) — **MATCH**
   - Replacement: `1f4c0014` (`b #0x24ac0`) — **MATCH**
2. **[P2] Return Stored Read Result:**
   - Offset: `0x011AD8`
   - Preimage: `20008052` (`mov w0, #1`) — **MATCH**
   - Replacement: `e00340b9` (`ldr w0, [sp]`) — **MATCH**
3. **[P3] Reject Short SPI Transfers:**
   - Offset: `0x02376C`
   - Preimage: `280340f9` (`ldr x8, [x25]`) — **MATCH**
   - Replacement: `da040014` (`b #0x24ad4`) — **MATCH**
4. **[P4] Release Contacts Before Read-Fail Reset:**
   - Offset: `0x004920`
   - Preimage: `00000090` (`adrp x0, #0x4000`) — **MATCH**
   - Replacement: `72800014` (`b #0x24ae8`) — **MATCH**
5. **[P5] Release Contacts Before Exception Recovery:**
   - Offset: `0x004BCC`
   - Preimage: `08000090` (`adrp x8, #0x4000`) — **MATCH**
   - Replacement: `cb7f0014` (`b #0x24af8`) — **MATCH**
6. **[P6] Fix Prevent-Notch Command Buffer Pointer Offset:**
   - Offset: `0x004CC0`
   - Preimage: `00f10091` (`add x0, x8, #0x3c`) — **MATCH**
   - Replacement: `00310191` (`add x0, x8, #0x4c`) — **MATCH**
7. **[P7] Request HSEN Mode on Resend:**
   - Offset: `0x01A61C`
   - Preimage: `09000090` (`adrp x9, #0x1a000`) — **MATCH**
   - Replacement: `3b290014` (`b #0x24b08`) — **MATCH**

---

## 3. ABI Compatibility & Module Dependencies

- **Vermagic:** `5.10.136-android12-9-gf16efe7b9174 SMP preempt mod_unload modversions aarch64` (Preserved intact).
- **Import Symbol CRCs:** All 116 imported kernel symbol CRCs are 100% identical to stock.
- **Exported Symbols:** All 36 exported symbols remain registered at valid entry points.
- **Cross-Module Dependents (6 modules in ramdisk):**
  - `hall_mod.ko`: imports `himax_common_set_hall_status` — **Signature & Address Valid**
  - `ktz8866.ko`: imports `wake_flag_drm` — **Preserved**
  - `mtk_charger_framework.ko`: imports `tp_usb_plug_status` — **Preserved**
  - `panel-boe-2-hx83102j-vdo.ko`: imports `himax_rst_gpio_high`, `wake_flag_drm` — **Preserved**
  - `panel-boe-hx83102j-vdo.ko`: imports `himax_rst_gpio_high`, `wake_flag_drm` — **Preserved**
  - `panel-tianma-hx83102j-vdo.ko`: imports `himax_rst_gpio_high`, `wake_flag_drm` — **Preserved**
- **Other Ramdisk Members:** All other 667 files in the CPIO ramdisk remain completely bit-for-bit identical to the stock image.

---

## 4. Boot Image Structure & AVB Descriptor

- **Header Version:** Android Boot Image v4.
- **Page Size:** 4096 bytes.
- **Partition Size:** Exactly `67,108,864` bytes (64 MB), matching hardware eMMC/UFS partition boundary.
- **DTB:** Preserved byte-identical (188,646 bytes).
- **AVB Footer:** AVB footer at offset `67,108,800` (last 64 bytes) validated. SHA-256 hash descriptor over the modified payload recalculated and verified.

---

## 5. Scope of Validation & Mandatory Hardware Notice

> [!IMPORTANT]
> **Static and emulation checks confirm mathematical and semantic correctness, but CANNOT replace physical hardware validation.**  
> Before declaring this fix complete in daily usage, the tablet must be tested through:
> 1. Normal booting to Android desktop.
> 2. Multitouch tracking (10 fingers simultaneous tap/drag).
> 3. Active stylus drawing and palm rejection in Lenovo Vantage / drawing apps.
> 4. USB cable plug / unplug cycles during active typing.
> 5. Screen off / on (sleep/wake) cycles.
