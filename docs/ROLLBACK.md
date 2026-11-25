# Rollback & Safe Flashing Guide (`TB350XU` / `TB350FU` S231018)

- **Partition Modified:** `vendor_boot` (`vendor_boot_a` / `vendor_boot_b`) — **`boot` (kernel + root ramdisk) is never touched**
- **Stock S231018 `vendor_boot.img` SHA-256:** `0c06ebe186f39b1ec64398fc8e3bad74b0c2a7c4fae8134822f7adcc12c0a7c4`

---

## 1. Safety Rules Before Flashing
1. **Unlocked Bootloader Required:** Verify `fastboot getvar unlocked` prints `yes`. Do not flash modified `vendor_boot` on a locked device.
2. **Never Relock Bootloader:** Relocking with any modified `vendor_boot` or rooted `boot` partition causes a Red State hard-brick (see [`BOOTLOADER_AND_AVB_FEASIBILITY.md`](BOOTLOADER_AND_AVB_FEASIBILITY.md)).
3. **Flash Active Slot First:** Keep the inactive slot untouched during your first boot test so you retain an immediate fastboot slot-switch fallback.

---

## 2. Flashing `vendor_boot_TB350XU_S231018_touch_fix.img`

1. Reboot to bootloader and inspect slot & lock status:
   ```cmd
   adb reboot bootloader
   fastboot devices
   fastboot getvar current-slot
   fastboot getvar unlocked
   ```
2. Flash active slot only first (`a` or `b` matching `current-slot`):
   ```cmd
   fastboot flash vendor_boot_a vendor_boot_TB350XU_S231018_touch_fix.img
   fastboot reboot
   ```
   *(Or run `tools\flash_vendor_boot.cmd` interactively.)*
3. Once Android boots and touch/typing is verified working, optionally update the inactive backup slot too:
   ```cmd
   fastboot flash vendor_boot_b vendor_boot_TB350XU_S231018_touch_fix.img
   ```

*(AVB Note: With unlocked bootloader / `orange` state on S231018, `androidboot.veritymode = enforcing` boots patched `vendor_boot` cleanly without needing `--disable-verity --disable-verification` on `vbmeta`.)*

---

## 3. Immediate Rollback to Stock

### Option A: Switch Slot via Fastboot (If only active slot was flashed)
```cmd
fastboot set_active other
fastboot reboot
```

### Option B: Reflash Stock S231018 `vendor_boot.img`
From fastboot mode (hold **Power + Volume Down** while powering on if Android does not boot):
```cmd
fastboot flash vendor_boot_a "TB350XU_USER_S231018_2601050930_MP_ROW\image\vendor_boot.img"
fastboot reboot
```
*(Reflash `vendor_boot_b` as well if you flashed both slots.)*

### Option C: Disable or Remove Userspace Module Only
- Disable or remove **Lenovo Tab P11 Gen 2 Touch & Performance Fix (S231018)** in APatch / Magisk / KernelSU Manager and reboot, or over ADB:
  ```bash
  adb shell su -c "touch /data/adb/modules/tb350xu_touch_fix/remove"
  adb reboot
  ```

---

## 4. Full Firmware Rescue (Lenovo RSA / LMSA)
If fastboot itself is unavailable, use **Lenovo Rescue and Smart Assistant (RSA)** on Windows (hold **Volume Up** while connecting USB) to restore the complete official `TB350XU` / `TB350FU` factory image.
