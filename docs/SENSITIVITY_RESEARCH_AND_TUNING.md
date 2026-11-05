# SENSITIVITY RESEARCH, SENSING CAPABILITIES AND TUNING ANALYSIS
**Target Subsystem:** Himax HX83102J Capacitive Touch & Active Stylus Subsystem  
**Device:** Lenovo Tab P11 Gen 2 (TB350XU)  
**Report Scope:** Comprehensive Multi-Layer Sensitivity Audit  

---

## 1. Architectural Layer Separation

To understand touchscreen sensitivity, one must strictly differentiate the five distinct architectural layers governing capacitive touch detection:

```
[Layer A: Controller Silicon & On-Chip Firmware]
   │  - Analog Front End (AFE), TX drive voltage, RX charge integration
   │  - Baseline mutual-capacitance calibration (ReK), raw ADC quantization
   │  - Firmware DSP: IIR/FIR noise filtering, 2D spatial filtering, peak detection
   │  - Contact detection thresholds (delta-C threshold to trigger contact)
   │  - Palm rejection bounding box and aspect-ratio classifiers
   ▼
[Layer B: Firmware Configuration Block (SRAM Zero-Flash Tables)]
   │  - Touch configuration table (loaded from host during boot/resume)
   │  - Dynamic noise profiles (charger connected vs battery mode)
   │  - Glove / High-Sensitivity (HSEN) threshold tables
   │  - Edge / notch bounding coordinates and dampening coefficients
   ▼
[Layer C: Himax Linux Kernel Driver (`himax_mmi.ko`)]
   │  - SPI packet transport and bus pacing
   │  - Mode switches via command registers (HSEN: 0x10007F14, USB: 0x10007F38)
   │  - Notch parameters forwarding (`fp_set_prevent_notch`)
   │  - Translates controller packet coordinates to Linux `input_event` structs
   ▼
[Layer D: MediaTek Device Tree & Board Level Configuration (DTB / DTBO)]
   │  - SPI bus frequency (clock speed, e.g. 15MHz-25MHz)
   │  - Interrupt trigger type (`IRQ_TYPE_EDGE_FALLING` vs `LEVEL_LOW`)
   │  - Display panel synchronization signals (`disp_notifier`)
   ▼
[Layer E: Android Userspace Input Framework (`InputReader` / IDC File)]
   │  - `touch.deviceType = touchScreen`
   │  - `touch.pressure.scale`, `touch.size.calibration`
   │  - Palm rejection geometry and edge exclusion zones
   │  - Pointer velocity calculation, tap-drag hysteresis, gestures
```

---

## 2. Controller Firmware vs Driver Realities

### 2.1 The Host Driver Does NOT Have an Arbitrary Sensitivity Slider
Reverse-engineering of the entire `.text` and `.data` of `himax_mmi.ko` confirms:
1. **No Host Pressure Filtering:** The driver does **not** compare finger pressure against a host threshold before emitting `ABS_MT_POSITION_X/Y`. When the controller reports a point in `hx_touch_data`, the host driver forwards it directly to Android. Raising reported pressure in software cannot resurrect a touch that the controller failed to detect.
2. **Fixed Firmware Register Interface:** The HX83102J does **not** expose continuous analog threshold adjustment registers (like "detection_threshold = 42 mV") through standard SPI register writes.
3. **Register `0x10007F14` is the Official HSEN Interface:**
   - Address: `0x10007F14` (`fw_addr_hsen_enable`)
   - Enable value: `0xA55AA55A` (Alternating bit pattern handshake token)
   - Disable value: `0x00000000`
   - Readback verification: Up to 5 attempts to confirm acceptance.

### 2.2 What High-Sensitivity (HSEN) Mode Actually Does in Firmware
When `0xA55AA55A` is written to `0x10007F14`, the controller's internal MCU changes its DSP detection algorithm:
- **Lower Delta-C Cutoff:** Lowers the minimum mutual-capacitance deviation ($\Delta C$) required to distinguish a finger from background noise.
- **Enhanced Edge Detection:** Compensates for electric field fringing near the bezel.
- **Smaller Contact Footprint:** Allows smaller contact areas (such as fingertips through thin gloves or glass screen protectors) to be classified as valid touches rather than rejected as noise spikes.

---

## 3. Investigating Further Sensitivity Improvements

### 3.1 Can We Arbitrarily Increase Sensitivity Further via Binary Patching?
**Warning against pseudo-engineering:**
A superficial patch that invents random register addresses (e.g. writing `0xFFFFFFFF` to undocumented addresses) risks putting the controller MCU into an invalid state, causing permanent controller lockup or erratic ghost tapping.

Genuine improvements must operate within confirmed hardware capabilities:

| Mechanism | Controlling Layer | Can be tuned safely in host binary? | Analysis & Recommendation |
|---|---|---|---|
| **HSEN Activation** | Layer C / B | **YES (Implemented)** | Activating `himax_mcu_set_HSEN_enable(1)` on boot and resume via [P7] safely commands the firmware's built-in high-sensitivity profile. |
| **Charger Noise Filter (USB Mode)** | Layer C / B | **YES (Verified)** | The controller firmware switches to a higher noise-rejection filter table when USB is connected (`0x10007F38`). Preserving this logic ensures stability when charging. |
| **Prevent-Notch Offset Fix** | Layer C | **YES (Implemented)** | Correcting the command buffer pointer in [P6] prevents edge-rejection corruption upon recovery. |
| **SPI Bus Polling / Latency** | Layer C / D | **NO** | HX83102J is interrupt-driven (`request_threaded_irq`). Polling does not increase scan rate and wastes CPU power. |
| **AFE TX/RX Drive Voltages** | Layer A | **NO** | Hardcoded inside encrypted/signed controller firmware loaded from vendor partition (`/vendor/firmware/`). Modifying without official sign-off bricks the IC. |
| **Android Tap Hysteresis** | Layer E | **YES (Userspace IDC)** | Android's `idc` file can tune pointer speed and tap debounce thresholds independently of root or kernel changes. |

---

## 4. Android Userspace Sensitivity Tuning (`IDC`)

To achieve the best possible sensitivity for light taps without kernel instability, Android provides Input Device Configuration (`.idc`) files.
For `himax_mmi` / `himax-touchscreen`, an IDC file can be placed at:
`/vendor/usr/idc/himax-touchscreen.idc` or `/system/usr/idc/himax-touchscreen.idc`

Recommended tuning profile for high responsiveness:
```ini
# Himax HX83102J High-Responsiveness IDC Configuration
touch.deviceType = touchScreen
touch.orientationAware = 1

# Reduce tap movement jitter without suppressing light taps
touch.pressure.calibration = physical
touch.pressure.scale = 0.001

# Size calibration: recognize smaller contact points (light touches)
touch.size.calibration = normalized
touch.size.scale = 1.0
touch.size.bias = 0

# Gesture & edge tuning
touch.gestureMode = spots
```

---

## 5. Conclusions on Sensitivity Engineering

1. **[P7] Activates the Maximum Supported Physical Sensitivity:** The controller's official HSEN profile is now activated dynamically during active touch operation.
2. **Ghost-Touch Mitigation:** Because HSEN is disabled during system suspend and re-validated upon resume, baseline drift does not trigger runaway phantom touches while the screen is asleep.
3. **Firmware Integrity Preserved:** No unsupported opaque firmware bytes are altered, preventing touchscreen bricking or irreversible calibration loss.
