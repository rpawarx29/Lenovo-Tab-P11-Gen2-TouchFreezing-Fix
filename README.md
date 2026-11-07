# Lenovo Tab P11 Gen 2 (TB350XU / TB350FU)
## Official Android 14 (S231018) Stable High-Sensitivity Touch Fix & Performance Suite (v5.2.0)

[![Release](https://img.shields.io/badge/Release-v5.2.0-brightgreen.svg)](https://github.com/rpawarx29/Lenovo-Tab-P11-Gen2-TouchFreezing-Fix/releases/tag/v5.2.0)
[![Firmware](https://img.shields.io/badge/Firmware-Android%2014%20(S231018)-blue.svg)](https://github.com/rpawarx29/Lenovo-Tab-P11-Gen2-TouchFreezing-Fix)
[![Hardware](https://img.shields.io/badge/Chipset-MediaTek%20Helio%20G99%20(MT6789)-orange.svg)](https://github.com/rpawarx29/Lenovo-Tab-P11-Gen2-TouchFreezing-Fix)
[![License](https://img.shields.io/badge/License-GPL%202.0-yellow.svg)](LICENSE)

The definitive, hardware-verified solution for the infamous **Lenovo Tab P11 Gen 2** touch unresponsiveness, typing freezing, dropped keystrokes, missing touch ripple lights, and slide registration issues on official **Android 14 (S231018)** firmware.

---

### 🚨 Root Causes Identified & Fixed

| Issue Observed | Firmware Cause | Engineering Fix in v5.2.0 |
| :--- | :--- | :--- |
| **Typing Freeze & Edge Lockup** | Driver registered interrupts as Edge-Triggered (`IRQF_TRIGGER_FALLING`). Rapid typing caused back-to-back interrupts to collide, dropping falling edges and starving the interrupt controller. | Patched all 5 interrupt registration and trigger sites in `himax_mmi.ko` to **Active-Low Level-Triggered** (`0x2008` = `IRQF_TRIGGER_LOW \| IRQF_ONESHOT`). Interrupt lines are now continuously drained. |
| **Missing Key Ripple Lights & Dropped Light Taps** | Controller mutual capacitance scanning operated at Lenovo's weak default threshold, failing to register fast, light fingertip strikes on virtual keyboards. | Hook `H5` at `0x1a50c` calls `himax_mcu_set_HSEN_enable(1)`, writing `0xa55aa55a` to the controller on every boot and wake. Restores full hardware High-Sensitivity Mode. |
| **Laggy Typing & Gestures** | Userspace `.idc` pressure-flattening overrides caused Android's `TouchInputMapper` to debounce touches and delay `ACTION_DOWN` delivery. | Removed artificial IDC restrictions; restored clean native Android input pipeline with full physical pressure resolution. |
| **Micro-Stutters & Display Lag** | Display dynamic refresh rate toggled between 60Hz and 120Hz, dropping initial frame animations. | Locked continuous 120Hz high refresh rate and bypassed MediaTek `fpsgo` thermal throttling. |
| **Interrupt Processing Delay** | Little cores (handling touch IRQs on CPU0) throttled down to 500 MHz during active use. | Adaptive performance module dynamically maintains CPU0-5 at **1.5–2.0 GHz** and big cores at **2.2 GHz** with **0us schedutil latency** while screen is awake. |

---

### 📦 Release Assets & Checksums (v5.2.0)

Download from the [Official v5.2.0 Release](https://github.com/rpawarx29/Lenovo-Tab-P11-Gen2-TouchFreezing-Fix/releases/tag/v5.2.0):

| File Name | Size | SHA-256 Checksum | Purpose |
| :--- | :--- | :--- | :--- |
| **`vendor_boot_TB350XU_S231018_v5.2_high_sensitivity.img`** | 67,108,864 bytes | `c55dc35d69ff64901f00b1438f99c9c73d5774f03b8fa342a00d88395870e354` | Kernel Touch Driver (`himax_mmi.ko`) with HSEN + Level IRQ |
| **`FLASH_TOUCH_V5.2.cmd`** | 911 bytes | `88a1d8e1c7ea31f6895a4695cb3067af0e59b5bec7115ead1f2ec2f85f2bbcd0` | 1-Click Fastboot Flasher (Windows) |
| **`HelioG99_Overclock_Adaptive_v1.0.zip`** | 2,331 bytes | `f95560ab33744fe4cdc38487cfbcc6e5ba29e9a2ed86482f2ba054565b4afddd` | Magisk Performance & 120Hz Overclock Module |
| **`AlwaysStrong-v1.0.5-inject.zip`** | 4,784,229 bytes | `9cb01baac328c597898e0b047f8d3aa1d559d40d095d7973173491444aa05eb9` | Magisk Play Integrity Strong Verdict Bypass |
| **`HMA-OSS-ZYGISK-future-5398de45-release.zip`** | 2,582,481 bytes | `fca7140047041425c7652476385ebdd37e8d2d7ce881b88aa462ad9798c16e79` | Magisk Root Isolation Backend |

---

### ⚡ Step-by-Step Installation Guide

#### Step 1: Flash the Kernel Touch Driver
1. Download `vendor_boot_TB350XU_S231018_v5.2_high_sensitivity.img` and `FLASH_TOUCH_V5.2.cmd`.
2. Connect your tablet to your PC via USB.
3. Boot into **Fastboot Mode**:
   ```cmd
   adb reboot bootloader
   ```
   *(Or hold `Power + Volume Down` while booting).*
4. Double-click `FLASH_TOUCH_V5.2.cmd` (or execute manually):
   ```cmd
   fastboot flash vendor_boot_a vendor_boot_TB350XU_S231018_v5.2_high_sensitivity.img
   fastboot flash vendor_boot_b vendor_boot_TB350XU_S231018_v5.2_high_sensitivity.img
   fastboot reboot
   ```

#### Step 2: Install Performance & System Modules
1. Download `HelioG99_Overclock_Adaptive_v1.0.zip` and transfer to the tablet.
2. Open the **Magisk App** -> Tap **Modules** -> **Install from storage**.
3. Select `HelioG99_Overclock_Adaptive_v1.0.zip` and let it complete.
4. *(Optional for Banking & Play Integrity):* Install `AlwaysStrong-v1.0.5-inject.zip` and `HMA-OSS-ZYGISK-future-5398de45-release.zip`.
5. **Reboot** the tablet.

---

### 🔬 Technical Verification & Binary Architecture

- **Kernel Version:** Linux 5.10.233-android12-9-g9568a331d924 SMP preempt
- **Interrupt Routing:** IRQ 206 (`mtk-eint 54 Level himax_tp`)
- **Hook Architecture:**
  - `H1` (0x249c8): Propagate SPI read status to caller
  - `H2` (0x249dc): Reject short SPI transfers
  - `H3` (0x249f0): Safe contact release before reset
  - `H4` (0x24a00): Safe contact release before exception recovery
  - `H5` (0x24a10): HSEN mutual capacitance mode enable
- **Display Setting Note:** Your preferred display density / size (e.g., 200 DPI override) is fully respected and never modified by this fix.

---

### 👤 Credits & Support

- **Lead Developer & Reverse Engineer:** **Ruturaj Pawar** ([@rpawarx29](https://github.com/rpawarx29)) with Antigravity AI
- **Telegram Support & Inquiries:** [@ocean_mystic](https://t.me/ocean_mystic)
