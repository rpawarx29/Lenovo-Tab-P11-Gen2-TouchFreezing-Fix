#!/usr/bin/env python3
"""Packages magisk_module/ into a deterministic LF-normalized flashable ZIP."""

import argparse
import hashlib
import pathlib
import zipfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MOD_DIR = REPO_ROOT / "magisk_module"
DEFAULT_OUT = REPO_ROOT / "releases" / "tb350xu-s231018-touch-fix.zip"


def build_zip(mod_dir: pathlib.Path, out_zip: pathlib.Path) -> str:
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in mod_dir.rglob("*") if p.is_file())
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            rel = p.relative_to(mod_dir).as_posix()
            raw = p.read_bytes().replace(b"\r\n", b"\n")
            txt = raw.decode("utf-8")
            for ln in txt.splitlines():
                s = ln.strip()
                if not s or s.startswith("#") or s.startswith("ui_print"):
                    continue
                low = s.lower()
                assert "vibrator" not in low, f"Refusing vibrator edit in {rel}: {s}"
                assert "min_refresh_rate" not in low and "peak_refresh_rate" not in low, f"Refusing forced RR in {rel}: {s}"
            zi = zipfile.ZipInfo(rel, date_time=(2026, 11, 25, 0, 0, 0))
            zi.external_attr = (0o755 if rel.endswith(".sh") else 0o644) << 16
            zf.writestr(zi, raw)
    digest = hashlib.sha256(out_zip.read_bytes()).hexdigest()
    print(f"[+] Built {out_zip} ({out_zip.stat().st_size} bytes, SHA256={digest})")
    return digest


def main() -> None:
    ap = argparse.ArgumentParser(description="Build APatch/Magisk/KSU touch module ZIP")
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT, help="Output ZIP path")
    args = ap.parse_args()
    build_zip(MOD_DIR, args.out)


if __name__ == "__main__":
    main()
