#!/usr/bin/env python3
"""
Himax TB350XU S231018 Candidate v5.2 (High-Sensitivity HSEN + Level IRQ + Zero Latency)
Combines:
  1. Active-Low Level-Triggered IRQ (0x2008 = IRQF_TRIGGER_LOW | IRQF_ONESHOT) across all 5 sites (P8a-e)
  2. Hardware High-Sensitivity Mode (HSEN) on boot and resend (P7 -> H5 calling himax_mcu_set_HSEN_enable(1))
  3. SPI read status propagation (P1-P3)
  4. Finger release before reset and recovery (P4-P5)
  5. Correct prevent-notch buffer offset (P6)
"""
import os, sys, struct, hashlib
from pathlib import Path

WORKSPACE = Path(r"E:\RUTURAJ DO NOT DELETE\P11_TOUCH_FINAL")
FINAL_OUT = WORKSPACE / "final_output"
sys.path.insert(0, str(FINAL_OUT))
import BUILD_FINAL

ORIG_IMG = Path(r"E:\RUTURAJ DO NOT DELETE\tab p 11 gen 2\TB350XU_USER_S231018_2601050930_MP_ROW\image\vendor_boot.img")
ORIG_IMG_SHA256 = "0c06ebe186f39b1ec64398fc8e3bad74b0c2a7c4fae8134822f7adcc12c0a7c4"
ORIG_MOD_SHA256 = "1085f0a9b0b12dabb6a1c658982798b1bc152dddc44abae055378a7ff6ed8b29"
TEXT_SIZE_ORIG = 149960  # 0x249c8

H1_OFF = TEXT_SIZE_ORIG + 0   # 0x249c8 (20 bytes)
H2_OFF = TEXT_SIZE_ORIG + 20  # 0x249dc (20 bytes)
H3_OFF = TEXT_SIZE_ORIG + 40  # 0x249f0 (16 bytes)
H4_OFF = TEXT_SIZE_ORIG + 56  # 0x24a00 (16 bytes)
H5_OFF = TEXT_SIZE_ORIG + 72  # 0x24a10 (36 bytes)

def arm64_b(src, dst):
    diff = (dst - src) // 4
    return struct.pack('<I', 0x14000000 | (diff & 0x03ffffff))

def arm64_bl(src, dst):
    diff = (dst - src) // 4
    return struct.pack('<I', 0x94000000 | (diff & 0x03ffffff))

def arm64_b_ne(src, dst):
    diff = (dst - src) // 4
    return struct.pack('<I', 0x54000001 | ((diff & 0x7ffff) << 5))

# Compute hook byte sequences
H1_BYTES = (
    bytes.fromhex("1f000071") +  # cmp w0, #0
    bytes.fromhex("e0179f1a") +  # cset w0, eq
    bytes.fromhex("e00300b9") +  # str w0, [sp]
    bytes.fromhex("a80240f9") +  # ldr x8, [x21]
    arm64_b(H1_OFF + 16, 0x11938)
)

H2_BYTES = (
    bytes.fromhex("a8c35bb8") +  # ldur w8, [x29, #-0x44]
    bytes.fromhex("1f01176b") +  # cmp w8, w23
    arm64_b_ne(H2_OFF + 8, 0x236d4) +
    bytes.fromhex("280340f9") +  # ldr x8, [x25]
    arm64_b(H2_OFF + 16, 0x23650)
)

H3_BYTES = (
    bytes.fromhex("e00313aa") +  # mov x0, x19
    arm64_bl(H3_OFF + 4, 0x054e8) + # bl himax_release_all_points
    bytes.fromhex("00000090") +  # adrp x0, page
    arm64_b(H3_OFF + 12, 0x04824)
)

H4_BYTES = (
    bytes.fromhex("e00313aa") +  # mov x0, x19
    arm64_bl(H4_OFF + 4, 0x054e8) + # bl himax_release_all_points
    bytes.fromhex("08000090") +  # adrp x8, page
    arm64_b(H4_OFF + 12, 0x04ad0)
)

# Hook 5 (HSEN - High Sensitivity Mode)
H5_BYTES = (
    bytes.fromhex("e87bbfa9") +     # stp x8, x30, [sp, #-16]!
    bytes.fromhex("b30000b4") +     # cbz x19, done (+24 bytes)
    bytes.fromhex("61064039") +     # ldrb w1, [x19, #1]
    bytes.fromhex("61000035") +     # cbnz w1, done (+12 bytes)
    bytes.fromhex("20008052") +     # mov w0, #1 (HSEN enable = 1)
    arm64_bl(H5_OFF + 20, 0x14658) +# bl himax_mcu_set_HSEN_enable
    bytes.fromhex("e87bc1a8") +     # ldp x8, x30, [sp], #16
    bytes.fromhex("09000090") +     # adrp x9, page (displaced from 0x1a50c)
    arm64_b(H5_OFF + 32, 0x1a510)   # b back to 0x1a510
)

ALL_HOOKS_HEX = (H1_BYTES + H2_BYTES + H3_BYTES + H4_BYTES + H5_BYTES).hex()

S231018_V52_MANIFEST = {
    "name": "Himax TB350XU S231018 v5.2 (High-Sensitivity HSEN + Level IRQ)",
    "base_module_sha256": ORIG_MOD_SHA256,
    "text_size": TEXT_SIZE_ORIG,

    "text_patches": [
        # P1: Propagate SPI read status
        {"offset": 0x11934, "old": "a80240f9", "new": None,
         "label": "[P1] Propagate SPI read status to caller"},
        # P2: Return actual read result
        {"offset": 0x119c8, "old": "20008052", "new": "e00340b9",
         "label": "[P2] Return actual read result (not hardcoded 1)"},
        # P3: Reject short SPI transfers
        {"offset": 0x2364c, "old": "280340f9", "new": None,
         "label": "[P3] Reject short SPI transfers"},
        # P4: Release finger contacts before read-fail reset
        {"offset": 0x04820, "old": "00000090", "new": None,
         "label": "[P4] Release finger contacts before read-fail reset"},
        # P5: Release finger contacts before exception recovery
        {"offset": 0x04acc, "old": "08000090", "new": None,
         "label": "[P5] Release finger contacts before exception recovery"},
        # P6: Fix prevent_notch buffer offset
        {"offset": 0x04bc0, "old": "00f10091", "new": "00310191",
         "label": "[P6] Fix prevent_notch buffer offset (ts+0x3c->ts+0x4c)"},

        # P7: Request HSEN High-Sensitivity Mode during active settings resend
        {"offset": 0x1a50c, "old": "09000090", "new": None,
         "label": "[P7] Request HSEN High-Sensitivity Mode during active resend"},

        # P8: Active-Low Level-Triggered IRQ (0x2008 = IRQF_TRIGGER_LOW | IRQF_ONESHOT)
        {"offset": 0x163b8, "old": "00010012", "new": "e0031f2a",
         "label": "[P8a] himax_mcu_read_ic_trigger_type: force return 0"},
        {"offset": 0x23b44, "old": "b4018c9a", "new": "f4030daa",
         "label": "[P8b] himax_int_register_trigger: force x20=x13=0x2008"},
        {"offset": 0x23bd4, "old": "b4018c9a", "new": "f4030daa",
         "label": "[P8c] himax_int_en_set: force x20=x13=0x2008"},
        {"offset": 0x23ca0, "old": "94018b9a", "new": "f4030caa",
         "label": "[P8d] himax_ts_register_interrupt: force x20=x12=0x2008"},
        {"offset": 0x08cfc, "old": "95018b9a", "new": "f5030caa",
         "label": "[P8e] himax_int_en_write: force x21=x12=0x2008"},
    ],

    "append_text": ALL_HOOKS_HEX,

    "relocation_moves": [
        {"old": 0x11934, "new": H1_OFF + 12},  # P1 -> H1 ldr x8,[x21]
        {"old": 0x2364c, "new": H2_OFF + 12},  # P3 -> H2 ldr x8,[x25]
        {"old": 0x04820, "new": H3_OFF + 8},   # P4 -> H3 adrp x0,page
        {"old": 0x04acc, "new": H4_OFF + 8},   # P5 -> H4 adrp x8,page
        {"old": 0x1a50c, "new": H5_OFF + 28},  # P7 -> H5 adrp x9,page
    ]
}

def patch_s231018_module(data, manifest):
    assert BUILD_FINAL.sha(data) == manifest['base_module_sha256']
    sections = BUILD_FINAL.elf_sections(data)
    byname = {s['name']: s for s in sections}
    textsec = byname['.text']
    textdata = bytearray(textsec['data'])
    assert len(textdata) == manifest['text_size']

    hook_branches = {
        0x11934: arm64_b(0x11934, H1_OFF),
        0x2364c: arm64_b(0x2364c, H2_OFF),
        0x04820: arm64_b(0x04820, H3_OFF),
        0x04acc: arm64_b(0x04acc, H4_OFF),
        0x1a50c: arm64_b(0x1a50c, H5_OFF),
    }

    for p in manifest['text_patches']:
        o = p['offset']
        old_bytes = bytes.fromhex(p['old'])
        if p['new'] is None:
            new_bytes = hook_branches[o]
        else:
            new_bytes = bytes.fromhex(p['new'])
        assert len(old_bytes) == len(new_bytes) == 4
        actual_old = textdata[o:o+4]
        assert actual_old == old_bytes, f"Mismatch at text+0x{o:x}: expected {old_bytes.hex()}, got {actual_old.hex()}"
        textdata[o:o+4] = new_bytes
        print(f"  [+] Patched text+0x{o:05x}: {p['old']} -> {new_bytes.hex()} ({p['label']})")

    append_bytes = bytes.fromhex(manifest['append_text'])
    textdata.extend(append_bytes)
    textsec['data'] = bytes(textdata)
    textsec['header'][5] = len(textdata)
    print(f"  [+] Appended {len(append_bytes)} bytes of hook code. New .text size: 0x{len(textdata):x}")

    moves = {m['old']: m['new'] for m in manifest['relocation_moves']}
    found = set()
    for sec in sections:
        h = sec['header']
        if h[1] != 4 or h[7] != textsec['index']:
            continue
        rel = bytearray(sec['data'])
        for o in range(0, len(rel), 24):
            ro, info_val, addend = struct.unpack_from('<QQq', rel, o)
            if ro in moves:
                assert ro not in found, f"Duplicate relocation at 0x{ro:x}"
                struct.pack_into('<Q', rel, o, moves[ro])
                found.add(ro)
                print(f"  [+] Moved relocation: 0x{ro:05x} -> 0x{moves[ro]:05x}")
        sec['data'] = bytes(rel)

    assert found == set(moves), f"Missing relocations: {set(moves) - found}"

    # Rebuild ELF
    out = bytearray(data[:64])
    for sec in sections[1:]:
        h = sec['header']
        pos = BUILD_FINAL.align(len(out), max(1, h[8]))
        out.extend(bytes(pos - len(out)))
        h[4] = pos
        if h[1] != 8:
            out.extend(sec['data'])

    shoff = BUILD_FINAL.align(len(out), 8)
    out.extend(bytes(shoff - len(out)))
    struct.pack_into('<Q', out, 40, shoff)
    for sec in sections:
        out.extend(struct.pack('<IIQQQQIIQQ', *sec['header']))

    note = byname.get('.note.gnu.build-id')
    if note:
        o = note['header'][4]
        out[o+16:o+36] = bytes(20)
        out[o+16:o+36] = hashlib.sha1(out).digest()

    return bytes(out)

def main():
    print("=" * 70)
    print("Building Himax TB350XU S231018 Candidate v5.2 (HighSense + Level IRQ)")
    print("=" * 70)

    with open(ORIG_IMG, "rb") as f:
        img_data = f.read()

    info = BUILD_FINAL.parse_image(img_data)
    cpio = BUILD_FINAL.decompress_legacy(info["ramdisk"])
    entries = BUILD_FINAL.cpio_entries(cpio)

    mod_name = "lib/modules/himax_mmi.ko"
    target_e = next(e for e in entries if e['name'] == mod_name)
    mod_bytes = cpio[target_e['body']:target_e['body']+target_e['size']]

    patched_mod = patch_s231018_module(mod_bytes, S231018_V52_MANIFEST)
    new_cpio = BUILD_FINAL.replace_cpio(cpio, entries, mod_name, patched_mod)
    new_ramdisk = BUILD_FINAL.compress_legacy(new_cpio)
    output_image = BUILD_FINAL.repack(img_data, info, new_ramdisk)

    v52_path = FINAL_OUT / "vendor_boot_TB350XU_S231018_v5.2_high_sensitivity.img"
    with open(v52_path, "wb") as f:
        f.write(output_image)

    print(f"\n[+] Successfully generated: {v52_path.name}")
    print(f"[+] Output path: {v52_path}")
    print(f"[+] Size: {len(output_image)} bytes")
    print(f"[+] SHA256: {hashlib.sha256(output_image).hexdigest()}")
    print("=" * 70)

if __name__ == "__main__":
    main()
