"""Placeholder flags for the tags the mod adds: gfx/flags/<TAG>.tga, 128x128, drawn from the tag's EU5 colour.

EU5's coats of arms are layered emblems the text files cannot render, so each new tag gets a plain heraldic field
(two colours, one of eight divisions) chosen from a hash of its tag: distinct enough to tell nations apart on the map
and in the interface until proper flags replace them. Files that already exist are left alone, so a hand-made or
baked flag is never overwritten.
"""
import hashlib
import struct

SIZE = 128


def _tone(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def _second(c, h):
    """A colour that reads against the field: white or gold on dark fields, black or deep red on light ones."""
    lum = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
    light = [(245, 245, 245), (225, 190, 60)] if lum < 110 else [(25, 25, 25), (140, 20, 30)]
    return light[h % 2] if lum < 200 else (30, 30, 30)


def pattern(tag, color):
    h = int(hashlib.md5(tag.encode()).hexdigest(), 16)
    color = tuple(max(0, min(255, int(round(v)))) for v in color)
    base, alt = color, _second(color, h >> 8)
    kind = h % 8
    px = []
    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            u, v = x / SIZE, y / SIZE
            if kind == 0:
                c = alt if v > 0.5 else base
            elif kind == 1:
                c = alt if u > 0.5 else base
            elif kind == 2:
                c = alt if abs(u - 0.5) < 0.12 or abs(v - 0.5) < 0.12 else base
            elif kind == 3:
                c = alt if abs(u - v) < 0.11 or abs(u + v - 1) < 0.11 else base
            elif kind == 4:
                c = alt if (u > 0.5) != (v > 0.5) else base
            elif kind == 5:
                c = alt if u + v > 1 else base
            elif kind == 6:
                c = alt if 0.3 < v < 0.7 else base
            else:
                c = alt if (u - 0.5) ** 2 + (v - 0.5) ** 2 < 0.06 else base
            row.append(c)
        px.append(row)
    return px


def tga(px):
    head = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, SIZE, SIZE, 24, 0x20)
    return head + b"".join(bytes((b, g, r)) for row in px for r, g, b in row)


def write(dest, colors):
    """colors: {tag: (r, g, b)}; returns how many files were written."""
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for tag, color in sorted(colors.items()):
        p = dest / f"{tag}.tga"
        if not p.exists():
            p.write_bytes(tga(pattern(tag, color)))
            n += 1
    return n
