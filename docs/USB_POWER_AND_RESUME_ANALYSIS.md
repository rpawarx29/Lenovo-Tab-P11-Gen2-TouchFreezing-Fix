# USB POWER, CHARGING & RESUME SUBSYSTEM ANALYSIS
**Target Subsystem:** Power, USB Charger Framework, and Suspend/Resume Interaction  
**Device:** Lenovo Tab P11 Gen 2 (TB350XU)  
**Binary Focus:** `himax_mmi.ko` + `mtk_charger_framework.ko`  

---

## 1. The USB Connection Pathway: Step-by-Step Flow

The user observed that the touchscreen freezes significantly less often when connected to a PC, and connecting USB frequently un-freezes a stuck touchscreen. Here is the reconstructed software and hardware flow:

```
[Physical USB Cable Inserted / Removed]
   │
   ▼
[MediaTek MT6368 PMIC / Type-C Controller]
   │  - Detects CC pin resistance and VBUS voltage
   │  - Generates power supply change interrupt
   ▼
[mtk_charger_framework.ko]
   │  - Reads charger type (SDP = PC USB, DCP = Wall Charger, CDP = High-Power USB)
   │  - Sets internal power delivery limits
   │  - Writes plug state to exported symbol:
   │      str w0, [tp_usb_plug_status]   (1 = Connected, 0 = Disconnected)
   ▼
[himax_mmi.ko - himax_cable_detect_func()]
   │  - Compares tp_usb_plug_status with cached USB_detect_flag
   │  - If state changed (or force_renew == true):
   │      USB_detect_flag = new_state
   │      Calls: g_core_fp.fp_usb_detect_set(new_state)
   ▼
[himax_mcu_usb_detect_set()]
   │  - Formats 4-byte command packet
   │  - Writes to controller firmware AHB address: 0x10007F38
   │  - Reads back up to 5 times to verify controller ACK
   ▼
[HX83102J Controller Firmware]
   │  - Switches capacitive noise filtering algorithm
   │  - Re-evaluates baseline mutual-capacitance (soft recalibration)
   │  - Clears stale noise suppression and palm rejection states!
   ▼
[Touch Screen Un-Freezes and Resumes Finger Reporting]
```

---

## 2. Why Does USB Connection Prevent or Clear Freezes?

### Reason 1: The Earth Ground Reference (Electrical Stabilization)
- **The Floating Ground Problem:** When holding a tablet on battery power, the device's electrical ground is floating relative to earth ground. Human capacitance is measured between the finger (connected to body ground) and the sensor electrodes (connected to floating tablet ground). High ambient electrical noise or dry skin can compress the signal-to-noise ratio (SNR) below the detection threshold.
- **The PC USB Ground:** A PC's USB shield is connected directly to the building's mains earth ground via the PC power supply. Connecting the tablet to a PC couples the tablet's ground plane to earth ground. This **dramatically increases the effective capacitance of a human finger tap ($\Delta C$)**, making light touches unmistakable to the AFE!

### Reason 2: The Command Resend Side Effect (Firmware Recalibration)
- As shown in the flow chart, every time the USB plug status transitions from 0 to 1, the host driver sends an explicit write to `0x10007F38` (`fw_usb_detect_addr`).
- Inside the controller's MCU, processing this command triggers a **re-initialization of the touch tracking baseline**. If the controller was trapped in an erroneous palm-rejection or pen-priority state with `finger_num = 0`, the USB command forces the firmware to re-scan all mutual-capacitance channels, restoring finger reporting!

---

## 3. Why Forcing "Always USB Connected" is the Wrong Fix

One might be tempted to hardcode `tp_usb_plug_status = 1` permanently. Our analysis reveals why this is technically flawed:
1. **Higher Noise-Filter Latency:** In USB mode, the controller firmware expects 50Hz/60Hz mains charger ripple. It engages aggressive digital notch filters and multi-frame averaging to suppress charger spikes. On clean battery power, this causes **unnecessary input latency and sluggish response**.
2. **Missing the Dynamic Reset Trigger:** The beneficial un-freezing effect comes from the **state transition** ($0 \rightarrow 1$), which causes the controller to re-evaluate its baseline. If permanently set to 1, no further state transitions occur, losing the recovery trigger when a freeze happens!

---

## 4. Suspend / Resume Sequencing

### 4.1 Suspend Sequence (`himax_chip_common_suspend`)
1. Notifier receives `MTK_DISP_EARLY_BLANK`.
2. Driver sets `ts->suspended = true`.
3. Calls `himax_report_all_leave_event(ts)` to release fingers.
4. Calls `hx83102j_sense_off()`: sends sleep command `0x9000005C` to controller.
5. Disables IRQ via `disable_irq_nosync()`.
6. Turns off display backlight and touch regulators.

### 4.2 Resume Sequence (`himax_chip_common_resume`)
1. Notifier receives `MTK_DISP_BLANK` (unblank).
2. Restores power rails and asserts hardware reset GPIO (`himax_rst_gpio_set`).
3. Executes zero-flash SRAM reload (`hx83102j_reload_to_active`).
4. Re-enables interrupt via `enable_irq()`.
5. Calls `himax_mcu_resend_cmd_func()`:
   - Resends USB charger mode.
   - Resends notch/edge filter parameters.
   - **Now via [P7]:** Sends `himax_mcu_set_HSEN_enable(1)` to ensure high-sensitivity is restored!
6. Sets `ts->suspended = false`.

This sequence explains why cycling the power button always cures a frozen touchscreen: it executes a full hardware reset, reloads clean firmware from flash, and re-initializes all controller registers from scratch.
