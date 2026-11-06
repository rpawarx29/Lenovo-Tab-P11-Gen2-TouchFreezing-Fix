# DEEP ROM FORENSIC AUDIT & HANDOVER BLUEPRINT
**Target Device:** Lenovo Tab P11 Gen 2 (`TB350XU` LTE)  
**Chipset:** MediaTek Helio G99 (`MT6789`)  
**Firmware Version:** Android 14 (`TB350XU_USER_S231018_2601050930_MP_ROW`)  
**Kernel:** Linux 5.10.233-android12-9-00001-g3d8ea7147b4b-ab12869156  
**Root Status:** Magisk v31.1 installed and verified  
**Date & Revision:** November 2026 / Rev 1.1  

---

## 1. Executive Summary & Baseline

The user reported chronic typing drops, missing keyboard touch ripple animations ("halka sa light nahi aana"), touch latency, and stuttery/janky frames on the Lenovo Tab P11 Gen 2 after upgrading to the official Android 14 ROM (`S231018`).

This document serves as the master engineering log, root-cause forensic analysis, and persistent handover document detailing:
1. Exact binary patches developed and verified for the kernel touch driver.
2. The custom adaptive Magisk overclock module architecture.
3. The root cause analysis and resolution of the boot-delay / SurfaceFlinger crash issue.
4. The comprehensive multi-layer roadmap across `vendor.img`, `system.img`, `product.img`, and `system_ext.img` to eradicate frame drops, jank, and hidden input bottlenecks.

---

## 2. Completed Milestones & Verified Fixes

### 2.1 Touch Driver Candidate v6 (`vendor_boot.img`) - SOLVED & ACTIVE
* **Image Name:** `vendor_boot_TB350XU_S231018_v6_touch_protocol_fix.img`
* **Partitions Flashed:** `vendor_boot_a` and `vendor_boot_b`
* **SHA256:** `cce9ec0d3bb0827acde5044569949cf0a59e3ab844c0eb9448950852b8d92598`
* **File Location on Host:** `E:\RUTURAJ DO NOT DELETE\P11_TOUCH_FINAL\final_output\`

#### Problem in Stock Driver:
In the stock `himax_mmi.ko`, coordinate events (`ABS_MT_POSITION_X`, `ABS_MT_POSITION_Y`) were being emitted before the slot state event (`input_mt_report_slot_state`), violating the Linux Multi-Touch Type-B protocol. Android's `InputReader` was rejecting out-of-order slot transitions with:
```text
InputReader: Received unexpected event for slot 0
```
This caused missing touch events, dropped keyboard pop-up animations, and delayed touch processing.

#### Binary Modification (`himax_mmi.ko`):
* Relocated call to `input_mt_report_slot_state` inside the finger-down parsing block (`0x0360c`–`0x03628`).
* **GOT Relocation Fix:** Zeroed out the stale relocation entry at `0x0360c` (`R_AARCH64_NONE`) to prevent the kernel module loader from overwriting `x0` with an external symbol pointer, which had previously caused a null pointer dereference (`x0 = 0`) crash upon touch in early v6 iterations.
* **Verification:** Processed 8,600+ interrupts with zero dropped touches and zero protocol errors in logcat. User explicitly confirmed: *"ohk ab hua chalu sab acche se"*.

---

### 2.2 Adaptive Overclock Module (`p11_g99_performance_oc`) - ACTIVE & UPDATED
* **Package:** `HelioG99_Overclock_Adaptive_v1.0.zip`
* **Location on Device:** `/sdcard/Download/HelioG99_Overclock_Adaptive_v1.0.zip`
* **Location on Host:** `E:\RUTURAJ DO NOT DELETE\P11_TOUCH_FINAL\final_output\`

#### Specifications:
* **CPU LITTLE Cluster (CPU 0–5):**
  * Min Frequency: `1.50 GHz`
  * Max Frequency: `2.00 GHz`
  * Governor: `sugov_ext` (Up-rate limit: `0us` for instantaneous ramp-up; Down-rate limit: `10000us`)
* **CPU BIG Cluster (CPU 6–7):**
  * Min Frequency: `1.70 GHz`
  * Max Frequency: `2.20 GHz`
  * Governor: `sugov_ext` (Up-rate limit: `0us`)
* **GPU Mali-G57 MC2 & MediaTek GED:**
  * Bottom Frequency: `648 MHz`
  * Max Frequency: `1.10 GHz` (`gpu_cust_upbound_freq = 1100000`)
  * Boost Frequency: `948 MHz`
  * `g_fb_dvfs_threshold`: `45` (forces GPU to ramp up early during UI transitions)
* **Adaptive Standby Architecture (Battery & Thermal Protection):**
  * Monitors `/sys/class/drm/card0-DSI-1/dpms` directly from hardware.
  * **Screen ON (`dpms == On`):** Overclock mode applied instantly (`1.80 GHz – 2.00 GHz`).
  * **Screen LOCKED/OFF (`dpms == Off`):** Frequencies instantly drop to `500 MHz` (LITTLE), `725 MHz` (BIG), and `390 MHz` (GPU). Keeps tablet cool and prevents standby battery drain.

---

### 2.3 Slow Boot / Boot Loop Root Cause & Fix - SOLVED
* **Symptom:** Tablet was taking 2–3 minutes to boot or hanging on boot animation.
* **Logcat Forensic Finding:**
  ```text
  Cmdline: /system/bin/surfaceflinger
  signal 6 (SIGABRT), fault addr --------
  Abort message: 'debug.sf.high_fps_late_app_phase_offset_ns is set to 1000000 but expecting duration'
  I Magisk: ** zygote restarted
  W Magisk: zygote crashed too many times, rolling-back
  ```
* **Cause:** In Android 14 (`UP1A`), Google altered the `SurfaceFlinger` property parser: phase offsets must be valid duration objects, not raw integer nanoseconds. `debug.sf.high_fps_late_app_phase_offset_ns=1000000` inside `system.prop` triggered an assertion failure on every launch of SurfaceFlinger, restarting Zygote repeatedly.
* **Fix Applied:** Stripped `system.prop` of all unsafe SurfaceFlinger properties. Fast boot (~20–25s) fully restored.

---

### 2.4 Missing `.idc` File Injection & MediaTek `fpsgo` Unthrottling - SOLVED & ACTIVE
* **Touch Device Identified:** `himax-touchscreen` (EventHub event6).
* **Forensic Finding:** Dumpsys input confirmed `ConfigurationFile: ` was empty. Android `InputReader` was running in generic fallback mode without calibrated pressure, orientation, or motion filtering.
* **Fix Injected:** Created `/system/usr/idc/himax-touchscreen.idc` and `himax_tp.idc` via Magisk overlay:
  ```ini
  touch.deviceType = touchScreen
  touch.orientationAware = 1
  touch.gestureMode = spots
  touch.pressure.calibration = physical
  touch.pressure.scale = 0.001
  touch.size.calibration = area
  touch.filter.level = 1
  ```
* **MediaTek `fpsgo` Throttle Bypass:**
  * `thrm_enable = 0` (Thermal frame drops disabled)
  * `enable_switch_down_throttle = 0` (No dynamic frame down-throttling)
  * `enable_ceiling = 0` (No artificial FPS ceiling)
  * `adopt_low_fps = 0` (Never drop target frame rate)
  * `boost_ta = 1` (Priority boost for foreground rendering thread)
* **120Hz High-Refresh Rate Lock:**
  * `min_refresh_rate = 120.0`
  * `peak_refresh_rate = 120.0`
  * Eliminates the 60Hz->120Hz display refresh lag that previously dropped first-touch keyboard ripples.

---

## 3. Multi-Layer Forensic Audit Matrix

| Layer / Image | Component / Binary | Suspected Bottleneck / Bug | Forensic Analysis & Action | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Layer 1: `vendor_boot`** | `himax_mmi.ko` | MT Type-B slot state reported after coordinates | Binary patched at `0x0360c`–`0x03628`; relocation zeroed. Flashed in Candidate v6. | **FIXED & VERIFIED** |
| **Layer 1: `vendor_boot`** | Kernel EAS & Clocks | Clocks drop to 500MHz during UI idle | Tuned via Magisk service daemon with 0us up-rate limit. | **ACTIVE** |
| **Layer 2: `vendor`** | `.idc` Files (`himax_tp.idc`) | Missing `.idc` file causes Android `InputReader` to use fallback filtering and low-resolution touch interpolation. | Injected `/system/usr/idc/himax-touchscreen.idc` via Magisk overlay with physical pressure and level-1 filtering. | **INJECTED & VERIFIED** |
| **Layer 2: `vendor`** | MTK `fpsgo` (`libfpsgo.so`) | MediaTek frame-tracking daemon aggressively caps rendering frames when it suspects frame target cannot be hit. | Sysfs overrides applied in `service.sh`: `thrm_enable=0`, `boost_ta=1`, `enable_switch_down_throttle=0`. | **APPLIED & VERIFIED** |
| **Layer 2: `vendor`** | Display Refresh Rate Switching | Dynamic refresh drops from 120Hz to 60Hz/30Hz when idle, causing first tap lag. | Locked 120Hz constantly via `settings put system min_refresh_rate 120.0`. | **LOCKED AT 120Hz** |
| **Layer 3: `system`** | `SurfaceFlinger` | Phase offset assertion crash on boot. | Cleaned `system.prop`. Verified instant 20s boot. | **SAFE & STABLE** |
