#!/usr/bin/env python3
"""build_dph_flag.py - DPH (Diepholz) flag.

Design (user-specified, 2026-08-27):
- Top half: the top 128 rows of URW.tga (Utrecht flag from this mod's
  gfx/flags).
- Bottom half: FER.tga (Ferrara, from the WappenWiki Custom flag pack),
  scaled to 256x128. Squishing is intentional.

Output: the mod's byte-exact EU4 TGA v2 flag (256x256, type 2 uncompressed
truecolor 24-bit, 196652 bytes, TRUEVISION footer identical to the existing
mod flags). Installs as gfx/flags/DPH.tga.

Usage:
  python3 tools/flags-research/build_dph_flag.py
"""

import argparse
import os
import sys

import cairosvg  # noqa: F401  (kept: this folder's pipeline always uses the venv)
from PIL import Image

MOD_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
URW_SRC = os.path.join(MOD_ROOT, "gfx", "flags", "URW.tga")
FER_SRC = os.path.join("/home/rick/Paradox/Mods/Europa Universalis IV",
                       "WappenWiki Flags for EUIV - Custom", "gfx", "flags", "FER.tga")
DEFAULT_OUT = os.path.join(MOD_ROOT, "gfx", "flags", "DPH.tga")


def tga_check(path):
    """Compare the trailing 26 bytes against a known-good mod flag footer."""
    data = open(path, "rb").read()
    ref = open(os.path.join(MOD_ROOT, "gfx", "flags", "LGN.tga"), "rb").read()
    size = len(data)
    img_type = data[2]
    depth = data[16]
    footer_ok = size == 196652 and img_type == 2 and depth == 24 and data[-26:] == ref[-26:]
    return size, img_type, depth, footer_ok


def main():
    p = argparse.ArgumentParser(description="DPH (Diepholz) flag")
    p.add_argument("-o", "--out", default=DEFAULT_OUT, help="output TGA path")
    args = p.parse_args()

    urw = Image.open(URW_SRC).convert("RGB")
    fer = Image.open(FER_SRC).convert("RGB")
    assert urw.size == fer.size == (256, 256), f"unexpected source size: {urw.size}, {fer.size}"

    top = urw.crop((0, 0, 256, 128))
    bottom = fer.resize((256, 128), Image.LANCZOS)

    flag = Image.new("RGB", (256, 256))
    flag.paste(top, (0, 0))
    flag.paste(bottom, (0, 128))
    flag.save(args.out)

    size, img_type, depth, ok = tga_check(args.out)
    print(f"saved {args.out}")
    print(f"  {size} bytes, type {img_type}, {depth}-bit, footer matches LGN: {ok}")
    if not ok:
        sys.exit("TGA header check FAILED - expected 196652 bytes, type 2, 24-bit, LGN footer")


if __name__ == "__main__":
    main()