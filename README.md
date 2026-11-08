# Lenovo Tab P11 Gen 2 (TB350XU / TB350FU)
## Official Android 14 (S231018) Pristine Multi-Touch Fix & Zero-Latency Performance Suite (v6.0.0)

[![Release](https://img.shields.io/badge/Release-v6.0.0-brightgreen.svg)](https://github.com/rpawarx29/Lenovo-Tab-P11-Gen2-TouchFreezing-Fix/releases/tag/v6.0.0)
[![Firmware](https://img.shields.io/badge/Firmware-Android%2014%20(S231018)-blue.svg)](https://github.com/rpawarx29/Lenovo-Tab-P11-Gen2-TouchFreezing-Fix)
[![Hardware](https://img.shields.io/badge/Chipset-MediaTek%20Helio%20G99%20(MT6789)-orange.svg)](https://github.com/rpawarx29/Lenovo-Tab-P11-Gen2-TouchFreezing-Fix)
[![License](https://img.shields.io/badge/License-GPL%202.0-yellow.svg)](LICENSE)

The definitive, hardware-verified solution for the **Lenovo Tab P11 Gen 2** touch unresponsiveness, typing freezing, dropped keystrokes, delayed toggles, sticky touch releases, and slide-to-click misclassifications on official **Android 14 (S231018)** firmware.

---

### 🚨 Root Causes Identified & Fixed

| Issue Observed | Firmware Cause | Engineering Fix in v6.0.0 |
| :--- | :--- | :--- |
| **Typing Drops & Missed Keystrokes** | Stock `himax_mmi.ko` dispatched coordinates before tracking ID, causing Android `InputReader` to drop touch events | **P10 Type-B Event Ordering:** Dispatches `ABS_MT_TRACKING_ID` early via `input_mt_report_slot_state` before coordinates |
| **Sticky Releases & Lingering Touches** | Forced Level-Low IRQ (0x2008) kept the interrupt line lingering low after finger lift | **Native Falling Edge IRQ (0x2002):** Restores hardware edge trigger so touches terminate instantaneously |
| **1-Second Toggle / Switch Delay** | Artificial physical pressure scaling (`0.005`) caused Android to detect touch as only 5% pressure | **Zero-Latency IDC:** Sets `touch.pressure.calibration = none` for instant 100% full contact pressure on touch down |
| **Slide-to-Click Misclassification** | Motion smoothing filter (`filter.level = 1`) delayed motion updates, converting swipes into accidental clicks | **Clean IDC:** Disables motion filter delays so swipes register immediately as scrolls |
| **Touchscreen Freezing (Black/Frozen Screen)** | SPI bus transfer error ignored by driver; reset without contact release caused permanent freeze | **P1–P5 Anti-Freeze:** Complete SPI status checks and `himax_release_all_points()` on recovery |
| **UI Stutter & Frame Drops** | Dynamic 60Hz/48Hz throttling and MediaTek `fpsgo` thermal ceiling down-throttling CPU0 to 500 MHz | **120Hz Lock & Overclock:** Locks 120.00 Hz refresh and CPU Little cluster to 1.5–2.0 GHz, Big cluster to 1.7–2.2 GHz |

---

### 📥 Downloads

All downloads are verified and available on the **[GitHub Releases Page](https://github.com/rpawarx29/Lenovo-Tab-P11-Gen2-TouchFreezing-Fix/releases/tag/v6.0.0)**.

---

### ⚡ Installation Instructions

#### Step 1: Flash the Touch Fix Kernel (`vendor_boot`)
1. Download `vendor_boot_TB350XU_S231018_v6.0_pristine_touch.img` and `FLASH_TOUCH_V6.0_PRISTINE.cmd`.
2. Connect your tablet via USB and reboot into **Fastboot Mode**:
   ```cmd
   adb reboot bootloader
   ```
3. Run `FLASH_TOUCH_V6.0_PRISTINE.cmd` (or execute manually):
   ```cmd
   fastboot flash vendor_boot_a vendor_boot_TB350XU_S231018_v6.0_pristine_touch.img
   fastboot flash vendor_boot_b vendor_boot_TB350XU_S231018_v6.0_pristine_touch.img
   fastboot reboot
   ```

#### Step 2: Install Performance Module (Via Magisk)
1. Open the **Magisk App** -> **Modules** -> **Install from storage**.
2. Flash `Helio_G99_Extreme_OC_120Hz_v3_Pristine.zip`.
3. (Optional) Flash `AlwaysStrong-v1.0.5-inject.zip` and `HMA-OSS-ZYGISK-future-5398de45-release.zip` for banking apps and Play Integrity.
4. Reboot your tablet.

---

### 👤 Credits
- **Lead Developer & Reverse Engineer:** Ruturaj Pawar ([@rpawarx29](https://github.com/rpawarx29)) with Antigravity AI
- **Telegram Support:** [@ocean_mystic](https://t.me/ocean_mystic)
