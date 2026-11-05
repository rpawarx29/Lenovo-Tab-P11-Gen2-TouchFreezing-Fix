# ALL VERIFIED BUGS & DEFECTS: HIMAX HX83102J SUBSYSTEM
**Target Device:** Lenovo Tab P11 Gen 2 (TB350XU)  
**Binary Analyzed:** `himax_mmi.ko` (`5.10.136-android12-9-gf16efe7b9174`)  
**Status:** Independently Verified & Classified via Reverse-Engineering  

---

## Bug Classification Summary

| ID | Defect Description | Location | Classification | Implemented Action |
|---|---|---|---|---|
| **BUG-01** | Unconditional Success Return in `hx83102j_read_event_stack` | `.text + 0x11A44`, `0x11AD8` | **Confirmed Critical Defect** | Corrected via [P1] & [P2] |
| **BUG-02** | Unchecked Transfer Length in `himax_bus_read` | `.text + 0x2376C` | **Confirmed Critical Defect** | Corrected via [P3] |
| **BUG-03** | Missing Contact Release Prior to Reset / Recovery | `.text + 0x04920`, `0x04BCC` | **Confirmed Defect** | Corrected via [P4] & [P5] |
| **BUG-04** | Prevent-Notch Command Buffer Pointer Offset Mismatch | `.text + 0x04CC0` | **Confirmed Defect** | Corrected via [P6] |
| **BUG-05** | Dormant High-Sensitivity Mode Never Activated | `.text + 0x1A61C` | **Confirmed Design Omission** | Corrected via [P7] |
| **BUG-06** | Stylus-Priority / Palm Rejection Finger Suppression | Packet Parser & Controller FW | **Confirmed Functional Defect** | Analyzed & Mitigated |
| **BUG-07** | Charger Framework Global Symbol Width Mismatch | `tp_usb_plug_status` | **Verified Benign Mismatch** | Verified Safe (No Overwrite) |
| **BUG-08** | Multi-Packet SPI Mutex Granularity Gap | `himax_bus_read` / `himax_ts_work` | **Architectural Weakness** | Documented & Preserved |

---

## Detailed Bug Analyses

### BUG-01: Unconditional Success Return in `hx83102j_read_event_stack`
- **Location:** `.text + 0x11A44` and `.text + 0x11AD8`
- **Root Cause:**
  In stock `himax_mmi.original.ko`, `hx83102j_read_event_stack()` calls `himax_bus_read()`, but completely ignores its return status in register `W0`. At function return (`.text + 0x11AD8`), the instruction is hardcoded:
  ```arm64
  0x011ad8: mov w0, #1    ; Returns TRUE unconditionally
  0x011adc: add sp, sp, #0x60
  0x011ae0: autiasp
  0x011ae4: ret
  ```
- **Consequence:**
  When an SPI bus read fails (e.g. SPI controller timeout, electrical noise, bus contention), `hx83102j_read_event_stack` returns `true`. The caller `himax_ts_work()` assumes valid data was received and attempts to parse stale or zeroed stack memory. The driver's intended read-failure recovery logic (`himax_mcu_ic_excp_recovery`) is completely bypassed!
- **Patch Resolution:**
  - `[P1]` redirects `.text + 0x11A44` to appended Hook 1, converting `W0` (bus read result: 0=success, negative=error) to boolean (`cset w0, eq`) and saving it on the stack.
  - `[P2]` replaces `mov w0, #1` at `0x11AD8` with `ldr w0, [sp]`, returning actual transfer status.

---

### BUG-02: Unchecked Transfer Length in `himax_bus_read`
- **Location:** `.text + 0x2376C`
- **Root Cause:**
  `himax_bus_read()` invokes `spi_sync()`. On completion, it inspects whether `spi_sync()` returned zero (success), but does not verify whether `spi_message.actual_length` equals the requested wire length (`requested_len + HIMAX_BUS_R_HLEN`).
- **Consequence:**
  If the SPI controller experiences an early FIFO termination or incomplete DMA burst, `spi_sync` may report status 0 while returning fewer bytes than requested. The driver copies incomplete data from the SPI RX buffer into the packet parser, triggering coordinate corruption or false release events.
- **Patch Resolution:**
  - `[P3]` redirects `.text + 0x2376C` to appended Hook 2. Compares `actual_length` from the stack frame against `requested_length` (`cmp w8, w23`). If mismatched, branches directly to error return path (`-EIO`) without copying corrupted data.

---

### BUG-03: Missing Contact Release Prior to Reset / Recovery
- **Location:** `.text + 0x04920` (read-failure reset) and `.text + 0x04BCC` (exception recovery)
- **Root Cause:**
  When a controller error or exception occurs, active touch contacts remain registered as "down" in the Linux kernel input subsystem. In stock binary:
  1. In the read-failure path (`0x04920`), `himax_report_all_leave_event()` is **never called at all**.
  2. In the exception recovery path (`0x04BCC`), `himax_report_all_leave_event()` was called only **after** full hardware reset, SRAM reload, and reinitialization completed.
- **Consequence:**
  If a hardware or communication freeze occurs while one or more fingers are touching the screen, Android's `InputReader` retains the active finger slots indefinitely ("ghost touch freeze"). Android continues suppressing subsequent taps because it believes the first contact is still held down.
- **Patch Resolution:**
  - `[P4]` inserts a call to `himax_report_all_leave_event(ts)` (`.text + 0x55E8`) immediately prior to the read-failure reset.
  - `[P5]` inserts a call to `himax_report_all_leave_event(ts)` immediately prior to triggering exception recovery.

---

### BUG-04: Prevent-Notch Command Buffer Pointer Offset Mismatch
- **Location:** `.text + 0x04CC0`
- **Root Cause:**
  In exception recovery, the driver restores notch filtering parameters by calling `g_core_fp.fp_set_prevent_notch(ts->cmd_param_buf)`.
  In stock disassembly:
  ```arm64
  0x004cc0: add x0, x8, #0x3c    ; ts + 0x3c (FIRST INT32 FIELD)
  ```
  However, `ts->cmd_param_buf` is located at offset `0x4C` (`ts + 0x4C`). Offset `0x3C` points to `ts->use_irq` / command header int32.
- **Consequence:**
  The controller receives 4 bytes of unrelated driver internal state instead of the packed edge/notch filter parameters, temporarily setting incorrect notch boundaries upon recovery.
- **Patch Resolution:**
  - `[P6]` alters instruction `0x004CC0` from `add x0, x8, #0x3c` (`00f10091`) to `add x0, x8, #0x4c` (`00310191`).

---

### BUG-05: Dormant High-Sensitivity Mode Never Activated
- **Location:** `.text + 0x14768` (`himax_mcu_set_HSEN_enable`)
- **Root Cause:**
  The controller supports physical high-sensitivity mode via AHB register `0x10007F14`. The driver contains a fully functional setter `himax_mcu_set_HSEN_enable()`, but:
  1. It is never registered or called during standard boot or resume.
  2. The `/proc/android_touch/HSEN` node is omitted from `himax_touch_proc_init` in this Lenovo production build.
- **Consequence:**
  The touchscreen operates strictly in standard sensitivity mode. Light touches or screen-protector contacts frequently fail to cross the controller's capacitive detection threshold.
- **Patch Resolution:**
  - `[P7]` intercepts the USB settings resend sequence (`himax_mcu_resend_cmd_func` at `.text + 0x1A61C`), checks that the device is active (`!ts->suspended`), and calls `himax_mcu_set_HSEN_enable(1)` to activate physical sensitivity enhancement on boot, resume, and recovery.

---

### BUG-06: Stylus-Priority / Palm Rejection Finger Suppression
- **Location:** Controller firmware & packet processing logic
- **Root Cause:**
  The strongest observed real-world symptom is: **finger touches freeze while active stylus continues working**.
  Investigation reveals:
  1. Both finger and stylus data arrive over the exact same SPI bus in the same packet buffer (`hx_touch_data`).
  2. If the stylus continues drawing, **SPI communication, IRQs, power rails, and the SPI bus mutex are 100% operational**.
  3. When an active stylus is detected (`stylus_num > 0`), the Himax firmware enters stylus-priority mode and suppresses mutual-capacitance finger detection to prevent palm interference.
  4. If the stylus tip un-press or leave packet is dropped, or if baseline mutual-capacitance drifts while in proximity mode, the controller firmware remains stuck in palm-rejection suppression (`finger_num = 0`).
- **Mitigation:**
  Ensured through [P4] and [P5] that when recovery or leave events are triggered, finger slots are cleared. Provided diagnostic monitoring via `MONITOR_TOUCH_RECOVERY.cmd` to observe `finger_num` vs `stylus_num` in real time.

---

### BUG-07: Charger Framework Global Symbol Width Mismatch
- **Location:** Exported symbol `tp_usb_plug_status`
- **Analysis:**
  `mtk_charger_framework.ko` writes a 32-bit integer (`str w0, [x8]`) to `tp_usb_plug_status`.
  In `himax_mmi.ko`, `tp_usb_plug_status` is declared as a 1-byte unsigned char (`.bss + 0x04`).
- **Finding:**
  In the BSS section layout of `himax_mmi.ko`, `tp_usb_plug_status` is at offset `0x04`. The next symbol, `private_ts`, begins at offset `0x08`. Bytes `0x05, 0x06, 0x07` are natural padding for 64-bit alignment. Therefore, the 32-bit store does **not** corrupt `private_ts` or any adjacent object in this specific compiled binary. It is benign on this kernel build and excluded from binary modification.
