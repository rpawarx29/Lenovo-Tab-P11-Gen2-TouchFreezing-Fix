# S231018 Verification Report

- **Device Under Test:** Lenovo Tab P11 Gen 2 (`TB350XU`, Serial `HVA5R4L6`)
- **ROM Build:** `TB350XU_USER_S231018_2601050930_MP_ROW` (`ro.build.display.id = TB350XU_S231018_260105_ROW`)
- **Kernel Vermagic:** `5.10.233-android12-9-g9568a331d924 SMP preempt mod_unload modversions aarch64`
- **Touch Hardware:** Himax `HX83102J` | Panel `Huaqin_BOE` | Project `Tulip_AX6298` | `FW_VER = 0xC402` | Driver `2.1.0.2_Tulip_01`
- **Root Stack Tested:** APatch (`11282` / `0.13.9`) + `zygisksu` + `playintegrityfix` + `magic_mount` + `zygisk-assistant` + `zygisk_shamiko` + `tb350xu_touch_fix` (`v2.0-S231018`)

---

## 1. Hardware & Boot Environment Telemetry

| Telemetry Item | Observed Live Value |
| :--- | :--- |
| Active Slot / Bootloader | `_a` / `unlocked` (`androidboot.verifiedbootstate = orange`, `veritymode = enforcing`) |
| SPI & IRQ Allocation | `IRQ 72` (`GICv3 223 Level 1100a000.spi0`), `IRQ 206` (`mtk-eint 54 Edge himax_tp`) |
| Interrupt Trigger (`/proc/android_touch/debug`) | `IC Interrupt type is edge trigger.` / `Driver register Interrupt : EDGE TIRGGER` (`0x2002`) |
| Kernel Input Devices | `himax-touchscreen` (`event6`), `himax-stylus` (`event7`) |
| MT6789 Verified OPP Ranges | `policy0`: `500000..2000000` (24 steps) \| `policy6`: `725000..2200000` (16 steps) \| `13000000.mali`: `390000000..1100000000` (45 steps) |

### AVB Behavior on Unlocked Bootloader
Stock `vbmeta.img` contains an RSA-signed `HashDescriptor` for `vendor_boot`. Because the tablet bootloader is `unlocked` (`orange` state), MTK LK permits booting modified `vendor_boot` without requiring `--disable-verity --disable-verification` on `vbmeta`, keeping `androidboot.veritymode = enforcing` intact. `tools/patch_vendor_boot.py` still recomputes `vendor_boot`'s internal AVB payload descriptor and footer cleanly.

---

## 2. Built Artifact Integrity (`SHA256SUMS.txt`)

| File | Bytes | Verified SHA-256 |
| :--- | :---: | :--- |
| Stock `TB350XU_USER_S231018.../vendor_boot.img` | `67,108,864` | `0c06ebe186f39b1ec64398fc8e3bad74b0c2a7c4fae8134822f7adcc12c0a7c4` |
| Stock `lib/modules/himax_mmi.ko` | `591,808` | `1085f0a9b0b12dabb6a1c658982798b1bc152dddc44abae055378a7ff6ed8b29` |
| Patched `vendor_boot_TB350XU_S231018_touch_fix.img` | `67,108,864` | `f570272f25a1c2354b60469cda6e163c56c149f5f84f2ebf0cddc21565c77402` |
| Patched `himax_mmi_s231018_patched.ko` | `591,960` | `a7efe8622dc9c9461ee00e1ef6b0ddb7a367e6e779b423e60b1173d6dc64fda5` |

### `.text` & `.rela.text.himax_report_data_init` Summary
- `.text` expanded by `+156` bytes (`0x249C8` -> `0x24A64`).
- `.rela.text.himax_report_data_init` (section index 24) retained all `11,536` original entries untouched and appended 1 `R_AARCH64_CALL26` (`283`) relocation at `0x24A44` targeting symbol `1496` (`input_mt_report_slot_state`).
- Zero stock relocations overlapped any patched site (`assert off not in existing_rela_offs`); all non-`.text`/`.rela.text` sections and DTB bytes remained unchanged.

| Hook | Callsite(s) | Original Code | Hook Logic | Offset Range |
| :---: | :--- | :--- | :--- | :--- |
| **H1 `[P1+P2]`** | `0x11938`, `0x119C8` | `ldrb w8, [x8, #0x9c]`, `mov w0, #1` | Captures `(w0 == 0)` to `[sp]`; returns `[sp]` via `ldr w0, [sp]` | `0x249C8..0x249DC` |
| **H2 `[P3]`** | `0x23650` | `mov w2, w19` | Verifies `[x29, #-0x44] == w23`, else jumps to `-EIO` (`0x23744`) + mutex unlock | `0x249DC..0x249F0` |
| **H3 `[P4]`** | `0x0484C` | `mov w1, #1` | Calls `himax_report_all_leave_event(x19)` (`0x054E8`) before read-fail reset | `0x249F0..0x24A00` |
| **H4 `[P5]`** | `0x04AEC` | `blr x21` | Calls `himax_report_all_leave_event(x19)` (`0x054E8`) before excp reset | `0x24A00..0x24A10` |
| **`[P6]`** | `0x04BC0` | `add x0, x8, #0x3c` | Direct instruction update to `add x0, x8, #0x4c` (`00310191`) | Inline |
| **H5 `[P7]`** | `0x1A514` | `ldr x9, [x19, #0x4c0]` | Saves `x8/x30`; if active (`[x19,#1]==0`), calls `himax_mcu_set_HSEN_enable(1)` | `0x24A10..0x24A34` |
| **H6 `[P10]`** | `0x03610`, `0x036AC` | `ldr x0, [x20, #0x170]`, `b #0x3584` | Emits `input_mt_report_slot_state(dev,0,w24)` early; loop tail -> `0x03594` | `0x24A34..0x24A54` |
| **H7 `[P9]`** | `0x037B8` | `cbz w8, #0x3960` | Checks `w8 \| [x20, #0x90]` (`pre_finger_mask`) before skipping release | `0x24A54..0x24A64` |

*(P8 Level-Low IRQ override intentionally omitted; `0x23C8C..0x23CA0` preserves native `0x2002` Edge IRQ.)*

---

## 3. Live On-Device Verification Results (Post-Flash Slot `_a`)

1. **Partition & Module Load Verification:**
   - Readback SHA-256 of `/dev/block/by-name/vendor_boot_a` verified `f570272f25a1c2354b60469cda6e163c56c149f5f84f2ebf0cddc21565c77402`.
   - `lsmod` verified `himax_mmi` (`294912` bytes) and dependent panel/hall/power modules loaded cleanly.
2. **HSEN Active on Boot & After Screen Suspend/Resume:**
   ```text
   echo "register,r:x10007F14" > /proc/android_touch/debug
   cat /proc/android_touch/debug
   -> command: 10,00,7F,14
   -> 0x5A 0xA5 0x5A 0xA5 ...
   ```
   Verified both after cold boot and after `input keyevent 223` (Dozing) -> `input keyevent 224` (Awake).
3. **Clean Kernel Log (`dmesg`):**
   - Zero `[HXTP][ERROR]` spam after removing `/proc/game_mode` polling from the 2s awake loop.
   - Single initialization confirmation on wake: `[HXTP] himax_mcu_set_game_mode: tmp_data[0]=90, mode=0, retry_cnt=0`.
4. **Sleep/Wake Daemon & PowerHAL Resilience:**
   - Screen off (`lcd-backlight/brightness = 0`): `policy0/scaling_min_freq = 500000`, `policy6/scaling_min_freq = 725000`, `gpu_bottom_freq = 390000`, `thrm_enable = 1`, `top-app/cpu.uclamp.latency_sensitive = 0`.
   - Screen on (`lcd-backlight/brightness = 33`): `sugov_ext/down_rate_limit_us = 30000`, `gpu_bottom_freq = 648000`, `fpsgo_enable = 0`, `thrm_enable = 0`, `top-app/cpu.uclamp.latency_sensitive = 1`.
5. **Display, Haptics & Typing Outcome:**
   - `ro.surface_flinger.set_touch_timer_ms = 2000`, `ro.surface_flinger.set_idle_timer_ms = 1000`, `peak_refresh_rate = 120.0`, `min_refresh_rate = null` (Settings toggle unlocked), `/sys/class/leds/vibrator` intact.
   - Zero `InputReader: Received unexpected event (0x35/0x36)` errors and touch/typing drops resolved in live usage.
