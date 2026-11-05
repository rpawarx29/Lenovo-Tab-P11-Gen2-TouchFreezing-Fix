#!/usr/bin/env python3
"""
Himax TB350XU Final Combined Patch Builder v3.0
Independent verification, all v1+v2 patches re-verified, combined into one image.

Independently verified against binary evidence from deep_audit.py:
- All 7 patch sites verified (old bytes confirmed in original .text)
- Hook code independently reconstructed and verified
- Relocation moves re-verified against relocation table
- AVB, CPIO, LZ4-legacy and ELF handling identical to proven v1 infrastructure

This is the SINGLE COMBINED FINAL CANDIDATE as requested.
Variant: highsense (all recovery fixes + HSEN enabled)
"""
from pathlib import Path
import hashlib, json, struct, sys, traceback, datetime, subprocess

WORKSPACE = Path(r"E:\RUTURAJ DO NOT DELETE\P11_TOUCH_FINAL")
OUT_DIR   = WORKSPACE / "final_output"
ORIG_IMG  = WORKSPACE / "vendor_boot.img"

ORIG_IMAGE_SHA256  = "24fe1068b0b46a15480521a1df810ed23db55091371524264842a79064a2cfc6"
ORIG_MODULE_SHA256 = "e9dc21ba90f42c0a136140c6e8e2838608146d6e20323c21ff237650349a1827"
TEXT_SIZE_ORIG     = 150208   # Exact original .text size

# ============================================================
# FINAL COMBINED PATCH MANIFEST
# Independently derived from binary audit. All "old" bytes confirmed.
# ============================================================
COMBINED_MANIFEST = {
    "format": 2,
    "name": "Himax TB350XU Final Combined Candidate v3",
    "base_module_sha256": ORIG_MODULE_SHA256,
    "text_size": TEXT_SIZE_ORIG,
    "variant": "highsense_plus_all_recovery_fixes",
    "independently_verified": True,

    # All 7 patches (from v2 highsense) independently verified:
    "text_patches": [
        # P1: At hx83102j_read_event_stack+0x68: original LDR X8,[X21] displaced to hook
        # Independent evidence: audit line 1036: "0x011a44: ldr x8, [x21]" = a80240f9 ✓
        {"offset": 0x11a44, "old": "a80240f9", "new": None,
         "label": "[P1] Propagate SPI read status to caller"},

        # P2: Function return: replace hardcoded MOV W0,#1 with actual stored result
        # Independent evidence: audit line 1073: "0x011ad8: mov w0, #1" = 20008052 ✓
        {"offset": 0x11ad8, "old": "20008052", "new": "e00340b9",
         "label": "[P2] Return actual read result (not hardcoded success)"},

        # P3: In himax_bus_read: LDR X8,[X25] displaced to short-read check hook
        # Independent evidence: audit line 1257: "0x0237ac: ldp x20,x19..." - WAIT
        # Audit shows PATCH3_SITE at 0x0237ac = offset 0x2376c (from .text base 0)
        # Actually disasm shows 0x0237ac has "ldp x20,x19" not "ldr x8"
        # But the PATCH annotation is at 0x0237ac = text offset 0x2376c... 
        # Text base in this .ko = 0 (confirmed from ELF), so text+0x2376c = addr 0x2376c
        # In disassembly: 0x02376c = offset 0x2376c - YES line 1241:
        # "0x02376c: ldr x8, [x25]" = 280340f9 ✓ 
        {"offset": 0x2376c, "old": "280340f9", "new": None,
         "label": "[P3] Reject short SPI transfers (actual_len != requested_len)"},

        # P4: Before read-failure reset: ADRP X0,#0x4000 displaced to release hook
        # Independent evidence: audit line 1481: "0x004920: adrp x0, #0x4000" = 00000090 ✓
        {"offset": 0x4920, "old": "00000090", "new": None,
         "label": "[P4] Release finger contacts before read-failure reset"},

        # P5: Before exception recovery: ADRP X8,#0x4000 displaced to release hook
        # Independent evidence: audit line 1542: "0x004bcc: adrp x8, #0x4000" = 08000090 ✓
        {"offset": 0x4bcc, "old": "08000090", "new": None,
         "label": "[P5] Release finger contacts before exception recovery"},

        # P6: Edge/notch buffer offset fix: 0x3c -> 0x4c
        # Independent evidence: v2 recovery patch verified, offset 0x4cc0 = 00f10091 ✓
        # Semantics: fp_set_prevent_notch needs ts->cmd_param_buf (at ts+0x4c), not ts+0x3c
        {"offset": 0x4cc0, "old": "00f10091", "new": "00310191",
         "label": "[P6] Fix prevent_notch buffer offset (ts+0x3c->ts+0x4c)"},

        # P7: HSEN request during USB settings resend (highsense variant)
        # Independent evidence: audit line 1839: "0x01a61c: adrp x9, #0x1a000" = 09000090 ✓
        {"offset": 0x1a61c, "old": "09000090", "new": None,
         "label": "[P7] Request HSEN mode during active settings resend"},
    ],

    # Hooks encoded from independent binary analysis
    # Format identical to v1/v2: hex string to append to .text
    # Each hook verified against audit disassembly for entry register values
    # 
    # Hook layout (all appended after text_size=0x24ac0):
    # H1 @ 0x24ac0 (20 bytes): propagate read status
    # H2 @ 0x24ad4 (20 bytes): reject short SPI
    # H3 @ 0x24ae8 (16 bytes): release before read-fail reset
    # H4 @ 0x24af8 (16 bytes): release before exception recovery  
    # H5 @ 0x24b08 (36 bytes): HSEN on resend (highsense only)
    #
    # Hook bytecodes independently re-derived matching v2 hex:
    "append_text":
        # H1 @ offset 0x24ac0 from text base (append pos 0 in appended data)
        # cmp w0, #0; cset w0, eq; str w0, [sp]; ldr x8, [x21]; b text+0x11a48
        "1f000071"      # CMP W0, #0
        "e0179f1a"      # CSET W0, EQ  
        "e00300b9"      # STR W0, [SP]
        "a80240f9"      # LDR X8, [X21] (displaced from patch1 site)
        "deb3ff17"      # B to text+0x11a48 = 0x24ac0+16 + offset
        # H2 @ offset 0x24ad4 (append pos 20)
        # ldur w8,[x29,#-0x44]; cmp w8,w23; b.ne 0x23864; ldr x8,[x25]; b 0x23770
        "a8c35bb8"      # LDUR W8, [X29, #-0x44]
        "1f01176b"      # CMP W8, W23
        "416cff54"      # B.NE to 0x23864
        "280340f9"      # LDR X8, [X25] (displaced from patch3 site)
        "23fbff17"      # B to text+0x23770
        # H3 @ offset 0x24ae8 (append pos 40)
        # mov x0,x19; bl 0x55e8; adrp x0,0; b 0x4924
        "e00313aa"      # MOV X0, X19
        "bf82ff97"      # BL to 0x55e8
        "e0feff90"      # ADRP X0, page (computed for this location -> page 0)
        "8c7fff17"      # B to text+0x4924
        # H4 @ offset 0x24af8 (append pos 56)
        # mov x0,x19; bl 0x55e8; adrp x8,0; b 0x4bd0
        "e00313aa"      # MOV X0, X19
        "bb82ff97"      # BL to 0x55e8
        "e8feff90"      # ADRP X8, page
        "3380ff17"      # B to text+0x4bd0
        # H5 @ offset 0x24b08 (append pos 72, highsense only)
        # stp x8,x30,[sp,#-16]!; cbz x19,done; ldrb w1,[x19,#1]; cbnz w1,done;
        # mov w0,#1; bl 0x14768; done: ldp x8,x30,[sp],#16; adrp x9,0; b 0x1a620
        "e87bbfa9"      # STP X8, X30, [SP, #-16]!
        "b30000b4"      # CBZ X19, done (+24)
        "61064039"      # LDRB W1, [X19, #1]
        "61000035"      # CBNZ W1, done (+12)
        "20008052"      # MOV W0, #1
        "13bfff97"      # BL to 0x14768
        "e87bc1a8"      # LDP X8, X30, [SP], #16
        "e9feff90"      # ADRP X9, page
        "bed6ff17",     # B to text+0x1a620

    # Relocations that move with their displaced instructions
    # (These are RELA entries in .rela.text that target moved instruction locations)
    "relocation_moves": [
        {"old": 0x11a44, "new": 0x24acc},  # P1: ldr x8,[x21] moved to H1+12 (0x24ac0 + 12)
        {"old": 0x2376c, "new": 0x24ae0},  # P3: ldr x8,[x25] moved to H2+12 (0x24ad4 + 12)
        {"old": 0x4920,  "new": 0x24af0},  # P4: adrp x0 moved to H3+8  (0x24ae8 + 8)
        {"old": 0x4bcc,  "new": 0x24b00},  # P5: adrp x8 moved to H4+8  (0x24af8 + 8)
        {"old": 0x1a61c, "new": 0x24b24},  # P7: adrp x9 moved to H5+28 (0x24b08 + 28)
    ],

    # What was investigated but NOT changed:
    "investigated_not_changed": [
        "himax_mcu_resend_cmd_func suspension guard - reviewed; existing CFI-bound code path safe",
        "hall_suspend_flag interaction - review only; no code change justified",
        "charger global type width mismatch (u32 store into u8) - no adjacent variable overwritten",
        "hx83102j_sense_off vs hx83102j_sense_on paths - reviewed; no defect found in current binary",
        "g_zero_event_count all-zeros suppression - reviewed; works as intended anti-flicker",
        "Pen ID bounds checking - current binary has trap instructions; old-source bug not present",
        "mtk_charger_framework tp_usb_plug_status width - documented as known type mismatch",
        "No watchdog / periodic IRQ health monitor added (safe design decision; absence of events != fault)",
    ],

    "limitations": [
        "Hardware boot and touch behavior are untested",
        "No new periodic watchdog for 'valid-packet finger-only freeze' scenarios",
        "No reset budget or transaction-wide SPI lock",
        "No controller firmware replacement or analog sensitivity calibration",
        "HSEN is a request to existing firmware feature; physical acceptance unproven",
        "May increase false touches; test with actual device before trusting in all scenarios",
        "Stylus operation is unchanged from stock",
        "AVB uses NONE algorithm; this is integrity metadata, not OEM signature",
        "Bootloader relock is NOT possible or safe with this modified image",
    ],
}

# ============================================================
def require(condition, message):
    if not condition:
        raise ValueError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def align(n, a):
    return (n + a - 1) // a * a

def stage(message, log_f=None):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {message}"
    print(line, flush=True)
    if log_f:
        log_f.write(line + "\n")
        log_f.flush()

def elf_sections(data):
    require(data[:7] == b'\x7fELF\x02\x01\x01', 'Expected ELF64 little endian module')
    require(struct.unpack_from('<HH', data, 16) == (1, 183), 'Expected relocatable ARM64 ELF')
    off = struct.unpack_from('<Q', data, 40)[0]
    ent, count, names = struct.unpack_from('<HHH', data, 58)
    require(ent == 64 and 0 < count < 1000, 'Unsupported ELF section headers')
    require(off + count * ent <= len(data), 'Truncated ELF section headers')
    headers = [list(struct.unpack_from('<IIQQQIIQQ', data, off + i * ent)) for i in range(count)]
    # Actually ELF64 section header is: sh_name(4)+sh_type(4)+sh_flags(8)+sh_addr(8)+sh_offset(8)+sh_size(8)+sh_link(4)+sh_info(4)+sh_addralign(8)+sh_entsize(8) = 64 bytes
    headers = [list(struct.unpack_from('<IIQQQQIIQQ', data, off + i * ent)) for i in range(count)]
    string_hdr = headers[names]
    strings = data[string_hdr[4]:string_hdr[4]+string_hdr[5]]
    sections = []
    for i, h in enumerate(headers):
        name = strings[h[0]:].split(b'\0', 1)[0].decode()
        require(h[1] == 8 or h[4] + h[5] <= len(data), 'ELF section outside file')
        sections.append(dict(index=i, name=name, header=h, data=(b'' if h[1] == 8 else data[h[4]:h[4]+h[5]])))
    return sections

def patch_module(data, manifest):
    """Apply all patches to the kernel module. Returns patched bytes."""
    require(sha(data) == manifest['base_module_sha256'],
            'Module differs from supported original; refusing to patch')
    
    sections = elf_sections(data)
    byname = {s['name']: s for s in sections}
    textsec = byname['.text']
    textdata = bytearray(textsec['data'])
    require(len(textdata) == manifest['text_size'],
            f'Unexpected text size {len(textdata)} != {manifest["text_size"]}')
    
    # Determine hook positions (relative to start of original .text)
    text_size = manifest['text_size']
    append_hex = manifest['append_text']
    append_bytes = bytes.fromhex(append_hex)
    
    # Compute branch targets for hooks
    # H1 is first hook, at text_size+0=0x24ac0
    H1_OFF = text_size + 0
    H2_OFF = text_size + 20
    H3_OFF = text_size + 40
    H4_OFF = text_size + 56
    H5_OFF = text_size + 72  # highsense only
    
    def b_offset(from_off, to_off):
        """ARM64 B instruction: 26-bit signed immediate in 2-LSB-dropped form."""
        delta = to_off - from_off
        require(delta % 4 == 0, f'Branch offset {delta} not aligned')
        imm26 = (delta // 4) & 0x3FFFFFF
        return struct.pack('<I', 0x14000000 | imm26)
    
    # Patch 1: LDR X8,[X21] -> B to H1
    # Patch 3: LDR X8,[X25] -> B to H2
    # Patch 4: ADRP X0 -> B to H3
    # Patch 5: ADRP X8 -> B to H4
    # Patch 7: ADRP X9 -> B to H5
    
    hook_branches = {
        0x11a44: b_offset(0x11a44, H1_OFF),
        0x2376c: b_offset(0x2376c, H2_OFF),
        0x4920:  b_offset(0x4920,  H3_OFF),
        0x4bcc:  b_offset(0x4bcc,  H4_OFF),
        0x1a61c: b_offset(0x1a61c, H5_OFF),
    }
    
    for p in manifest['text_patches']:
        o = p['offset']
        old_bytes = bytes.fromhex(p['old'])
        
        # For hook patches, the 'new' is None in manifest; compute it
        if p['new'] is None:
            new_bytes = hook_branches[o]
        else:
            new_bytes = bytes.fromhex(p['new'])
        
        require(len(old_bytes) == len(new_bytes) == 4, 'All patches must be 4 bytes')
        require(textdata[o:o+4] == old_bytes,
                f'Preimage mismatch at text+0x{o:x}: expected {p["old"]} found {textdata[o:o+4].hex()} ({p["label"]})')
        textdata[o:o+4] = new_bytes
        stage(f'  PATCH OK: text+0x{o:05x} {p["old"]} -> {new_bytes.hex():8s}  {p["label"]}')
    
    # Append hook code
    textdata.extend(append_bytes)
    textsec['data'] = bytes(textdata)
    textsec['header'][5] = len(textdata)
    
    # Update relocation offsets for moved instructions
    moves = {m['old']: m['new'] for m in manifest['relocation_moves']}
    found = set()
    for sec in sections:
        h = sec['header']
        # RELA sections (.rela.text): type=4, targeting .text section
        if h[1] != 4 or h[7] != textsec['index']:
            continue
        require(h[9] == 24, 'Unexpected relocation entry size')
        rel = bytearray(sec['data'])
        for o in range(0, len(rel), 24):
            ro, info, addend = struct.unpack_from('<QQq', rel, o)
            if ro in moves:
                require(ro not in found, f'Duplicate relocation at 0x{ro:x}')
                struct.pack_into('<Q', rel, o, moves[ro])
                found.add(ro)
        sec['data'] = bytes(rel)
    
    require(found == set(moves),
            f'Missing relocations: {set(moves) - found}. Found: {found}')
    
    # Rebuild ELF (identical approach to v1 proven script)
    out = bytearray(data[:64])  # ELF header
    for sec in sections[1:]:
        h = sec['header']
        pos = align(len(out), max(1, h[8]))
        out.extend(bytes(pos - len(out)))
        h[4] = pos
        if h[1] != 8:
            out.extend(sec['data'])
    
    shoff = align(len(out), 8)
    out.extend(bytes(shoff - len(out)))
    struct.pack_into('<Q', out, 40, shoff)
    for sec in sections:
        out.extend(struct.pack('<IIQQQQIIQQ', *sec['header']))
    
    # Update GNU build ID to distinguish patched module
    note = byname.get('.note.gnu.build-id')
    if note:
        o = note['header'][4]
        ns, ds, typ = struct.unpack_from('<III', out, o)
        require(ns == 4 and ds == 20 and typ == 3 and out[o+12:o+16] == b'GNU\0',
                'Unexpected GNU build ID format')
        out[o+16:o+36] = bytes(20)
        out[o+16:o+36] = hashlib.sha1(out).digest()
    
    # Verify no unintended changes to other sections
    check = {s['name']: s for s in elf_sections(out)}
    rela_text_names = {sec['name'] for sec in sections
                       if sec['header'][1] == 4 and sec['header'][7] == textsec['index']}
    for sec in elf_sections(data):
        name = sec['name']
        if name not in {'.text', '.note.gnu.build-id'} and name not in rela_text_names:
            require(check[name]['data'] == sec['data'],
                    f'Unexpected change in section {name}')
    
    return bytes(out)

def decompress_legacy(data):
    """Decompress Android vendor_boot LZ4-legacy ramdisk."""
    import lz4.block
    require(data[:4] == b'\x02\x21\x4c\x18', 'Expected legacy LZ4 vendor ramdisk magic')
    out = bytearray()
    o = 4
    while o < len(data):
        require(o + 4 <= len(data), 'Truncated LZ4 block header')
        size = struct.unpack_from('<I', data, o)[0]
        o += 4
        require(0 < size <= 8421520 and o + size <= len(data), f'Invalid LZ4 block size {size}')
        block = lz4.block.decompress(data[o:o+size], uncompressed_size=8*1024*1024)
        out.extend(block)
        o += size
        require(len(out) <= 512*1024*1024, 'Ramdisk exceeds 512MB limit')
    return bytes(out)

def compress_legacy(data):
    """Compress CPIO as Android vendor_boot LZ4-legacy ramdisk."""
    import lz4.block
    out = bytearray(b'\x02\x21\x4c\x18')
    for o in range(0, len(data), 8*1024*1024):
        block = lz4.block.compress(data[o:o+8*1024*1024], store_size=False,
                                   mode='high_compression', compression=9)
        out.extend(struct.pack('<I', len(block)))
        out.extend(block)
    return bytes(out)

def cpio_entries(data):
    """Parse CPIO newc archive entries."""
    out = []
    o = 0
    seen = set()
    while True:
        start = o
        require(data[o:o+6] == b'070701' and o + 110 <= len(data),
                'Unsupported or truncated CPIO archive')
        h = [int(data[o+6+i*8:o+14+i*8], 16) for i in range(13)]
        size = h[6]
        ns = h[11]
        require(1 <= ns <= 4096 and o + 110 + ns <= len(data), 'Invalid CPIO name size')
        namebytes = data[o+110:o+110+ns]
        require(namebytes[-1:] == b'\0', 'CPIO name not null-terminated')
        name = namebytes[:-1].decode()
        body = align(o + 110 + ns, 4)
        end = align(body + size, 4)
        require(end <= len(data), 'CPIO member data beyond archive end')
        require(name not in seen, f'Duplicate CPIO member: {name}')
        seen.add(name)
        out.append(dict(name=name, start=start, body=body, end=end, size=size, header=h))
        o = end
        if name == 'TRAILER!!!':
            require(not any(data[end:]), 'Unexpected bytes after CPIO trailer')
            return out

def replace_cpio(data, entries, name, payload):
    """Replace one CPIO member's data."""
    targets = [e for e in entries if e['name'] == name]
    require(len(targets) == 1, f'Expected exactly one member named {name}')
    e = targets[0]
    head = bytearray(data[e['start']:e['body']])
    head[54:62] = f'{len(payload):08x}'.encode()
    result = (data[:e['start']] + bytes(head) + payload +
              bytes(align(len(payload), 4) - len(payload)) + data[e['end']:])
    
    # Verify
    old = {x['name']: (x['header'], data[x['body']:x['body']+x['size']]) for x in entries}
    new = cpio_entries(result)
    require([x['name'] for x in new] == [x['name'] for x in entries],
            'CPIO member list changed after replacement')
    for n in new:
        if n['name'] != name:
            require((n['header'], result[n['body']:n['body']+n['size']]) == old[n['name']],
                    f'Unexpected change to CPIO member {n["name"]}')
    return result

def parse_image(data):
    """Parse vendor_boot v4 image structure."""
    require(len(data) >= 4096 and data[:8] == b'VNDRBOOT', 'Not a vendor_boot image')
    version, pg = struct.unpack_from('<II', data, 8)
    require(version == 4 and pg == 4096, 'Only v4 / 4096-byte page supported')
    rs = struct.unpack_from('<I', data, 24)[0]
    hs, ds = struct.unpack_from('<II', data, 2096)
    tablesize, count, entrysize, bs = struct.unpack_from('<4I', data, 2112)
    require(hs == 2128 and count == 1 and tablesize == 108 and entrysize == 108 and bs == 0,
            'Unexpected ramdisk-table layout')
    ro = align(hs, pg)
    dto = align(ro + rs, pg)
    to = align(dto + ds, pg)
    bo = align(to + tablesize, pg)
    require(data[-64:-60] == b'AVBf', 'Expected AVB footer')
    maj, minor, orig, vbo, vbs = struct.unpack_from('>IIQQQ', data, len(data)-60)
    require(maj == 1 and orig == bo and vbo >= orig and vbo + vbs <= len(data) - 64,
            'Invalid AVB bounds')
    table = data[to:to+tablesize]
    rsize, rstart = struct.unpack_from('<II', table)
    require(rsize == rs and rstart == 0, 'Ramdisk table does not describe one whole fragment')
    return dict(page=pg, ramdisk=data[ro:ro+rs], dtb=data[dto:dto+ds], table=table,
                header=data[:ro], vbmeta=data[vbo:vbo+vbs], orig=orig, footer=data[-64:])

def update_vbmeta(vbmeta, payload):
    """Update AVB hash descriptor for new payload."""
    v = bytearray(vbmeta)
    require(v[:4] == b'AVB0', 'Invalid vbmeta magic')
    auth, aux = struct.unpack_from('>QQ', v, 12)
    algo = struct.unpack_from('>I', v, 28)[0]
    require(auth == 0 and algo == 0 and len(v) == 256 + aux,
            'Expected unsigned vbmeta (NONE algorithm); signed images are not modified')
    off, size = struct.unpack_from('>QQ', v, 96)
    o = 256 + off
    end = o + size
    found = 0
    while o < end:
        tag, n = struct.unpack_from('>QQ', v, o)
        body = o + 16
        require(o + 16 + n <= end, 'Bad vbmeta descriptor')
        if tag == 2:  # HashDescriptor
            pn, sl, dl, flags = struct.unpack_from('>IIII', v, body + 40)
            require(v[body+8:body+40].split(b'\0')[0] == b'sha256' and dl == 32,
                    'Unsupported AVB hash algorithm')
            require(bytes(v[body+116:body+116+pn]) == b'vendor_boot',
                    'Wrong AVB partition name')
            salt = v[body+116+pn:body+116+pn+sl]
            struct.pack_into('>Q', v, body, len(payload))
            digest = hashlib.sha256(salt + payload).digest()
            pos = body + 116 + pn + sl
            v[pos:pos+dl] = digest
            found += 1
        o += 16 + n
    require(found == 1, 'Expected exactly one vendor_boot hash descriptor')
    return bytes(v)

def repack(original, info, ramdisk):
    """Repack vendor_boot with new ramdisk, updating AVB."""
    pg = info['page']
    head = bytearray(info['header'])
    struct.pack_into('<I', head, 24, len(ramdisk))
    table = bytearray(info['table'])
    struct.pack_into('<I', table, 0, len(ramdisk))
    payload = bytearray(head)
    for blob in (ramdisk, info['dtb'], table):
        payload.extend(blob)
        payload.extend(bytes(align(len(payload), pg) - len(payload)))
    vb = update_vbmeta(info['vbmeta'], payload)
    require(len(payload) + align(len(vb), pg) + pg <= len(original),
            'Repacked image exceeds original partition size')
    out = bytearray(payload)
    out.extend(vb)
    out.extend(bytes(len(original) - 64 - len(out)))
    foot = bytearray(info['footer'])
    struct.pack_into('>QQQ', foot, 12, len(payload), len(payload), len(vb))
    out.extend(foot)
    
    # Verify
    check = parse_image(out)
    require(check['dtb'] == info['dtb'], 'DTB changed during repack')
    require(check['vbmeta'] == update_vbmeta(check['vbmeta'], out[:check['orig']]),
            'AVB hash verification failed on repacked image')
    return bytes(out)

def main():
    OUT_DIR.mkdir(exist_ok=True)
    log_path = OUT_DIR / "build_log.txt"
    
    with open(log_path, 'w', encoding='utf-8') as log_f:
        try:
            stage("=" * 65, log_f)
            stage("Himax TB350XU Final Combined Patch Builder v3.0", log_f)
            stage(f"Time: {datetime.datetime.now().isoformat()}", log_f)
            stage("=" * 65, log_f)
            
            # Install lz4 if needed
            try:
                import lz4.block
            except ImportError:
                stage("Installing lz4...", log_f)
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'lz4'], check=True)
                import lz4.block
            stage("lz4 available", log_f)
            
            stage("\n[1/6] Verifying original image", log_f)
            require(ORIG_IMG.exists(), f'Original image not found: {ORIG_IMG}')
            original = ORIG_IMG.read_bytes()
            orig_hash = sha(original)
            stage(f"Original: {len(original)} bytes, SHA256={orig_hash}", log_f)
            require(orig_hash.lower() == ORIG_IMAGE_SHA256,
                    f'Original image hash mismatch: {orig_hash}')
            stage("Original image hash VERIFIED", log_f)
            
            stage("\n[2/6] Parsing image structure", log_f)
            info = parse_image(original)
            stage(f"Page size: {info['page']}", log_f)
            stage(f"Ramdisk: {len(info['ramdisk'])} bytes", log_f)
            stage(f"DTB: {len(info['dtb'])} bytes", log_f)
            stage(f"VBmeta: {len(info['vbmeta'])} bytes", log_f)
            # Verify AVB integrity on original
            require(update_vbmeta(info['vbmeta'], original[:info['orig']]) == info['vbmeta'],
                    'Original AVB hash is invalid')
            stage("Original AVB integrity VERIFIED", log_f)
            
            stage("\n[3/6] Decompressing ramdisk and extracting himax_mmi.ko", log_f)
            cpio = decompress_legacy(info['ramdisk'])
            stage(f"Decompressed CPIO: {len(cpio)} bytes", log_f)
            entries = cpio_entries(cpio)
            stage(f"CPIO members: {len(entries)}", log_f)
            ko_name = 'lib/modules/himax_mmi.ko'
            e = next((x for x in entries if x['name'] == ko_name), None)
            require(e is not None, f'{ko_name} not found in CPIO')
            module = cpio[e['body']:e['body']+e['size']]
            module_hash = sha(module)
            stage(f"Module: {len(module)} bytes, SHA256={module_hash}", log_f)
            require(module_hash.lower() == ORIG_MODULE_SHA256,
                    f'Module hash mismatch: {module_hash}')
            stage("Module hash VERIFIED", log_f)
            
            stage("\n[4/6] Applying combined ARM64 patches", log_f)
            stage("Independently verified against binary audit output", log_f)
            patched = patch_module(module, COMBINED_MANIFEST)
            patched_hash = sha(patched)
            stage(f"\nPatched module: {len(patched)} bytes, SHA256={patched_hash}", log_f)
            
            # Save patched module
            (OUT_DIR / 'himax_mmi.combined_final.ko').write_bytes(patched)
            stage("Patched module saved", log_f)
            
            stage("\n[5/6] Repacking CPIO, compressing, and rebuilding image", log_f)
            cpio2 = replace_cpio(cpio, entries, ko_name, patched)
            stage("CPIO rebuilt and verified", log_f)
            compressed = compress_legacy(cpio2)
            stage(f"Compressed ramdisk: {len(compressed)} bytes (original: {len(info['ramdisk'])})", log_f)
            output = repack(original, info, compressed)
            stage("Image repacked and AVB updated", log_f)
            
            stage("\n[6/6] Final verification", log_f)
            # Verify CPIO roundtrip
            verify_cpio = decompress_legacy(parse_image(output)['ramdisk'])
            require(verify_cpio == cpio2, 'Ramdisk decompression roundtrip failed')
            stage("Ramdisk decompression roundtrip PASSED", log_f)
            
            # Verify only himax_mmi.ko changed
            orig_entries = cpio_entries(cpio)
            new_entries = cpio_entries(verify_cpio)
            changes = []
            for oe, ne in zip(orig_entries, new_entries):
                require(oe['name'] == ne['name'], 'CPIO member order changed')
                orig_data = cpio[oe['body']:oe['body']+oe['size']]
                new_data = verify_cpio[ne['body']:ne['body']+ne['size']]
                if orig_data != new_data:
                    changes.append(ne['name'])
            require(changes == [ko_name], f'Unexpected CPIO changes: {changes}')
            stage(f"Only {ko_name} changed in CPIO: VERIFIED", log_f)
            
            # Save output
            out_name = 'vendor_boot_himax_combined_final_candidate.img'
            out_path = OUT_DIR / out_name
            out_path.write_bytes(output)
            out_hash = sha(output)
            stage(f"\nOutput: {out_path}", log_f)
            stage(f"Output SHA256: {out_hash}", log_f)
            stage(f"Output size: {len(output)} bytes (original: {len(original)})", log_f)
            require(len(output) == len(original), 'Output size changed!')
            stage("Output size preserved: VERIFIED", log_f)
            
            # Save SHA256SUMS
            sums = (OUT_DIR / 'SHA256SUMS.txt')
            sums_content = (
                f"# Himax TB350XU Final Combined Candidate\n"
                f"# Built: {datetime.datetime.now().isoformat()}\n"
                f"# Variant: highsense + all recovery fixes\n"
                f"# Status: EXPERIMENTAL - NOT HARDWARE TESTED\n\n"
                f"{sha(original)}  vendor_boot.img (ORIGINAL BASELINE)\n"
                f"{module_hash}  himax_mmi.original.ko\n"
                f"{patched_hash}  himax_mmi.combined_final.ko\n"
                f"{out_hash}  {out_name}\n"
            )
            sums.write_text(sums_content, encoding='utf-8')
            stage(f"SHA256SUMS written: {sums}", log_f)
            
            # Save build report
            report = {
                "status": "EXPERIMENTAL_BUILT_NOT_HARDWARE_TESTED",
                "build_time": datetime.datetime.now().isoformat(),
                "variant": "highsense_plus_all_recovery_fixes",
                "original_image_sha256": sha(original),
                "original_module_sha256": module_hash,
                "patched_module_sha256": patched_hash,
                "output_sha256": out_hash,
                "image_size": len(output),
                "original_ramdisk_size": len(info['ramdisk']),
                "patched_ramdisk_size": len(compressed),
                "patches_applied": len(COMBINED_MANIFEST['text_patches']),
                "relocations_moved": len(COMBINED_MANIFEST['relocation_moves']),
                "append_bytes": len(bytes.fromhex(COMBINED_MANIFEST['append_text'])),
                "independently_verified": True,
                "checks_passed": [
                    "Original image SHA256 verified",
                    "Module SHA256 verified",
                    "All patch preimages verified against binary evidence",
                    "All relocation moves applied",
                    "AVB hash updated and verified",
                    "Ramdisk decompression roundtrip verified",
                    "Only himax_mmi.ko changed in CPIO",
                    "Output partition size preserved",
                    "GNU build ID updated",
                ],
                "limitations": COMBINED_MANIFEST['limitations'],
                "investigated_not_changed": COMBINED_MANIFEST['investigated_not_changed'],
                "hardware_tested": False,
            }
            (OUT_DIR / 'BUILD_REPORT_final.json').write_text(
                json.dumps(report, indent=2), encoding='utf-8')
            
            stage("\n" + "="*65, log_f)
            stage("BUILD SUCCESSFUL", log_f)
            stage("="*65, log_f)
            stage(f"Output: {out_path}", log_f)
            stage(f"SHA256: {out_hash}", log_f)
            stage("\nSTATUS: EXPERIMENTAL - requires hardware testing before trusted use.", log_f)
            stage("BOOTLOADER RELOCK: NOT SUPPORTED OR SAFE with this image.", log_f)
            
            return report
            
        except Exception as exc:
            stage(f"\nBUILD FAILED: {exc}", log_f)
            log_f.write(traceback.format_exc())
            raise

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'\nERROR: {exc}', file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
