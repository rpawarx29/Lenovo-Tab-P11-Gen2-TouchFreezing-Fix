# Lenovo Tab P11 Gen 2 (TB350XU / TB350FU) & Idea Tab Pro
## Ultimate Touch Freezing Fix, Precision Pen 2 Stabilization & Performance Suite (v6.0.0 Pristine)

[![Release](https://img.shields.io/badge/Release-v6.0.0--Pristine-brightgreen.svg)](https://github.com/rpawarx29/Lenovo-Tab-P11-Gen2-TouchFreezing-Fix/releases)
[![Firmware](https://img.shields.io/badge/Firmware-Android%2012%20(S020008)%20%7C%20Android%2014%20(S231018)-blue.svg)](https://github.com/rpawarx29/Lenovo-Tab-P11-Gen2-TouchFreezing-Fix)
[![Hardware](https://img.shields.io/badge/Chipset-MediaTek%20Helio%20G99%20(MT6789)-orange.svg)](https://github.com/rpawarx29/Lenovo-Tab-P11-Gen2-TouchFreezing-Fix)
[![Support](https://img.shields.io/badge/Root-KernelSU%20%7C%20Magisk-red.svg)](https://github.com/rpawarx29/Lenovo-Tab-P11-Gen2-TouchFreezing-Fix)
[![License](https://img.shields.io/badge/License-GPL%202.0-yellow.svg)](LICENSE)

The definitive, hardware-verified engineering solution for the touchscreen freezing, typing latency, dropped keystrokes, slide-to-click misclassifications, and active stylus (Precision Pen 2) stroke wobble across the **Lenovo Tab P11 Gen 2** and **Idea Tab Pro / Xiaoxin Pad** series.

---

## 📱 Supported Devices & Firmware Builds

* **Target Hardware:** Lenovo Tab P11 (2nd Gen) – Models `TB350XU` (LTE) and `TB350FU` (Wi-Fi)
* **Secondary Reference:** Lenovo Idea Tab Pro / Xiaoxin Pad Pro Series
* **Supported Official Stock ROMs:**
  * **Android 12:** `Lenovo_Tab_P11_2nd_Gen_TB350XU_MT6789_USER_S020008_221025`
  * **Android 13 / 14:** `TB350XU_S231018` / `TB350FU_S231018` Maintenance Releases
* **Root Compatibility:** **KernelSU** (v0.9.5+ / 32680 native kernel unmount) & **Magisk** (v26.0+)

---

## 🚨 The Real Problem: Empirical Symptom Profile & Video Evidence

Across Lenovo official forums, Reddit, and XDA, thousands of users have reported identical symptoms occurring 6 to 7 months post-launch or after public OTA updates:

1. **Periodic Digitizer Freezes:** The screen randomly stops responding to touches for 1 to 2 seconds during typing/browsing, and locks up for **15 to 30+ seconds** during gaming or heavy use.
2. **Definitive Proof OS Has Not Crashed:** While touch input is completely dead, background videos, audio, game timers, and graphics continue rendering smoothly. Furthermore, connecting an external USB/OTG mouse moves and clicks with zero latency, proving the SoC, GPU, and Android OS are healthy, and only the touch input stack has stalled.
3. **The "Power Button Sleep/Wake" Workaround:** Pressing the physical Power button to sleep and wake the device forces the Linux kernel driver to execute a resume re-initialization (`himax_common_resume`), temporarily unhanging the digitizer until the next freeze.
4. **Documented Video Proof:**
   * **Video 1 (`VID_20260915_160857949.mp4`):** Live gaming footage on Lenovo Tab P11 Gen 2. Touch completely dies during active combat while game graphics run at 60/120 FPS; restored only by a physical power button sleep/wake toggle.
   * **Video 2 (`video6280748702365655865.mp4`):** Live virtual keyboard typing footage. Repeated taps on keys are swallowed by the driver, key popups freeze on screen, and rapid typing produces mangled input.

---

## 🔬 The 16 Root Causes Identified & Fixed

| Bug ID | Subsystem | Stock Flaw | Engineering Solution |
| :--- | :--- | :--- | :--- |
| **BUG-01** | `himax_mmi.ko` | Unconditional `mov w0, #1` return in `hx83102j_read_event_stack` bypassing recovery on SPI read fail | Restored return-code propagation to force hardware bus recovery on SPI faults |
| **BUG-02** | `himax_mmi.ko` | Unchecked DMA transfer length in `himax_bus_read` causing coordinate packet truncation | Strict buffer length bounds-checking prior to parsing multi-touch DMA packets |
| **BUG-03** | `himax_mmi.ko` | Missing contact release on driver reset causing phantom slots and ghost touches | Explicit slot release sequence (`ABS_MT_TRACKING_ID -1`) across all slots before reset |
| **BUG-04** | `himax_mmi.ko` | Prevent-notch buffer pointer offset mismatch causing false boundary rejections | Aligned boundary exclusion coordinates with native 2000x1200 panel geometry |
| **BUG-05** | `himax_mmi.ko` | Dormant high-sensitivity mode never activated in public firmware | Dynamically activated high-sensitivity polling on initial touch contact |
| **BUG-06** | `himax_mmi.ko` | Charger symbol width mismatch (`tp_usb_plug_status`) disabling noise filtering | Corrected symbol width mapping to allow charger noise suppression switching |
| **BUG-07** | `himax_mmi.ko` | Multi-packet SPI mutex granularity gap allowing race conditions during fast typing | Extended mutex locking across complete multi-packet transaction cycles |
| **BUG-08** | `himax_mmi.ko` | Falling-edge vs Level-low interrupt deadlock during fast typing | Transitioned interrupt handling to level-triggered mode with proper EOI ack |
| **BUG-09** | `himax_mmi.ko` | Contact release and slot clearing suppression on quick finger lift | Guaranteed immediate slot state clear on every finger-up transition |
| **BUG-10** | IDC Profile | Artificial pressure calibration (`touch.pressure.scale = 0.005`) causing 1-second tap delay | Set `touch.pressure.calibration = none` and `touch.size.calibration = diameter` |
| **BUG-11** | IDC Profile | Framework motion smoothing filter (`filter.level = 1`) misclassifying slides as clicks | Disabled framework motion dampening for raw, instantaneous coordinate delivery |
| **BUG-12** | EventHub | Coordinates dispatched before tracking ID in Linux Type-B stream | Enforced strict Type-B event ordering (`SLOT` -> `TRACKING_ID` -> coordinates) |
| **BUG-13** | DVFS / Scheduler | MediaTek `fpsgo` thermal engine throttling CPU0 to 500 MHz, starving touch SPI IRQ | Set `fpsgo_enable = 0`, `boost_ta = 1`, and maintained Little cluster baseline frequency |
| **BUG-14** | Display Subsystem | Dynamic 60Hz/48Hz throttling causing touch digitizer sampling rate collapse | Locked 120.00 Hz refresh (`min_refresh_rate = 120.0`, `peak_refresh_rate = 120.0`) |
| **BUG-15** | SystemUI | Broken notification window blur scrim (`disable_window_blurs = 0`) stalling GPU | Set `disable_window_blurs = 1` globally to bypass broken shader pipeline |
| **BUG-16** | Platform Driver | Hardware vibrator electrical/mechanical feedback inducing SPI bus noise | Unbound `soc:regulator_vibrator` from platform driver and muted haptics |

---

## 🖊️ Precision Pen 2 Active Stylus Stroke Stabilization

Stock Lenovo firmware mistakenly configures the active stylus in `/vendor/usr/idc/himax-stylus.idc` as:
```ini
touch.deviceType = pointer  # Triggers mouse pointer acceleration curves!
```
This causes diagonal line wobble and micro-jitter. Our updated `himax-stylus.idc` fixes this completely:
```ini
touch.deviceType = touchScreen
touch.orientationAware = 1
touch.gestureMode = spots
touch.pressure.calibration = physical
touch.pressure.scale = 0.000244140625  # 12-bit linear 4096 pressure levels
touch.distance.calibration = scaled
touch.distance.scale = 1.0
touch.filter.level = 2                  # Moving-average anti-jitter filter
```

---

## ⚡ Installation Instructions

### Method A: KernelSU (Recommended – 100% Stealth & Banking App Ready)
1. Install **KernelSU Manager** on your tablet.
2. Ensure your kernel is patched with KernelSU (GKI 5.10.101+).
3. Place `himax-touchscreen.idc` and `himax-stylus.idc` into `/data/system/devices/idc/`:
   ```bash
   adb push himax-touchscreen.idc /data/local/tmp/
   adb push himax-stylus.idc /data/local/tmp/
   adb shell su -c "cp /data/local/tmp/*.idc /data/system/devices/idc/; chmod 644 /data/system/devices/idc/*.idc; chown system:system /data/system/devices/idc/*.idc"
   ```
4. Flash the **`helio_g99_oc`** module in KernelSU Modules tab for 120Hz lock, CPU/GPU performance optimization, and adaptive battery saver.
5. Reboot tablet.

### Method B: Magisk
1. Flash the patched `vendor_boot` image in Fastboot mode:
   ```cmd
   fastboot flash vendor_boot_a vendor_boot_TB350XU_S231018_v6.0_pristine_touch.img
   fastboot flash vendor_boot_b vendor_boot_TB350XU_S231018_v6.0_pristine_touch.img
   fastboot reboot
   ```
2. Open **Magisk** -> **Modules** -> **Install from storage** -> Select `Helio_G99_Extreme_OC_120Hz_v3_Pristine.zip`.
3. Reboot tablet.

---

## 📄 Formal Technical Escalation to Lenovo
A complete, documented formal escalation letter containing global community evidence across Lenovo Tab P11 Gen 2, P11/P12, M10, and Idea Tab Pro is available in:
👉 **[`docs/EXECUTIVE_ESCALATION_LETTER_TO_LENOVO.md`](docs/EXECUTIVE_ESCALATION_LETTER_TO_LENOVO.md)**

---

## 👤 Credits & Maintainers
* **Lead Developer & Reverse Engineer:** Ruturaj Pawar ([@rpawarx29](https://github.com/rpawarx29)) with Antigravity AI
* **Special Thanks:** Independent Open-Source Android Kernel Community for the Idea Tab Pro touch recovery breakthrough.
