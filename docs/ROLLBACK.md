# ROLLBACK AND RECOVERY GUIDE

- **Target Devices:** Lenovo Tab P11 Gen 2 (`TB350XU` / `TB350FU`)
- **Partition Modified:** `vendor_boot` (`vendor_boot_a` / `vendor_boot_b`) — **`boot` is never modified by this patch**
- **Stock S231018 Baseline `vendor_boot.img` SHA-256:** `0c06ebe186f39b1ec64398fc8e3bad74b0c2a7c4fae8134822f7adcc12c0a7c4`
*(Historical Android 12 `S020008` Stock `vendor_boot.img` SHA-256: `24fe1068b0b46a15480521a1df810ed23db55091371524264842a79064a2cfc6`)*

---

## 1. Safety Principles Before Flashing
1. **Bootloader Must Be Unlocked:** Verify `fastboot getvar unlocked` reports `yes`. Never flash modified `vendor_boot` on a locked bootloader.
2. **Never Relock Bootloader:** Relocking with any modified `vendor_boot` (or APatch/Magisk/KSU `boot`) triggers a Red State hard-brick (see [`BOOTLOADER_AND_AVB_FEASIBILITY.md`](BOOTLOADER_AND_AVB_FEASIBILITY.md)).
3. **Keep `boot` Separate:** Only `vendor_boot` carries `himax_mmi.ko`; your APatch / Magisk / KernelSU `boot` image remains untouched.
4. **Flash Active Slot First (`_a` Before `_b`):** Keeping the inactive fallback slot untouched during your first test boot gives an instant slot-switch recovery option if needed.

---

## 2. Flashing `vendor_boot_TB350XU_S231018_ULTIMATE_TOUCH.img`

1. Reboot to bootloader and verify fastboot + active slot:
   ```cmd
   adb reboot bootloader
   fastboot devices
   fastboot getvar current-slot
   fastboot getvar unlocked
   ```
2. Flash the active slot (`a` or `b`, matching `current-slot`):
   ```cmd
   fastboot flash vendor_boot_a vendor_boot_TB350XU_S231018_ULTIMATE_TOUCH.img
   fastboot reboot
   ```
   *(Or run `tools\FLASH_S231018_ULTIMATE_TOUCH.cmd` interactively.)*
3. Once Android boots and you verify touch/typing works cleanly, you may optionally sync the inactive backup slot from fastboot as well:
   ```cmd
   fastboot flash vendor_boot_b vendor_boot_TB350XU_S231018_ULTIMATE_TOUCH.img
   ```

*(AVB Note: On S231018 with unlocked bootloader / `orange` state, `androidboot.veritymode = enforcing` boots patched `vendor_boot` without needing `--disable-verity --disable-verification`.)*

---

## 3. Immediate Rollback to Factory Stock

### Option A: Switch Slot via Fastboot (If only active slot was flashed)
```cmd
fastboot set_active other
fastboot reboot
```

### Option B: Reflash Untouched Stock `vendor_boot.img`
From fastboot mode (hold **Power + Volume Down** if Android is unreachable):
```cmd
fastboot flash vendor_boot_a "TB350XU_USER_S231018_2601050930_MP_ROW\image\vendor_boot.img"
fastboot reboot
```
*(Replace `vendor_boot_a` with `vendor_boot_b` or flash both slots if both were updated.)*

### Option C: Remove Userspace APatch / Magisk / KSU Module Only
- In APatch / Magisk / KernelSU Manager -> **Modules** -> remove **Lenovo Tab P11 Gen 2 - Ultimate Touch & Performance Suite** and reboot, OR via ADB:
  ```bash
  adb shell su -c "touch /data/adb/modules/tb350xu_master_touch_fix/remove"
  adb reboot
  ```

---

## 4. Full Stock Emergency Rescue (Lenovo RSA / LMSA)
If fastboot itself is inaccessible:
1. Install **Lenovo Rescue and Smart Assistant (RSA / LMSA)** on Windows.
2. Choose **Tablet** -> `TB350XU` (or `TB350FU`) and hold **Volume Up** while plugging in USB to restore full stock firmware.
