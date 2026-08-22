#!/usr/bin/env python3
"""Compose a EU4 flag from an Azgaar Armoria charge SVG.

Charges live in the Armoria clone (public/charges/*.svg). They are drawn on a
200x200 box with a root fill (primary tincture) and optional path classes
"secondary" / "tertiary" that carry their own tinctures at render time.

Usage:
  armoria_flag.py --charge eagleTwoHeads --primary 188,46,46 \
      --bg 242,188,81 -o FRB.tga [--secondary R,G,B] [--tertiary R,G,B]
      [--margin 0.82] [--size 256]
"""
import argparse
import re
import sys
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image

PARADOX_ROOT = Path("/home/rick/Paradox")
CHARGES_DIR = PARADOX_ROOT / "heraldry" / "Armoria" / "public" / "charges"


def hexify(rgb):
    r, g, b = (int(v) for v in rgb.split(","))
    return f"#{r:02x}{g:02x}{b:02x}"


def load_charge(name):
    path = CHARGES_DIR / f"{name}.svg"
    if not path.exists():
        avail = sorted(p.stem for p in CHARGES_DIR.glob("*.svg"))
        sys.exit(f"unknown charge '{name}'. Close matches: "
                 f"{[a for a in avail if name[:5] in a][:8]}")
    return path.read_text()


def apply_tinctures(svg, primary, secondary=None, tertiary=None):
    svg = re.sub(r'(<svg[^>]*?)\bfill="[^"]*"', rf'\1fill="{primary}"', svg, count=1)
    if secondary:
        svg = re.sub(r'(<path\b[^>]*?\bclass="secondary"[^>]*?)\s*/>',
                     rf'\1 fill="{secondary}"/>', svg)
        svg = re.sub(r'(<path\b(?![^>]*\bclass=)[^>]*?)\s*/>', r'\1/>', svg)
        svg = re.sub(r'(class=")(secondary)(")', r"\1\2\3", svg)
    return svg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--charge", required=True)
    ap.add_argument("--primary", required=True, help="R,G,B")
    ap.add_argument("--secondary", help="R,G,B")
    ap.add_argument("--tertiary", help="R,G,B")
    ap.add_argument("--bg", required=True, help="R,G,B field colour")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--margin", type=float, default=0.82,
                    help="charge fits into size*margin box")
    args = ap.parse_args()

    p = hexify(args.primary)
    sec = hexify(args.secondary) if args.secondary else None
    ter = hexify(args.tertiary) if args.tertiary else None
    svg = load_charge(args.charge)

    # set explicit fills per class before rendering
    def fill_class(match, hexcolor):
        tag = match.group(0)
        if 'fill="' in tag:
            tag = re.sub(r'fill="[^"]*"', f'fill="{hexcolor}"', tag)
        else:
            tag = tag.replace("<path ", f'<path fill="{hexcolor}" ', 1)
        return tag

    svg = re.sub(r'<path\b[^>]*\bclass="secondary"[^>]*>',
                 lambda m: fill_class(m, sec or p), svg)
    svg = re.sub(r'<path\b[^>]*\bclass="tertiary"[^>]*>',
                 lambda m: fill_class(m, ter or sec or p), svg)

    S = args.size
    SS = 4  # supersample: rasterize the vector big, then downsample once
    png = Path("/tmp/opencode/_armoria_tmp.png")
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(png),
                     output_width=S * SS, output_height=S * SS, unsafe=True,
                     background_color="rgba(0,0,0,0)")
    charge = Image.open(png).convert("RGBA")

    bbox = np.array(charge)[..., 3] > 8
    ys, xs = np.where(bbox)
    charge = charge.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))

    bg = tuple(int(v) for v in args.bg.split(","))
    flag = Image.new("RGB", (S, S), bg)
    box = round(S * args.margin)
    sc = min(box / charge.width, box / charge.height)
    charge = charge.resize((round(charge.width * sc), round(charge.height * sc)),
                           Image.LANCZOS)
    flag.paste(charge, ((S - charge.width) // 2, (S - charge.height) // 2), charge)
    flag.save(args.out)
    print(f"saved {args.out} ({S}x{S}, charge {charge.width}x{charge.height})")


if __name__ == "__main__":
    main()
