#!/usr/bin/env python3
"""VBT (Vasterbotten) flag.

Source charge: /home/rick/Downloads/Vasterbotten_1660.svg (background-free,
golden running reindeer with silver accents and black outlines, content
bbox 693x751, aspect 0.923).

Arms: azure field, golden running reindeer (1660 version). Field azure =
(13,103,147), the exact blue used by the mod's WRM flag (Wermland), which
itself is the WappenWiki blue. Proportions mirror WRM: the charge is fully
centered on both axes.

Charge: 153x166 at (52,45), side margins 52/51 and top/bottom 45/45; height
166 keeps the source aspect (693x751, 0.9228) so the reindeer is not
distorted.
"""

import io
import os

import cairosvg
import numpy as np
from PIL import Image

ROOT = "/home/rick/.local/share/Paradox Interactive/Europa Universalis IV/mod/Historical European Tags"
SRC = "/home/rick/Downloads/Västerbotten_1660.svg"
OUT = os.path.join(ROOT, "gfx/flags/VBT.tga")

FIELD = (13, 103, 147)    # WappenWiki azure (matches WRM.tga)
TOP, LEFT, W, H = 45, 52, 153, 166
SIZE = 256


def main() -> None:
    svg = open(SRC, encoding="utf-8").read()
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=820,
                           output_height=952, unsafe=True)
    im = np.array(Image.open(io.BytesIO(png)).convert("RGBA"))
    a = im[:, :, 3] > 0
    ys, xs = np.where(a)
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    crop = im[y0:y1, x0:x1]
    rgba = Image.fromarray(crop, "RGBA")

    # premultiplied-alpha resize into the target box
    ch = rgba.resize((W, H), Image.LANCZOS)
    ca = np.array(ch).astype(np.float32) / 255.0
    alpha = ca[..., 3:4]
    rgb = ca[..., :3]

    canvas = np.zeros((SIZE, SIZE, 3), np.float32)
    canvas[:] = np.array(FIELD, dtype=np.float32) / 255.0
    y0c, x0c = TOP, LEFT
    canvas[y0c:y0c + H, x0c:x0c + W] = (canvas[y0c:y0c + H, x0c:x0c + W]
                                        * (1 - alpha) + rgb * alpha)

    Image.fromarray(np.clip(canvas * 255, 0, 255).astype(np.uint8)).save(
        OUT)
    print("written", OUT)


if __name__ == "__main__":
    main()