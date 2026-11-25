#!/usr/bin/env python3
"""Patch stock S231018 vendor_boot.img for Lenovo Tab P11 Gen 2 (TB350XU / TB350FU).

Applies verified ARM64 binary hooks H1..H7 (P1..P7, P9, P10) to lib/modules/himax_mmi.ko
(driver 2.1.0.2_Tulip_01 on Android 14 S231018, kernel 5.10.233-android12-9-g9568a331d924):
  - [P1+P2 / H1] 0x11938 + 0x119C8: Propagate real SPI read status in hx83102j_read_event_stack
  - [P3 / H2]    0x23650: Reject short SPI reads in himax_bus_read (actual_length != w23 -> -EIO)
  - [P4 / H3]    0x0484C: Release all touch contacts before SPI read-fail reset
  - [P5 / H4]    0x04AEC: Release all touch contacts before exception recovery reset
  - [P6]         0x04BC0: Fix prevent_notch recovery struct offset (#0x3C -> #0x4C)
  - [P7 / H5]    0x1A514: Enable High-Sensitivity mode (HSEN 0x10007F14 = 0xA55AA55A) when active
  - [P9 / H7]    0x037B8: Check BOTH p_point_num and pre_finger_mask on lift so slots clear cleanly
  - [P10 / H6]   0x03610 + 0x036AC: Report slot state before coordinates & attributes (no 0x35/0x36 drops)
Preserves native EDGE IRQ trigger (0x2002) matching hardware int_is_edge=1.
"""

import argparse
import hashlib
import pathlib
import struct
import sys
from capstone import CS_ARCH_ARM64, CS_MODE_ARM, Cs

TOOLS_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
DEFAULT_STOCK_VB = (
    REPO_ROOT.parent
    / "TB350XU_USER_S231018_2601050930_MP_ROW"
    / "image"
    / "vendor_boot.img"
)
DEFAULT_OUT_VB = REPO_ROOT.parent / "vendor_boot_TB350XU_S231018_touch_fix.img"
DEFAULT_OUT_KO = REPO_ROOT.parent / "himax_mmi_s231018_patched.ko"

EXPECTED_STOCK_VB_SHA256 = "0c06ebe186f39b1ec64398fc8e3bad74b0c2a7c4fae8134822f7adcc12c0a7c4"
EXPECTED_STOCK_KO_SHA256 = "1085f0a9b0b12dabb6a1c658982798b1bc152dddc44abae055378a7ff6ed8b29"

sys.path.insert(0, str(TOOLS_DIR))
import vendor_boot_image as vbi  # noqa: E402


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def enc_b(src: int, dst: int) -> bytes:
    delta = dst - src
    assert delta % 4 == 0
    imm26 = delta >> 2
    assert -(1 << 25) <= imm26 < (1 << 25)
    return struct.pack("<I", 0x14000000 | (imm26 & 0x03FFFFFF))


def enc_bl(src: int, dst: int) -> bytes:
    delta = dst - src
    assert delta % 4 == 0
    imm26 = delta >> 2
    assert -(1 << 25) <= imm26 < (1 << 25)
    return struct.pack("<I", 0x94000000 | (imm26 & 0x03FFFFFF))


def enc_cond_b(cond: int, src: int, dst: int) -> bytes:
    delta = dst - src
    assert delta % 4 == 0
    imm19 = delta >> 2
    assert -(1 << 18) <= imm19 < (1 << 18)
    return struct.pack("<I", 0x54000000 | ((imm19 & 0x7FFFF) << 5) | cond)


def enc_cbz(reg: int, is64: bool, nz: bool, src: int, dst: int) -> bytes:
    delta = dst - src
    assert delta % 4 == 0
    imm19 = delta >> 2
    assert -(1 << 18) <= imm19 < (1 << 18)
    sf = 0x80000000 if is64 else 0
    op = 0x35000000 if nz else 0x34000000
    return struct.pack("<I", sf | op | ((imm19 & 0x7FFFF) << 5) | (reg & 31))


def rebuild_elf_with_appended_text_and_rela(ko: bytes, new_text: bytes, extra_text_relas: list) -> bytes:
    e_shoff = struct.unpack_from("<Q", ko, 40)[0]
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", ko, 58)
    assert e_shentsize == 64

    secs = []
    shstr_hdr = struct.unpack_from("<IIQQQQIIQQ", ko, e_shoff + e_shstrndx * 64)
    shstrtab = ko[shstr_hdr[4] : shstr_hdr[4] + shstr_hdr[5]]

    for i in range(e_shnum):
        hdr = list(struct.unpack_from("<IIQQQQIIQQ", ko, e_shoff + i * 64))
        sh_name, sh_type, _flags, _addr, sh_offset, sh_size, _link, _info, _align, _entsize = hdr
        nm_end = shstrtab.find(b"\x00", sh_name)
        nm = shstrtab[sh_name:nm_end].decode(errors="replace")
        raw = b"" if sh_type in (0, 8) else ko[sh_offset : sh_offset + sh_size]
        secs.append({"idx": i, "name": nm, "hdr": hdr, "data": raw})

    text_sec = secs[1]
    assert text_sec["name"] == ".text"
    rela_text_sec = next(s for s in secs if s["hdr"][1] == 4 and s["hdr"][7] == 1)

    text_sec["data"] = new_text
    text_sec["hdr"][5] = len(new_text)

    if extra_text_relas:
        buf = bytearray(rela_text_sec["data"])
        for r_off, r_sym, r_type, r_add in extra_text_relas:
            r_info = (r_sym << 32) | (r_type & 0xFFFFFFFF)
            buf += struct.pack("<QQq", r_off, r_info, r_add)
        rela_text_sec["data"] = bytes(buf)
        rela_text_sec["hdr"][5] = len(buf)

    out = bytearray(ko[:64])
    assert secs[1]["hdr"][4] >= 64
    cursor = secs[1]["hdr"][4]
    out += b"\x00" * (cursor - len(out))

    for s in secs[1:]:
        sh_type = s["hdr"][1]
        align = max(1, s["hdr"][8])
        if sh_type == 8:
            s["hdr"][4] = (len(out) + align - 1) & ~(align - 1)
            continue
        pad = ((len(out) + align - 1) & ~(align - 1)) - len(out)
        out += b"\x00" * pad
        s["hdr"][4] = len(out)
        s["hdr"][5] = len(s["data"])
        out += s["data"]

    pad = ((len(out) + 7) & ~7) - len(out)
    out += b"\x00" * pad
    new_e_shoff = len(out)
    for s in secs:
        out += struct.pack("<IIQQQQIIQQ", *s["hdr"])

    struct.pack_into("<Q", out, 40, new_e_shoff)
    return bytes(out)


def build_image(stock_vb: pathlib.Path, out_vb: pathlib.Path, out_ko: pathlib.Path | None = None) -> None:
    vb_raw = stock_vb.read_bytes()
    assert sha256(vb_raw) == EXPECTED_STOCK_VB_SHA256, f"Unexpected stock vendor_boot sha256: {sha256(vb_raw)}"
    print(f"[+] Loaded stock S231018 vendor_boot.img ({len(vb_raw)} bytes, SHA256={EXPECTED_STOCK_VB_SHA256[:16]}...)")

    info = vbi.parse_image(vb_raw)
    cpio = vbi.decompress_legacy(info["ramdisk"])
    entries = vbi.cpio_entries(cpio)
    ko_entry = next(x for x in entries if x["name"] == "lib/modules/himax_mmi.ko")
    ko = cpio[ko_entry["body"] : ko_entry["body"] + ko_entry["size"]]
    assert sha256(ko) == EXPECTED_STOCK_KO_SHA256, f"Unexpected stock himax_mmi.ko sha256: {sha256(ko)}"
    print(f"[+] Extracted stock himax_mmi.ko ({len(ko)} bytes, SHA256={EXPECTED_STOCK_KO_SHA256[:16]}...)")

    secs = vbi.elf_sections(ko)
    byname = {s["name"]: s for s in secs}
    orig_text = byname[".text"]["data"]
    assert len(orig_text) == 0x249C8

    expected_orig = {
        0x11938: bytes.fromhex("08714239"),
        0x119C8: bytes.fromhex("20008052"),
        0x23650: bytes.fromhex("e203132a"),
        0x0484C: bytes.fromhex("21008052"),
        0x04AEC: bytes.fromhex("a0023fd6"),
        0x04BC0: bytes.fromhex("00f10091"),
        0x1A514: bytes.fromhex("696242f9"),
        0x037B8: bytes.fromhex("480d0034"),
        0x03610: bytes.fromhex("80ba40f9"),
        0x036AC: bytes.fromhex("b6ffff17"),
    }
    for off, exp in expected_orig.items():
        actual = orig_text[off : off + 4]
        assert actual == exp, f"Mismatch at 0x{off:05x}: expected {exp.hex()}, got {actual.hex()}"

    rela_sec = next(s for s in secs if s["header"][1] == 4 and s["header"][7] == 1)
    existing_rela_offs = {struct.unpack_from("<QQq", rela_sec["data"], o)[0] for o in range(0, len(rela_sec["data"]), 24)}
    for off in expected_orig:
        assert off not in existing_rela_offs, f"BUG: 0x{off:05x} has an existing relocation!"

    text = bytearray(orig_text)
    base = len(text)

    # H1 [P1]: hx83102j_read_event_stack status capture
    H1 = len(text)
    text += bytes.fromhex("1f000071")
    text += bytes.fromhex("e0179f1a")
    text += bytes.fromhex("e00300b9")
    text += bytes.fromhex("08714239")
    text += enc_b(len(text), 0x1193C)

    # H2 [P3]: himax_bus_read actual_length == frame_length check
    H2 = len(text)
    text += bytes.fromhex("a9c35bb8")
    text += bytes.fromhex("3f01176b")
    text += enc_cond_b(1, len(text), 0x23744)
    text += bytes.fromhex("e203132a")
    text += enc_b(len(text), 0x23654)

    # H3 [P4]: himax_report_all_leave_event before SPI read-fail reset
    H3 = len(text)
    text += bytes.fromhex("e00313aa")
    text += enc_bl(len(text), 0x054E8)
    text += bytes.fromhex("21008052")
    text += enc_b(len(text), 0x04850)

    # H4 [P5]: himax_report_all_leave_event before exception recovery reset
    H4 = len(text)
    text += bytes.fromhex("e00313aa")
    text += enc_bl(len(text), 0x054E8)
    text += bytes.fromhex("a0023fd6")
    text += enc_b(len(text), 0x04AF0)

    # H5 [P7]: Enable HSEN (0x10007F14 = 0xA55AA55A) when active (!ts->suspended)
    H5 = len(text)
    H5_skip = H5 + 6 * 4
    text += bytes.fromhex("e87bbfa9")
    text += enc_cbz(19, True, False, H5 + 4, H5_skip)
    text += bytes.fromhex("61064039")
    text += enc_cbz(1, False, True, H5 + 12, H5_skip)
    text += bytes.fromhex("20008052")
    text += enc_bl(H5 + 20, 0x14658)
    assert len(text) == H5_skip
    text += bytes.fromhex("e87bc1a8")
    text += bytes.fromhex("696242f9")
    text += enc_b(len(text), 0x1A518)

    # H6 [P10]: Emit input_mt_report_slot_state before coordinates & attributes
    H6 = len(text)
    text += bytes.fromhex("e87bbfa9")
    text += bytes.fromhex("80ba40f9")
    text += bytes.fromhex("e1031f2a")
    text += bytes.fromhex("e203182a")
    H6_bl_off = len(text)
    text += bytes.fromhex("00000094")
    text += bytes.fromhex("e87bc1a8")
    text += bytes.fromhex("80ba40f9")
    text += enc_b(len(text), 0x03614)

    # H7 [P9]: Check both p_point_num and pre_finger_mask ([x20, #0x90])
    H7 = len(text)
    text += bytes.fromhex("89224179")
    text += bytes.fromhex("0801092a")
    text += enc_cbz(8, False, False, len(text), 0x03960)
    text += enc_b(len(text), 0x037BC)

    text[0x11938:0x1193C] = enc_b(0x11938, H1)
    text[0x119C8:0x119CC] = bytes.fromhex("e00340b9")
    text[0x23650:0x23654] = enc_b(0x23650, H2)
    text[0x0484C:0x04850] = enc_b(0x0484C, H3)
    text[0x04AEC:0x04AF0] = enc_b(0x04AEC, H4)
    text[0x04BC0:0x04BC4] = bytes.fromhex("00310191")
    text[0x1A514:0x1A518] = enc_b(0x1A514, H5)
    text[0x03610:0x03614] = enc_b(0x03610, H6)
    text[0x036AC:0x036B0] = enc_b(0x036AC, 0x03594)
    text[0x037B8:0x037BC] = enc_b(0x037B8, H7)

    symtab = byname[".symtab"]["data"]
    strtab = byname[".strtab"]["data"]
    st_name = struct.unpack_from("<I", symtab, 1496 * 24)[0]
    sym_nm = strtab[st_name : strtab.find(b"\x00", st_name)].decode()
    assert sym_nm == "input_mt_report_slot_state"

    new_ko = rebuild_elf_with_appended_text_and_rela(ko, bytes(text), [(H6_bl_off, 1496, 283, 0)])
    if out_ko is not None:
        out_ko.write_bytes(new_ko)
    print(f"[+] Built patched himax_mmi.ko: {len(new_ko)} bytes (+{len(text) - base}B .text), SHA256={sha256(new_ko)}")

    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    assert len(list(md.disasm(text[base:], base))) == (len(text) - base) // 4

    new_cpio = vbi.replace_cpio(cpio, entries, "lib/modules/himax_mmi.ko", new_ko)
    comp_rd = vbi.compress_legacy(new_cpio)
    final_vb = vbi.repack(vb_raw, info, comp_rd)
    assert len(final_vb) == len(vb_raw) == 67108864
    out_vb.write_bytes(final_vb)

    chk_info = vbi.parse_image(final_vb)
    chk_cpio = vbi.decompress_legacy(chk_info["ramdisk"])
    chk_e = next(x for x in vbi.cpio_entries(chk_cpio) if x["name"] == "lib/modules/himax_mmi.ko")
    assert chk_cpio[chk_e["body"] : chk_e["body"] + chk_e["size"]] == new_ko
    print(f"[+] Roundtrip verified: {out_vb} (SHA256={sha256(final_vb)})")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build patched S231018 vendor_boot.img for Lenovo Tab P11 Gen 2")
    ap.add_argument("--stock-vendor-boot", type=pathlib.Path, default=DEFAULT_STOCK_VB, help="Path to stock S231018 vendor_boot.img")
    ap.add_argument("--out-img", type=pathlib.Path, default=DEFAULT_OUT_VB, help="Output path for patched vendor_boot image")
    ap.add_argument("--out-ko", type=pathlib.Path, default=DEFAULT_OUT_KO, help="Output path for patched himax_mmi.ko")
    args = ap.parse_args()
    build_image(args.stock_vendor_boot, args.out_img, args.out_ko)


if __name__ == "__main__":
    main()
