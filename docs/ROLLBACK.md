# ROLLBACK AND RECOVERY GUIDE
**Target Device:** Lenovo Tab P11 Gen 2 (TB350XU)  
**Partition:** `vendor_boot`  
**Stock Baseline Image:** `vendor_boot.img` (SHA-256: `24fe1068b0b46a15480521a1df810ed23db55091371524264842a79064a2cfc6`)  

---

## 1. Safety Principles Before Flashing

1. **Your Bootloader Must Be UNLOCKED:** Do NOT attempt to flash this or any modified image if your device state is locked.
2. **Never Relock the Bootloader with This Image:** As detailed in `BOOTLOADER_AND_AVB_FEASIBILITY.md`, relocking will brick the tablet.
3. **The Original Image is Always Preserved:** The original untouched factory `vendor_boot.img` is stored in the root workspace directory. Keep multiple copies.
4. **Boot Partition is Untouched:** This project only modifies `vendor_boot`. Your `boot` partition (which contains KernelSU, the core Linux kernel image, and initramfs) is **never touched or altered**.

---

## 2. Flashing the Combined Final Candidate

To flash the final experimental candidate to your tablet:

### Step 1: Reboot into Fastboot Mode
```bash
adb reboot bootloader
```
Verify fastboot connection:
```bash
fastboot devices
```

### Step 2: Determine Current Active Slot
Check whether your tablet is currently on slot `a` or `b`:
```bash
fastboot getvar current-slot
```
*(Example output: `current-slot: a` or `current-slot: b`)*

### Step 3: Flash the Candidate to the Active Slot
Flash to the active slot (or specify both slots if desired):
```bash
# If on slot a:
fastboot flash vendor_boot_a vendor_boot_himax_combined_final_candidate.img

# If on slot b:
fastboot flash vendor_boot_b vendor_boot_himax_combined_final_candidate.img

# Or flash both slots to be certain:
fastboot flash vendor_boot vendor_boot_himax_combined_final_candidate.img
```

### Step 4: Reboot
```bash
fastboot reboot
```

---

## 3. Immediate Rollback Procedure (Returning to Factory Stock)

If the device exhibits any unexpected behavior, instability, or if you simply wish to restore 100% factory behavior:

### Step 1: Boot into Fastboot
Power down tablet, hold `Power + Volume Down` until the Fastboot screen appears, or run:
```bash
adb reboot bootloader
```

### Step 2: Flash the 100% Untouched Original Image
From the workspace root directory where `vendor_boot.img` is located:
```bash
fastboot flash vendor_boot vendor_boot.img
```

### Step 3: Verify Flash Success and Reboot
```bash
fastboot reboot
```
Your tablet is now completely restored to the exact factory touchscreen driver configuration.

---

## 4. Emergency Recovery (LMSA)

If fastboot mode becomes inaccessible for any reason:
1. Download and install the official **Lenovo Rescue and Smart Assistant (LMSA)** on a Windows PC.
2. Select **Rescue** -> **Tablet** -> Enter model `TB350XU`.
3. Follow the on-screen prompts to connect the tablet with Volume Up held while inserting the USB cable.
4. LMSA will re-flash the complete official factory firmware package.
