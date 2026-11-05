# COMPLETE DRIVER FUNCTION MAP: `himax_mmi.ko`
**Target Device:** Lenovo Tab P11 Gen 2 (TB350XU)  
**Binary Base:** Stock `himax_mmi.original.ko` (SHA-256: `e9dc21ba90f42c0a136140c6e8e2838608146d6e20323c21ff237650349a1827`)  
**Mapping Method:** Capstone ARM64 symbol resolution + disassembly xref analysis  

---

## 1. Overview of Driver Architecture

The Himax touchscreen subsystem consists of five functional layers:
1. **Hardware Bus Transport Layer (`himax_bus_*`):** SPI communication over MediaTek SPI controller.
2. **Controller Core MCU Layer (`hx83102j_*`, `himax_mcu_*`):** Controller initialization, zero-flash SRAM reload, register reads/writes, firmware handshake.
3. **Interrupt & Event Stack Layer (`himax_ts_thread`, `*_read_event_stack`):** Top/bottom half IRQ processing, SPI packet buffering.
4. **Input Subsystem Reporting Layer (`himax_report_data`, `himax_parse_report_points`):** Parsing multitouch packets, finger slot tracking, active stylus coordinates, pressure, and button reporting.
5. **System Integration & Power Management Layer (`himax_common_*`, `himax_disp_notifier_*`):** Suspend, resume, charger status notifications, hall sensor interaction.

---

## 2. Key Driver Functions Reference

### 2.1 Hardware Transport & Bus I/O

#### `himax_bus_read`
- **Address:** `.text + 0x23648` (Size: 396 bytes)
- **Signature:** `int himax_bus_read(uint8_t command, uint8_t *data, uint32_t length, uint8_t toRetry)`
- **Role:** Primary SPI read function. Formats SPI transmit buffer (command byte + dummy bytes), executes `spi_sync()` under mutex lock (`private_ts + 0x210`), and copies response data to destination buffer.
- **Callers:** `hx83102j_read_event_stack`, `himax_mcu_register_read`, `himax_mcu_read_sram_0f`.
- **Callees:** `mutex_lock`, `spi_sync`, `memcpy`, `mutex_unlock`, `printk`.
- **Known Defect:** In stock binary, failed or short reads did not verify that `actual_length == requested_length + HIMAX_BUS_R_HLEN`, allowing partial garbage packets into parser. Patched by [P3].

#### `himax_bus_write`
- **Address:** `.text + 0x23484` (Size: 452 bytes)
- **Signature:** `int himax_bus_write(uint8_t command, uint8_t *data, uint32_t length, uint8_t toRetry)`
- **Role:** Primary SPI write function. Prepares command header, acquires bus mutex, calls `spi_sync()`.
- **Callers:** `himax_mcu_register_write`, `himax_mcu_set_HSEN_enable`, `himax_mcu_usb_detect_set`, `himax_mcu_system_reset`.
- **Callees:** `mutex_lock`, `spi_sync`, `mutex_unlock`.

---

### 2.2 Controller Core MCU & Initialization

#### `hx83102j_chip_init`
- **Address:** `.text + 0x11360` (Size: 176 bytes)
- **Signature:** `int hx83102j_chip_init(void)`
- **Role:** Assigns IC-specific function pointers to global `ic_data` and `g_core_fp` structures. Sets protocol version to `HX_PROTOCOL_B_3PA`.
- **Callers:** `hx_ic_register` (`.text + 0x5710`).
- **Callees:** Assigns `hx83102j_read_event_stack`, `hx83102j_sense_on`, `hx83102j_sense_off`, `hx83102j_reload_to_active`.

#### `hx83102j_read_event_stack`
- **Address:** `.text + 0x119DC` (Size: 272 bytes)
- **Signature:** `bool hx83102j_read_event_stack(uint8_t *buf, uint8_t length)`
- **Role:** Reads touch event packet stack from controller. In stock binary, ignores return value of `himax_bus_read` and unconditionally returns `true` (`mov w0, #1` at `0x11AD8`). Patched by [P1] and [P2].
- **Callers:** `himax_ts_work` (`.text + 0x422C`).
- **Callees:** `himax_bus_read`, `ktime_get_ts64` (for debug latency calculations).

#### `himax_mcu_set_HSEN_enable`
- **Address:** `.text + 0x14768` (Size: 444 bytes)
- **Signature:** `void himax_mcu_set_HSEN_enable(uint8_t enable, bool suspended)`
- **Role:** Configures controller high-sensitivity mode. If `enable == 1`, writes `0xA55AA55A` to `0x10007F14`; if `enable == 0`, writes `0x00000000`. Reads back up to 5 times to verify controller acceptance.
- **Callers:** Patched [P7] hook in `himax_mcu_resend_cmd_func`.
- **Callees:** `himax_bus_write`, `himax_bus_read`, `msleep`.

#### `hx83102j_reload_to_active`
- **Address:** `.text + 0x11B10` (Size: 392 bytes)
- **Signature:** `int hx83102j_reload_to_active(void)`
- **Role:** Reloads SRAM zero-flash configuration from flash image during resume or hardware reset.
- **Callers:** `himax_chip_common_resume`, exception recovery handler.
- **Callees:** `himax_mcu_clean_sram_0f`, `himax_mcu_write_sram_0f`, `himax_sram_write_crc_check`.

---

### 2.3 Interrupt Handling & Coordinate Parsing

#### `himax_ts_thread`
- **Address:** `.text + 0x23BC4` (Size: 44 bytes)
- **Signature:** `irqreturn_t himax_ts_thread(int irq, void *ptr)`
- **Role:** Kernel thread spawned by `request_threaded_irq`. Calls `himax_ts_work()`.
- **Callers:** Linux IRQ core.
- **Callees:** `himax_ts_work`.

#### `himax_ts_work`
- **Address:** `.text + 0x422C` (Size: 1,080 bytes)
- **Signature:** `void himax_ts_work(struct himax_ts_data *ts)`
- **Role:** Main state loop. Calls `hx83102j_read_event_stack()`, validates packet header, checks exception flags (`hx_EB_event_flag`, `hx_EC_event_flag`, `hx_ED_event_flag`), calls coordinate parser, and triggers recovery if read fails.
- **Callers:** `himax_ts_thread`.
- **Callees:** `hx83102j_read_event_stack`, `himax_parse_report_points`, `himax_report_data`, `himax_cable_detect_func`, `himax_mcu_ic_excp_recovery`.

#### `himax_parse_report_points`
- **Address:** `.text + 0x2D34` (Size: 2,176 bytes)
- **Signature:** `int himax_parse_report_points(struct himax_ts_data *ts, uint8_t *buf)`
- **Role:** Decodes raw byte payload into individual finger contacts and stylus records.
  - Byte 0-3: Packet header and checksum.
  - Byte 4: `finger_num` (number of finger contacts detected).
  - Byte 5: `stylus_num` (number of active pens detected).
  - Slot bytes: Coordinates `X` (16-bit), `Y` (16-bit), `W` (width/area), `Z` (pressure).
- **Callers:** `himax_ts_work`.
- **Callees:** Computes running checksum, updates `ts->last_slot`.

#### `himax_report_data`
- **Address:** `.text + 0x35B4` (Size: 2,740 bytes)
- **Signature:** `void himax_report_data(struct himax_ts_data *ts)`
- **Role:** Dispatches parsed points to Linux input subsystem:
  - For fingers: `input_mt_slot()`, `input_mt_report_slot_state(MT_TOOL_FINGER)`, `input_report_abs(ABS_MT_POSITION_X/Y)`, `input_report_abs(ABS_MT_PRESSURE)`.
  - For stylus: `input_report_abs(ABS_X/Y)`, `input_report_abs(ABS_PRESSURE)`, `input_report_key(BTN_TOUCH)`, `input_report_key(BTN_STYLUS/STYLUS2)`.
  - `input_sync(ts->input_dev)`.
- **Callers:** `himax_ts_work`.
- **Callees:** Linux input subsystem APIs.

---

### 2.4 Recovery & Reset Subsystem

#### `himax_report_all_leave_event`
- **Address:** `.text + 0x55E8` (Size: 208 bytes)
- **Signature:** `void himax_report_all_leave_event(struct himax_ts_data *ts)`
- **Role:** Iterates over all multitouch slots (`0` to `ts->max_touch_num - 1`), reports `input_mt_report_slot_state(slot, false)` for any active finger, and issues `input_sync()`. Ensures Android does not leave stuck touch down events.
- **Callers:** `himax_common_suspend`, Patched [P4] hook (before read-failure reset), Patched [P5] hook (before exception recovery).
- **Callees:** `input_mt_slot`, `input_mt_report_slot_state`, `input_sync`.

#### `himax_mcu_ic_excp_recovery`
- **Address:** `.text + 0x4800` (Size: 1,824 bytes)
- **Signature:** `void himax_mcu_ic_excp_recovery(void)`
- **Role:** Handles controller exception flags (e.g. controller firmware crash or watchdog bite). Triggers pin reset or software reset, reloads SRAM zero-flash configuration, and calls `himax_mcu_resend_cmd_func()`.
- **Callers:** `himax_ts_work` on exception flag match.
- **Callees:** `himax_mcu_system_reset`, `himax_rst_gpio_set`, `himax_mcu_resend_cmd_func`, `himax_report_all_leave_event`.

---

### 2.5 Power & External Notifications

#### `himax_cable_detect_func`
- **Address:** `.text + 0x2C6C` (Size: 196 bytes)
- **Signature:** `void himax_cable_detect_func(bool force_renew)`
- **Role:** Reads exported global `tp_usb_plug_status`. If changed or `force_renew == true`, sends charger noise mitigation parameters to controller at `0x10007F38`.
- **Callers:** `himax_ts_work`, `himax_mcu_resend_cmd_func`.
- **Callees:** `himax_mcu_usb_detect_set`.

#### `himax_mcu_resend_cmd_func`
- **Address:** `.text + 0x1A5C0` (Size: 188 bytes)
- **Signature:** `void himax_mcu_resend_cmd_func(struct himax_ts_data *ts, bool suspended)`
- **Role:** Re-applies active configuration settings (USB charger mode, notch filtering, and via [P7] high-sensitivity mode) following screen wake or recovery reset.
- **Callers:** `himax_chip_common_resume`, `himax_mcu_ic_excp_recovery`.
- **Callees:** `himax_cable_detect_func`, `himax_mcu_set_HSEN_enable` (via [P7]).

#### `himax_disp_notifier_callback`
- **Address:** `.text + 0x23FD4` (Size: 332 bytes)
- **Signature:** `int himax_disp_notifier_callback(struct notifier_block *nb, unsigned long val, void *v)`
- **Role:** Listens for MediaTek DRM panel state changes (`MTK_DISP_EARLY_BLANK`, `MTK_DISP_BLANK`). Coordinates touch sleep and wake.
- **Callers:** MediaTek Display Subsystem notifier chain.
- **Callees:** `himax_chip_common_suspend`, `himax_chip_common_resume`.
