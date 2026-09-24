#!/usr/bin/env python3
"""HLS (Halsingland) flag.

Source charge: /home/rick/Downloads/Halsingland.svg (background-free,
the Halsingland goat, gold/red/black/white, content 595x802, aspect 0.742).

Field = black (51,51,51), the exact field black of the mod's VID.tga.
Layout mirrors VID: charge box 167x198 at (44,28); the goat is fit inside
that box preserving aspect (147x198 at (54,28)).
"""

import io
import os

import cairosvg
import numpy as np
from PIL import Image

ROOT = "/home/rick/.local/share/Paradox Interactive/Europa Universalis IV/mod/Historical European Tags"
SRC = "/home/rick/Downloads/Hälsingland.svg"
OUT = os.path.join(ROOT, "gfx/flags/HLS.tga")

FIELD = (51, 51, 51)      # VID.tga black
BOX_L, BOX_T, BOX_W, BOX_H = 44, 28, 167, 198
SIZE = 256


def main() -> None:
    svg = open(SRC, encoding="utf-8", errors="replace").read()
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=820,
                           output_height=952, unsafe=True)
    im = np.array(Image.open(io.BytesIO(png)).convert("RGBA"))
    a = im[:, :, 3] > 0
    ys, xs = np.where(a)
    crop = im[int(ys.min()):int(ys.max()) + 1, int(xs.min()):int(xs.max()) + 1]
    ch = Image.fromarray(crop, "RGBA")

    src_w, src_h = ch.size
    scale = min(BOX_W / src_w, BOX_H / src_h)
    w = round(src_w * scale)
    h = round(src_h * scale)
    left = BOX_L + (BOX_W - w) // 2
    top = BOX_T + (BOX_H - h) // 2
    print(f"charge {w}x{h} at ({left},{top})")

    ch = ch.resize((w, h), Image.LANCZOS)
    ca = np.array(ch).astype(np.float32) / 255.0
    alpha = ca[..., 3:4]
    rgb = ca[..., :3]

    canvas = np.zeros((SIZE, SIZE, 3), np.float32)
    canvas[:] = np.array(FIELD, dtype=np.float32) / 255.0
    canvas[top:top + h, left:left + w] = (
        canvas[top:top + h, left:left + w] * (1 - alpha) + rgb * alpha)

    Image.fromarray(np.clip(canvas * 255, 0, 255).astype(np.uint8)).save(
        OUT)
    print("written", OUT)


if __name__ == "__main__":
    main()