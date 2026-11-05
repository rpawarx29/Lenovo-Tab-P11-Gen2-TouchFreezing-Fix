# BOOTLOADER RELOCK & ANDROID VERIFIED BOOT (AVB) FEASIBILITY REPORT
**Target Device:** Lenovo Tab P11 Gen 2 (TB350XU)  
**Platform:** MediaTek MT6789 (Helio G99)  
**Partition Modified:** `vendor_boot` (`vendor_boot.img`)  
**Critical Safety Notice:** Mandatory reading prior to any flashing operation  

---

## 1. Executive Determination

> [!CAUTION]
> **RELOCKING THE BOOTLOADER WITH THIS MODIFIED VENDOR_BOOT IMAGE IS NOT SUPPORTED AND WILL HARD-BRICK THE TABLET.**  
> Under no circumstances should `fastboot flashing lock` or `fastboot oem lock` be executed while running this modified image.

---

## 2. Root-Free Runtime Independence

### 2.1 Can the Touchscreen Fix Work Without Root?
**YES.**
The touchscreen driver `himax_mmi.ko` is packaged inside the first-stage ramdisk of `vendor_boot.img` at `lib/modules/himax_mmi.ko`.
- During boot, the Linux kernel module loader automatically insmods all modules listed in `modules.load` directly from the ramdisk.
- The driver runs in kernel space before Android userspace (`init`, Zygisk, Magisk, or KernelSU) ever launches.
- **Therefore, the touchscreen fix does NOT require KernelSU, Magisk, ZygiskNext, or root privileges to function.** Once flashed to the `vendor_boot` partition on an unlocked device, root can be completely removed if desired.

---

## 3. The Android Verified Boot (AVB) Chain of Trust

### 3.1 MediaTek MT6789 AVB Architecture
The Lenovo Tab P11 Gen 2 uses AVB 2.0 with a multi-partition chained verification hierarchy:

```
[Hardware Root of Trust: SoC eFuses]
   │  - Lenovo OEM Public Key Hash burned into MediaTek SoC silicon
   ▼
[Little Kernel (LK) Bootloader]
   │  - Verifies signature of vbmeta using OEM Public Key
   ▼
[vbmeta Partition]
   ├── Contains Hash Descriptor for vbmeta_system
   └── Contains Hash Descriptor for vbmeta_vendor
         │
         ▼
     [vbmeta_vendor Partition]
         ├── Chained Hash for /vendor
         ├── Chained Hash for /vendor_boot
         └── Chained Hash for /dtbo
```

### 3.2 What Happens Inside `vendor_boot.img`?
Our build tool recalculates the internal SHA-256 hash descriptor stored in the AVB footer of `vendor_boot.img`:
- The original stock image uses AVB algorithm `NONE` (algorithm type 0), meaning `vendor_boot.img` itself is not signed with an asymmetric private key inside its own partition footer; its integrity hash is stored in `vbmeta_vendor`.
- However, when the bootloader is **LOCKED**, it requires that:
  1. `vbmeta` is signed by Lenovo's private RSA release key matching the hardware eFuses.
  2. `vbmeta_vendor` matches the signature inside `vbmeta`.
  3. `vendor_boot` matches the exact hash listed in `vbmeta_vendor`.

Since only Lenovo possesses the private RSA key required to sign `vbmeta` and `vbmeta_vendor`, an independently generated `vendor_boot` image cannot be added to the signed OEM chain.

---

## 4. Why Custom Key Enrollment (`avb_custom_key`) is NOT Feasible

On Google Pixel devices and a few select developer platforms, AVB allows enrolling a user-generated signing key into a special hardware key slot:
```bash
fastboot flash avb_custom_key my_custom_key.bin
```
**We audited the TB350XU bootloader commands and community testing records:**
1. **Command Not Implemented:** MediaTek LK on the TB350XU does not expose the `avb_custom_key` partition or enrollment command. The command returns `unknown command` or `FAILED (remote: not allowed in production)`.
2. **Hard-Brick Mechanism:** If a user runs `fastboot flashing lock` on a TB350XU with an untrusted or modified partition, the bootloader's cryptographic verification fails on the very next boot. The device halts with:
   ```
   dm-verity corruption
   Your device is corrupt. It can't be trusted and will not boot.
   ```
   Because the bootloader is now locked, it permanently rejects fastboot flashing commands, preventing recovery without JTAG or proprietary MediaTek authorized service center flash tools (SP Flash Tool with SLA authentication).

---

## 5. Official Recommendations for Safe Operation

1. **Keep Bootloader Unlocked:** Maintain the device with `Device state: unlocked`. This is standard and required for running custom kernel drivers or GSI ROMs.
2. **Disable Verification When Flashing:** Ensure dm-verity and verification flags are disabled across all vbmeta partitions when flashing modified images:
   ```bash
   fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img
   fastboot --disable-verity --disable-verification flash vbmeta_vendor vbmeta_vendor.img
   fastboot flash vendor_boot vendor_boot_himax_combined_final_candidate.img
   ```
3. **Restoring Factory Locked State:** If you ever wish to return to a locked bootloader:
   - First, flash the **100% original stock firmware** using the official Lenovo Rescue and Smart Assistant (LMSA) tool.
   - Verify the stock system boots properly.
   - Only then run `fastboot flashing lock`.
