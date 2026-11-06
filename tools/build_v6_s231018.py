#!/usr/bin/env python3
"""
Himax TB350XU (Firmware TB350XU_USER_S231018_2601050930_MP_ROW)
Touch Candidate v6:
  - Linux Multi-Touch Protocol Type-B Compliant Ordering (ABS_MT_TRACKING_ID before coordinates)
  - Eliminates "InputReader: Received unexpected event (0x35/0x36)" coordinate drop bug
  - Eliminates fast-typing keystroke drops and missing keyboard ripple animations
  - Active-Low Level-Triggered IRQ (0x2008 = IRQF_TRIGGER_LOW | IRQF_ONESHOT)
  - Balanced Normal Physical Sensitivity (no phantom touches, no freezing)
  - SPI transfer error recovery & prevent-notch buffer offset fix
"""
import os
import sys
import struct
import hashlib
from pathlib import Path

WORKSPACE = Path(r"E:\RUTURAJ DO NOT DELETE\P11_TOUCH_FINAL")
FINAL_OUT = WORKSPACE / "final_output"
sys.path.insert(0, str(FINAL_OUT))
import BUILD_FINAL

ORIG_IMG = Path(r"E:\RUTURAJ DO NOT DELETE\tab p 11 gen 2\TB350XU_USER_S231018_2601050930_MP_ROW\image\vendor_boot.img")
ORIG_IMG_SHA256 = "0c06ebe186f39b1ec64398fc8e3bad74b0c2a7c4fae8134822f7adcc12c0a7c4"
ORIG_MOD_SHA256 = "1085f0a9b0b12dabb6a1c658982798b1bc152dddc44abae055378a7ff6ed8b29"
TEXT_SIZE_ORIG = 149960  # 0x249c8

H1_OFF = TEXT_SIZE_ORIG + 0   # 0x249c8
H2_OFF = TEXT_SIZE_ORIG + 20  # 0x249dc
H3_OFF = TEXT_SIZE_ORIG + 40  # 0x249f0
H4_OFF = TEXT_SIZE_ORIG + 56  # 0x24a00

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

ALL_HOOKS_HEX = (H1_BYTES + H2_BYTES + H3_BYTES + H4_BYTES).hex()

S231018_V6_MANIFEST = {
    "name": "Himax TB350XU S231018 v6 (Type-B Multi-Touch Protocol Fix + Zero Freeze)",
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

        # P10: Multi-Touch Type-B Protocol Event Ordering Fix (Smoking Gun Fix):
        # Emit ABS_MT_TRACKING_ID via input_mt_report_slot_state BEFORE coordinates!
        {"offset": 0x0360c, "old": "680340f9", "new": "80ba40f9",
         "label": "[P10a] ldr x0, [x20, #0x170] (input_dev for input_mt_report_slot_state)"},
        {"offset": 0x03610, "old": "80ba40f9", "new": "e1031f2a",
         "label": "[P10b] mov w1, wzr (MT_TOOL_FINGER = 0)"},
        {"offset": 0x03614, "old": "61008052", "new": "22008052",
         "label": "[P10c] mov w2, #1 (active = 1)"},
        {"offset": 0x03618, "old": "02068052", "new": "1f2003d5",
         "label": "[P10d] NOP"},
        {"offset": 0x0361c, "old": "080140f9", "new": "1f2003d5",
         "label": "[P10e] NOP"},
        {"offset": 0x03620, "old": "08011a8b", "new": "1f2003d5",
         "label": "[P10f] NOP"},
        {"offset": 0x03624, "old": "030940b9", "new": "1f2003d5",
         "label": "[P10g] NOP"},
        # 0x03628 calls input_mt_report_slot_state (reloc changed from 1497 to 1496)
        {"offset": 0x03638, "old": "42068052", "new": "02068052",
         "label": "[P10h] mov w2, #0x30 (reports ABS_MT_TOUCH_MAJOR)"},
        {"offset": 0x036ac, "old": "b6ffff17", "new": "baffff17",
         "label": "[P10i] b 0x3594 (advance to next slot directly, skip late slot_state)"},
    ],

    "append_text": ALL_HOOKS_HEX,

    "relocation_moves": [
        {"old": 0x11934, "new": H1_OFF + 12},  # P1 -> H1 ldr x8,[x21]
        {"old": 0x2364c, "new": H2_OFF + 12},  # P3 -> H2 ldr x8,[x25]
        {"old": 0x04820, "new": H3_OFF + 8},   # P4 -> H3 adrp x0,page
        {"old": 0x04acc, "new": H4_OFF + 8},   # P5 -> H4 adrp x8,page
    ],

    "relocation_symbol_changes": [
        {"offset": 0x03628, "old_sym": 1497, "new_sym": 1496,
         "label": "[P10-reloc] Change call at 0x3628 to input_mt_report_slot_state"},
    ],

    "relocation_zero_out": [
        0x0360c,  # Stale R_AARCH64_LD64_GOT_LO12_NC from replaced ldr x8,[x27]
    ]
}

def patch_s231018_v6_module(data, manifest):
    """Custom module patcher for S231018 v6."""
    assert BUILD_FINAL.sha(data) == manifest['base_module_sha256'], "SHA mismatch on base module!"
    
    sections = BUILD_FINAL.elf_sections(data)
    byname = {s['name']: s for s in sections}
    textsec = byname['.text']
    textdata = bytearray(textsec['data'])
    assert len(textdata) == manifest['text_size'], f"Unexpected text size {len(textdata)}"

    hook_branches = {
        0x11934: arm64_b(0x11934, H1_OFF),
        0x2364c: arm64_b(0x2364c, H2_OFF),
        0x04820: arm64_b(0x04820, H3_OFF),
        0x04acc: arm64_b(0x04acc, H4_OFF),
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
        assert actual_old == old_bytes, f"Mismatch at text+0x{o:x}: expected {p['old']}, got {actual_old.hex()} ({p['label']})"
        textdata[o:o+4] = new_bytes
        print(f"  [+] Patched text+0x{o:05x}: {p['old']} -> {new_bytes.hex()} ({p['label']})")

    # Append hook code
    append_bytes = bytes.fromhex(manifest['append_text'])
    textdata.extend(append_bytes)
    textsec['data'] = bytes(textdata)
    textsec['header'][5] = len(textdata)
    print(f"  [+] Appended {len(append_bytes)} bytes of hook code. New .text size: 0x{len(textdata):x}")

    # Relocation updates (moves)
    moves = {m['old']: m['new'] for m in manifest['relocation_moves']}
    sym_changes = {c['offset']: (c['old_sym'], c['new_sym'], c['label']) for c in manifest['relocation_symbol_changes']}
    zero_outs = set(manifest.get('relocation_zero_out', []))

    found_moves = set()
    found_changes = set()
    found_zeros = set()

    for sec in sections:
        h = sec['header']
        if h[1] != 4 or h[7] != textsec['index']:
            continue
        rel = bytearray(sec['data'])
        for o in range(0, len(rel), 24):
            ro, info, addend = struct.unpack_from('<QQq', rel, o)
            r_type = info & 0xffffffff
            r_sym = info >> 32

            if ro in moves:
                assert ro not in found_moves, f"Duplicate relocation at 0x{ro:x}"
                struct.pack_into('<Q', rel, o, moves[ro])
                found_moves.add(ro)
                print(f"  [+] Moved relocation: 0x{ro:05x} -> 0x{moves[ro]:05x}")

            if ro in sym_changes:
                old_s, new_s, lbl = sym_changes[ro]
                assert r_sym == old_s, f"Relocation symbol mismatch at 0x{ro:x}: expected {old_s}, got {r_sym}"
                new_info = (new_s << 32) | r_type
                struct.pack_into('<Q', rel, o + 8, new_info)
                found_changes.add(ro)
                print(f"  [+] Changed relocation symbol at 0x{ro:05x}: sym {old_s} -> {new_s} ({lbl})")

            if ro in zero_outs:
                # Set info = 0 (R_AARCH64_NONE) and addend = 0
                struct.pack_into('<Qq', rel, o + 8, 0, 0)
                found_zeros.add(ro)
                print(f"  [+] Zeroed out stale relocation at 0x{ro:05x} (R_AARCH64_NONE)")

        sec['data'] = bytes(rel)

    assert found_moves == set(moves), f"Missing relocation moves: {set(moves) - found_moves}"
    assert found_changes == set(sym_changes), f"Missing relocation symbol changes: {set(sym_changes) - found_changes}"
    assert found_zeros == zero_outs, f"Missing zero out relocations: {zero_outs - found_zeros}"

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

    # Update GNU build ID
    note = byname.get('.note.gnu.build-id')
    if note:
        o = note['header'][4]
        out[o+16:o+36] = bytes(20)
        out[o+16:o+36] = hashlib.sha1(out).digest()

    return bytes(out)

def build_v6_s231018():
    print(f"[*] Reading stock image: {ORIG_IMG}")
    with open(ORIG_IMG, "rb") as f:
        img_data = f.read()

    assert BUILD_FINAL.sha(img_data) == ORIG_IMG_SHA256, "Stock image SHA mismatch!"
    info = BUILD_FINAL.parse_image(img_data)
    cpio = BUILD_FINAL.decompress_legacy(info["ramdisk"])
    entries = BUILD_FINAL.cpio_entries(cpio)

    mod_name = "lib/modules/himax_mmi.ko"
    target_e = next(e for e in entries if e['name'] == mod_name)
    mod_bytes = cpio[target_e['body']:target_e['body']+target_e['size']]

    print(f"[*] Original himax_mmi.ko SHA: {BUILD_FINAL.sha(mod_bytes)}")
    assert BUILD_FINAL.sha(mod_bytes) == ORIG_MOD_SHA256

    print("\n[*] Applying S231018 v6 Patches (Type-B Multi-Touch Protocol Fix)...")
    patched_mod = patch_s231018_v6_module(mod_bytes, S231018_V6_MANIFEST)
    print(f"[+] Patched module SHA256: {BUILD_FINAL.sha(patched_mod)}")

    new_cpio = BUILD_FINAL.replace_cpio(cpio, entries, mod_name, patched_mod)
    print(f"[*] Compressing ramdisk (LZ4 legacy)...")
    new_ramdisk = BUILD_FINAL.compress_legacy(new_cpio)
    print(f"[+] New compressed ramdisk size: {len(new_ramdisk)} bytes")

    print("[*] Repacking vendor_boot image & updating AVB vbmeta...")
    output_image = BUILD_FINAL.repack(img_data, info, new_ramdisk)

    out_file = FINAL_OUT / "vendor_boot_TB350XU_S231018_v6_touch_protocol_fix.img"
    with open(out_file, "wb") as f:
        f.write(output_image)

    print(f"\n=======================================================")
    print(f"[+] Generated: {out_file.name}")
    print(f"[+] Output path: {out_file}")
    print(f"[+] Size: {len(output_image)} bytes")
    print(f"[+] SHA256: {BUILD_FINAL.sha(output_image)}")
    print(f"=======================================================")
    return out_file

if __name__ == "__main__":
    build_v6_s231018()
