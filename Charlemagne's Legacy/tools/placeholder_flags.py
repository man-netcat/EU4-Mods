#!/usr/bin/env python3
"""Placeholder flags in the style of the base game's missing flag: the tag's colour on one diagonal, black on the other.

    python3 tools/placeholder_flags.py            # write gfx/flags/<TAG>.tga for every tag and formable that has none
    python3 tools/placeholder_flags.py --list     # list every flag that looks like a placeholder

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


def is_placeholder(path):
    """True when the file is one flat colour on the upper-left diagonal and black on the other (our placeholder,
    whoever wrote it); a baked or hand-made flag never has that shape."""
    d = open(path, "rb").read()
    if len(d) != 18 + SIZE * SIZE * 3 or d[2] != 2 or struct.unpack("<HH", d[12:16]) != (SIZE, SIZE):
        return False
    px = d[18:]

    def at(x, y):
        i = (y * SIZE + x) * 3
        return px[i:i + 3]

    col = at(0, 0)
    if col == b"\0\0\0":
        return False
    return all(at(x, y) == (col if x + y < SIZE else b"\0\0\0")
               for y in range(0, SIZE, 7) for x in range(0, SIZE, 7))


def placeholders():
    return sorted(f[:-4] for f in os.listdir(FLAGS) if f.endswith(".tga") and is_placeholder(os.path.join(FLAGS, f)))


def main():
    import sys
    if "--list" in sys.argv:
        found = placeholders()
        print(f"{len(found)} placeholder flags: {', '.join(found)}")
        return
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
