# S231018 ULTIMATE TOUCH & PERFORMANCE VERIFICATION REPORT

- **Device Under Test:** Lenovo Tab P11 Gen 2 (`TB350XU`, Serial `HVA5R4L6`)
- **ROM Build:** `TB350XU_USER_S231018_2601050930_MP_ROW` (`ro.build.display.id = TB350XU_S231018_260105_ROW`)
- **Kernel:** `5.10.233-android12-9-g9568a331d924 SMP preempt mod_unload modversions aarch64`
- **Touch Hardware:** Himax `HX83102J` | Panel `Huaqin_BOE` | Project `Tulip_AX6298` | `FW_VER = 0xC402` | Driver `2.1.0.2_Tulip_01`
- **Root & Stealth Stack Tested:** APatch (`11282` / `0.13.9`) + `zygisksu` + `playintegrityfix` + `magic_mount` + `zygisk-assistant` + `zygisk_shamiko` + `tb350xu_master_touch_fix (v6.1-Ultimate)`

---

## 1. Verified Hardware & Boot Environment

| Telemetry Item | Verified Observed Value |
| :--- | :--- |
| Active Slot / Boot State | `_a` / `unlocked` (`androidboot.verifiedbootstate = orange`, `veritymode = enforcing`) |
| SPI & Interrupt Lines | `IRQ 72` (`GICv3 223 Level 1100a000.spi0`), `IRQ 206` (`mtk-eint 54 Edge himax_tp`) |
| Interrupt Mode (`/proc/android_touch/debug`) | `IC Interrupt type is edge trigger.` / `Driver register Interrupt : EDGE TIRGGER` (`0x2002`) |
| Input Devices | `himax-touchscreen` (`event6`), `himax-stylus` (`event7`) |
| Verified MT6789 OPP Frequencies | `policy0`: `500000..2000000` (24 steps) \| `policy6`: `725000..2200000` (16 steps) \| `13000000.mali`: `390000000..1100000000` (45 steps) |

### AVB & Boot Behavior
`vbmeta.img` contains an RSA-signed `HashDescriptor` for `vendor_boot`. Because the device bootloader is `unlocked` (`androidboot.verifiedbootstate = orange`), MTK LK skips halting on `vendor_boot` AVB hash mismatch while keeping `androidboot.veritymode = enforcing` intact — no `--disable-verity` or `vbmeta` blanking is required, preserving a cleaner environment for Play Integrity modules. Internal `vendor_boot` footer & payload `HashDescriptor` are still recomputed cleanly by `tools/build_s231018_ultimate_touch.py`.

---

## 2. Binary Image & ELF Relocation Verification

| Artifact | Size (Bytes) | Verified SHA-256 |
| :--- | :---: | :--- |
| Stock `TB350XU_USER_S231018.../vendor_boot.img` | `67,108,864` | `0c06ebe186f39b1ec64398fc8e3bad74b0c2a7c4fae8134822f7adcc12c0a7c4` |
| Stock `lib/modules/himax_mmi.ko` | `591,808` | `1085f0a9b0b12dabb6a1c658982798b1bc152dddc44abae055378a7ff6ed8b29` |
| Patched `vendor_boot_TB350XU_S231018_ULTIMATE_TOUCH.img` | `67,108,864` | `f570272f25a1c2354b60469cda6e163c56c149f5f84f2ebf0cddc21565c77402` |
| Patched `himax_mmi_s231018_ultimate.ko` | `591,960` | `a7efe8622dc9c9461ee00e1ef6b0ddb7a367e6e779b423e60b1173d6dc64fda5` |
| `releases/TB350XU_Master_Touch_and_Performance_Fix.zip` | `8,089` | `8596ec6f390706df6f3802a9bf229db0928af63a206edc344d6f63e4a9c541d3` |

### Exact `.text` & `.rela` Changes in `himax_mmi.ko`
- `.text` grew by `+156` bytes (`0x249C8` -> `0x24A64`).
- `.rela.text.himax_report_data_init` (section index 24) preserved all `11,536` original relocations untouched and appended 1 `R_AARCH64_CALL26` (`283`) entry at `0x24A44` pointing to symbol `1496` (`input_mt_report_slot_state`).
- All other sections (`__ksymtab`, `__versions`, `.modinfo`, `.rodata`, `.data`, `.bss`, `.symtab`, `.strtab`) and DTB bytes remained identical to stock (recalculated section offsets & alignments only).

| Hook | Callsite(s) | Original Instruction(s) | Patched Action | Trampoline Range |
| :---: | :--- | :--- | :--- | :--- |
| **H1 `[P1+P2]`** | `0x11938`, `0x119C8` (`hx83102j_read_event_stack`) | `ldrb w8, [x8, #0x9c]`, `mov w0, #1` | Stores `(w0==0)` to `[sp]`, returns via `ldr w0, [sp]` | `0x249C8..0x249DC` |
| **H2 `[P3]`** | `0x23650` (`himax_bus_read`) | `mov w2, w19` | Checks `[x29, #-0x44] == w23`, else `-EIO` (`0x23744`) | `0x249DC..0x249F0` |
| **H3 `[P4]`** | `0x0484C` (`himax_ts_work`) | `mov w1, #1` | `himax_report_all_leave_event(x19)` (`0x054E8`) before reset | `0x249F0..0x24A00` |
| **H4 `[P5]`** | `0x04AEC` (`himax_ts_work`) | `blr x21` | `himax_report_all_leave_event(x19)` (`0x054E8`) before excp reset | `0x24A00..0x24A10` |
| **`[P6]`** | `0x04BC0` (`himax_ts_work`) | `add x0, x8, #0x3c` | Direct patch to `add x0, x8, #0x4c` (`00310191`) | Inline |
| **H5 `[P7]`** | `0x1A514` (`himax_mcu_resend_cmd_func`) | `ldr x9, [x19, #0x4c0]` | Saves `x8/x30`; if `x19 != 0 && [x19,#1]==0`, calls `HSEN(1)` (`0x14658`) | `0x24A10..0x24A34` |
| **H6 `[P10]`** | `0x03610`, `0x036AC` (`himax_report_data`) | `ldr x0, [x20, #0x170]`, `b #0x3584` | Saves `x8/x30`, calls `input_mt_report_slot_state(dev,0,w24)`, tail -> `0x03594` | `0x24A34..0x24A54` |
| **H7 `[P9]`** | `0x037B8` (`himax_report_data`) | `cbz w8, #0x3960` | Checks `w8 \| [x20, #0x90]` (`pre_finger_mask`) before skip | `0x24A54..0x24A64` |

*(P8 Level-Low IRQ override intentionally excluded; `0x23C8C..0x23CA0` continues selecting native `0x2002` Edge IRQ.)*

---

## 3. On-Device Live Test Results (Post-Flash `_a`)

1. **Partition & Module Load Verification:**
   - `/dev/block/by-name/vendor_boot_a` readback SHA-256 verified identical to `f570272f25a1c2354b60469cda6e163c56c149f5f84f2ebf0cddc21565c77402`.
   - `lsmod` verified `himax_mmi` (`294912` bytes) and dependent MTK/panel modules (`panel_boe_hx83102j_vdo`, `panel_tianma_hx83102j_vdo`, `hall_mod`, `ktz8866`) loaded with zero errors.
2. **HSEN Hardware Register (`0x10007F14`) Verified Active Before & After Sleep:**
   ```text
   echo "register,r:x10007F14" > /proc/android_touch/debug
   cat /proc/android_touch/debug
   -> command: 10,00,7F,14
   -> 0x5A 0xA5 0x5A 0xA5 ...   (Stock baseline was 0x00 0x00 0x00 0x00)
   ```
   Verified both after initial cold boot and again after cycling `input keyevent 223` (Dozing) -> `input keyevent 224` (Awake).
3. **`dmesg` Cleanliness & `/proc/game_mode` Fix:**
   - Removing `/proc/game_mode` polling from the 2s loop eliminated `[HXTP][ERROR] mode not match, pls check!` completely.
   - `dmesg` logs one clean initialization message on resume: `[HXTP] himax_mcu_set_game_mode: tmp_data[0]=90, mode=0, retry_cnt=0`.
4. **Sleep/Wake Daemon & PowerHAL Resilience:**
   - Screen off (`lcd-backlight/brightness = 0`): `policy0/scaling_min_freq = 500000`, `policy6/scaling_min_freq = 725000`, `gpu_bottom_freq = 390000`, `thrm_enable = 1`, `top-app/cpu.uclamp.latency_sensitive = 0`.
   - Screen on (`lcd-backlight/brightness = 33`): `sugov_ext/down_rate_limit_us = 30000`, `gpu_bottom_freq = 648000`, `fpsgo_enable = 0`, `thrm_enable = 0`, `top-app/cpu.uclamp.latency_sensitive = 1`, `policy0/scaling_min_freq >= 1200000`.
5. **Display, Haptics & InputReader State:**
   - `ro.surface_flinger.set_touch_timer_ms = 2000`, `ro.surface_flinger.set_idle_timer_ms = 1000`, `peak_refresh_rate = 120.0`, `min_refresh_rate = null` (native Settings toggle intact), `/sys/class/leds/vibrator` intact.
   - Zero `InputReader: Received unexpected event (0x35/0x36)` drops; user confirmed typing and touch issues resolved.
