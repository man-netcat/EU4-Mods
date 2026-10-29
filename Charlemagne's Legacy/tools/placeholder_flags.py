#!/usr/bin/env python3
"""Placeholder flags in the style of the base game's missing flag: the tag's colour on one diagonal, black on the other.

    python3 tools/placeholder_flags.py            # write gfx/flags/<TAG>.tga for every tag and formable that has none

Never overwrites: a baked or hand-made flag (or an earlier placeholder) is kept, so replace a placeholder by deleting
it or dropping the real flag over it. 256x256, 24bpp, uncompressed.
"""
import os
import sqlite3
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
FLAGS = os.path.join(HERE, "..", "gfx", "flags")
SIZE = 256


def tga(color):
    r, g, b = color
    rows = []
    for y in range(SIZE):  # top row first (origin bit 0x20)
        rows.append(b"".join(bytes((b, g, r)) if x + y < SIZE else b"\0\0\0" for x in range(SIZE)))
    return struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, SIZE, SIZE, 24, 0x20) + b"".join(rows)


def main():
    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    rows = list(con.execute("select tag, color_r, color_g, color_b from tags")) + \
        list(con.execute("select tag, color_r, color_g, color_b from formables"))
    made = []
    for tag, r, g, b in sorted(rows):
        p = os.path.join(FLAGS, f"{tag}.tga")
        if os.path.exists(p) or r is None:
            continue
        open(p, "wb").write(tga((r, g, b)))
        made.append(tag)
    print(f"placeholder flags written: {', '.join(made) or 'none'}")


if __name__ == "__main__":
    main()
