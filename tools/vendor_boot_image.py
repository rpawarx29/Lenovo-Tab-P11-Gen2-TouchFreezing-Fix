#!/usr/bin/env python3
"""Minimal Android vendor_boot v4, LZ4-legacy, CPIO newc, AVB, and ELF64 utilities."""

import hashlib
import struct


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def align(n: int, a: int) -> int:
    return (n + a - 1) // a * a


def elf_sections(data: bytes) -> list[dict]:
    require(data[:7] == b"\x7fELF\x02\x01\x01", "Expected ELF64 little-endian kernel module")
    require(struct.unpack_from("<HH", data, 16) == (1, 183), "Expected relocatable ARM64 ELF")
    off = struct.unpack_from("<Q", data, 40)[0]
    ent, count, names = struct.unpack_from("<HHH", data, 58)
    require(ent == 64 and 0 < count < 1000, "Unsupported ELF section headers")
    require(off + count * ent <= len(data), "Truncated ELF section headers")
    headers = [list(struct.unpack_from("<IIQQQQIIQQ", data, off + i * ent)) for i in range(count)]
    string_hdr = headers[names]
    strings = data[string_hdr[4] : string_hdr[4] + string_hdr[5]]
    sections = []
    for i, h in enumerate(headers):
        name = strings[h[0] :].split(b"\0", 1)[0].decode()
        require(h[1] == 8 or h[4] + h[5] <= len(data), "ELF section outside file")
        sections.append(
            dict(
                index=i,
                name=name,
                header=h,
                data=(b"" if h[1] == 8 else data[h[4] : h[4] + h[5]]),
            )
        )
    return sections


def decompress_legacy(data: bytes) -> bytes:
    import lz4.block

    require(data[:4] == b"\x02\x21\x4c\x18", "Expected legacy LZ4 vendor ramdisk magic")
    out = bytearray()
    o = 4
    while o < len(data):
        require(o + 4 <= len(data), "Truncated LZ4 block header")
        size = struct.unpack_from("<I", data, o)[0]
        o += 4
        require(0 < size <= 8421520 and o + size <= len(data), f"Invalid LZ4 block size {size}")
        out.extend(lz4.block.decompress(data[o : o + size], uncompressed_size=8 * 1024 * 1024))
        o += size
        require(len(out) <= 512 * 1024 * 1024, "Ramdisk exceeds 512MB limit")
    return bytes(out)


def compress_legacy(data: bytes) -> bytes:
    import lz4.block

    out = bytearray(b"\x02\x21\x4c\x18")
    for o in range(0, len(data), 8 * 1024 * 1024):
        block = lz4.block.compress(
            data[o : o + 8 * 1024 * 1024],
            store_size=False,
            mode="high_compression",
            compression=9,
        )
        out.extend(struct.pack("<I", len(block)))
        out.extend(block)
    return bytes(out)


def cpio_entries(data: bytes) -> list[dict]:
    out = []
    o = 0
    seen = set()
    while True:
        start = o
        require(data[o : o + 6] == b"070701" and o + 110 <= len(data), "Unsupported or truncated CPIO archive")
        h = [int(data[o + 6 + i * 8 : o + 14 + i * 8], 16) for i in range(13)]
        size = h[6]
        ns = h[11]
        require(1 <= ns <= 4096 and o + 110 + ns <= len(data), "Invalid CPIO name size")
        namebytes = data[o + 110 : o + 110 + ns]
        require(namebytes[-1:] == b"\0", "CPIO name not null-terminated")
        name = namebytes[:-1].decode()
        body = align(o + 110 + ns, 4)
        end = align(body + size, 4)
        require(end <= len(data), "CPIO member data beyond archive end")
        require(name not in seen, f"Duplicate CPIO member: {name}")
        seen.add(name)
        out.append(dict(name=name, start=start, body=body, end=end, size=size, header=h))
        o = end
        if name == "TRAILER!!!":
            require(not any(data[end:]), "Unexpected bytes after CPIO trailer")
            return out


def replace_cpio(data: bytes, entries: list[dict], name: str, payload: bytes) -> bytes:
    targets = [e for e in entries if e["name"] == name]
    require(len(targets) == 1, f"Expected exactly one member named {name}")
    e = targets[0]
    head = bytearray(data[e["start"] : e["body"]])
    head[54:62] = f"{len(payload):08x}".encode()
    result = (
        data[: e["start"]]
        + bytes(head)
        + payload
        + bytes(align(len(payload), 4) - len(payload))
        + data[e["end"] :]
    )
    old = {x["name"]: (x["header"], data[x["body"] : x["body"] + x["size"]]) for x in entries}
    new = cpio_entries(result)
    require([x["name"] for x in new] == [x["name"] for x in entries], "CPIO member list changed")
    for n in new:
        if n["name"] != name:
            require((n["header"], result[n["body"] : n["body"] + n["size"]]) == old[n["name"]], f"CPIO drift: {n['name']}")
    return result


def parse_image(data: bytes) -> dict:
    require(len(data) >= 4096 and data[:8] == b"VNDRBOOT", "Not a vendor_boot image")
    version, pg = struct.unpack_from("<II", data, 8)
    require(version == 4 and pg == 4096, "Only vendor_boot v4 (4096-byte page) supported")
    rs = struct.unpack_from("<I", data, 24)[0]
    hs, ds = struct.unpack_from("<II", data, 2096)
    tablesize, count, entrysize, bs = struct.unpack_from("<4I", data, 2112)
    require(hs == 2128 and count == 1 and tablesize == 108 and entrysize == 108 and bs == 0, "Unexpected ramdisk table")
    ro = align(hs, pg)
    dto = align(ro + rs, pg)
    to = align(dto + ds, pg)
    bo = align(to + tablesize, pg)
    require(data[-64:-60] == b"AVBf", "Expected AVB footer")
    maj, _minor, orig, vbo, vbs = struct.unpack_from(">IIQQQ", data, len(data) - 60)
    require(maj == 1 and orig == bo and vbo >= orig and vbo + vbs <= len(data) - 64, "Invalid AVB bounds")
    table = data[to : to + tablesize]
    rsize, rstart = struct.unpack_from("<II", table)
    require(rsize == rs and rstart == 0, "Unexpected fragmented ramdisk table")
    return dict(
        page=pg,
        ramdisk=data[ro : ro + rs],
        dtb=data[dto : dto + ds],
        table=table,
        header=data[:ro],
        vbmeta=data[vbo : vbo + vbs],
        orig=orig,
        footer=data[-64:],
    )


def update_vbmeta(vbmeta: bytes, payload: bytes) -> bytes:
    v = bytearray(vbmeta)
    require(v[:4] == b"AVB0", "Invalid vbmeta magic")
    auth, aux = struct.unpack_from(">QQ", v, 12)
    algo = struct.unpack_from(">I", v, 28)[0]
    require(auth == 0 and algo == 0 and len(v) == 256 + aux, "Expected unsigned AVB vbmeta footer")
    off, size = struct.unpack_from(">QQ", v, 96)
    o = 256 + off
    end = o + size
    found = 0
    while o < end:
        tag, n = struct.unpack_from(">QQ", v, o)
        body = o + 16
        require(o + 16 + n <= end, "Bad vbmeta descriptor")
        if tag == 2:
            pn, sl, dl, _flags = struct.unpack_from(">IIII", v, body + 40)
            require(v[body + 8 : body + 40].split(b"\0")[0] == b"sha256" and dl == 32, "Unsupported AVB hash")
            require(bytes(v[body + 116 : body + 116 + pn]) == b"vendor_boot", "Wrong AVB partition name")
            salt = v[body + 116 + pn : body + 116 + pn + sl]
            struct.pack_into(">Q", v, body, len(payload))
            digest = hashlib.sha256(salt + payload).digest()
            pos = body + 116 + pn + sl
            v[pos : pos + dl] = digest
            found += 1
        o += 16 + n
    require(found == 1, "Expected exactly one vendor_boot hash descriptor")
    return bytes(v)


def repack(original: bytes, info: dict, ramdisk: bytes) -> bytes:
    pg = info["page"]
    head = bytearray(info["header"])
    struct.pack_into("<I", head, 24, len(ramdisk))
    table = bytearray(info["table"])
    struct.pack_into("<I", table, 0, len(ramdisk))
    payload = bytearray(head)
    for blob in (ramdisk, info["dtb"], table):
        payload.extend(blob)
        payload.extend(bytes(align(len(payload), pg) - len(payload)))
    vb = update_vbmeta(info["vbmeta"], payload)
    require(len(payload) + align(len(vb), pg) + pg <= len(original), "Repacked image exceeds partition size")
    out = bytearray(payload)
    out.extend(vb)
    out.extend(bytes(len(original) - 64 - len(out)))
    foot = bytearray(info["footer"])
    struct.pack_into(">QQQ", foot, 12, len(payload), len(payload), len(vb))
    out.extend(foot)

    check = parse_image(out)
    require(check["dtb"] == info["dtb"], "DTB changed during repack")
    require(check["vbmeta"] == update_vbmeta(check["vbmeta"], out[: check["orig"]]), "AVB verification failed")
    return bytes(out)
