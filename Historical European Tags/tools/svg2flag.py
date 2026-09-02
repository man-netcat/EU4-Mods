#!/usr/bin/env python3
"""svg2flag.py - turn a WappenWiki-style heraldic SVG into a 256x256 EU4 flag TGA.

Method: strip Adobe DOCTYPE/entities, optionally drop the shield/field shapes
by id, rasterize the remaining charge on transparency at high resolution,
crop to its alpha bounding box, scale to fit a square with a small margin,
and paste it centered on the field colour.

The field colour is auto-detected as the most common colour of the FULL
render (shield included), or set explicitly with --bg R,G,B.

Examples:
  # lion only, gold background auto-detected from the SVG's own field
  svg2flag.py Von_Katzenelnbogen.svg -o KZN.tga --drop-id polygon9

  # charge on a forced sable field
  svg2flag.py Some.svg -o NAM.tga --drop-id polygon9 --bg 51,51,51

  # keep everything (no id drops), just crop+square the whole shield
  svg2flag.py Mark.svg -o MKR.tga

Requires: cairosvg + pillow. The script bootstraps its own venv on first run.
"""

import os
import re
import sys
import subprocess
import argparse
import tempfile
import urllib.request

VENV = os.path.expanduser("~/.local/share/svg2flag/venv")


def ensure_deps():
    """Re-exec inside a private venv with cairosvg+pillow if imports fail."""
    try:
        import cairosvg  # noqa: F401
        import PIL  # noqa: F401
        return
    except ImportError:
        pass
    if not os.path.exists(os.path.join(VENV, "bin", "python")):
        print("bootstrapping venv at", VENV, file=sys.stderr)
        subprocess.run([sys.executable, "-m", "venv", VENV], check=True)
        subprocess.run(
            [os.path.join(VENV, "bin", "pip"), "install", "-q", "cairosvg", "pillow"],
            check=True,
        )
    os.execv(os.path.join(VENV, "bin", "python"), [VENV + "/bin/python", __file__] + sys.argv[1:])


ensure_deps()

import cairosvg  # noqa: E402
from PIL import Image  # noqa: E402


def load_svg(source: str) -> str:
    if source.startswith(("http://", "https://")):
        # curl first (handles redirects/TLS quirks), urllib as fallback
        try:
            data = subprocess.run(
                ["curl", "-sfL", source], check=True, capture_output=True
            ).stdout
        except (FileNotFoundError, subprocess.CalledProcessError):
            req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as r:
                data = r.read()
    else:
        with open(source, "rb") as f:
            data = f.read()
    svg = data.decode("utf-8", errors="replace")
    svg = re.sub(r"<!DOCTYPE.*?\]>", "", svg, flags=re.S)  # Adobe entity block
    svg = re.sub(r"&(ns_\w+);", "urn:x", svg)              # entity references in attrs
    return svg


def render(svg: str, width: int, height: int) -> Image.Image:
    png = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    cairosvg.svg2png(
        bytestring=svg.encode(), write_to=png,
        output_width=width, output_height=height,
        background_color="rgba(0,0,0,0)",
    )
    im = Image.open(png).convert("RGBA")
    os.unlink(png)
    return im


def dominant_colour(im: Image.Image) -> tuple:
    """Most common opaque colour = the heraldic field."""
    rgb = Image.new("RGB", im.size, (255, 255, 255))
    rgb.paste(im, mask=im.getchannel("A"))
    counts = rgb.getcolors(maxcolors=1 << 24)
    counts.sort(reverse=True)
    return counts[0][1]


def drop_ids(svg: str, ids: list) -> str:
    for el_id in ids:
        # remove the element carrying this id, whatever the tag
        pat = rf'<(\w+)\b[^>]*\bid="{re.escape(el_id)}"[^>]*>.*?</\1>|<\w+\b[^>]*\bid="{re.escape(el_id)}"[^>]*/>'
        svg, n = re.subn(pat, "", svg, flags=re.S)
        if n == 0:
            print(f"warning: no element with id '{el_id}' found", file=sys.stderr)
    return svg


def drop_indexes(svg: str, indexes: list) -> str:
    """Remove shapes by 1-based document order among <polygon>/<path>/<rect> elements.
    WappenWiki exports draw the shield first, so index 1 is usually the field."""
    pat = re.compile(r"<(?:polygon|path|rect)\b[^>]*?(?:/>|>.*?</(?:polygon|path|rect)>)", re.S)
    hits = list(pat.finditer(svg))
    for n in sorted(indexes, reverse=True):
        if 1 <= n <= len(hits):
            m = hits[n - 1]
            svg = svg[:m.start()] + svg[m.end():]
        else:
            print(f"warning: no shape at index {n} (found {len(hits)})", file=sys.stderr)
    return svg


def main():
    p = argparse.ArgumentParser(description="SVG charge -> square EU4 flag TGA")
    p.add_argument("source", help="SVG file path or URL")
    p.add_argument("-o", "--out", required=True, help="output .tga path")
    p.add_argument("--drop-id", action="append", default=[],
                   help="element id to remove before rendering (repeatable), e.g. the shield polygon")
    p.add_argument("--drop-index", type=int, action="append", default=[],
                   help="1-based document-order shape index to remove (repeatable); 1 = usually the shield")
    p.add_argument("--bg", default="auto",
                   help="'auto' (most common colour of full render) or R,G,B")
    p.add_argument("--size", type=int, default=256)
    p.add_argument("--margin", type=float, default=0.80,
                   help="fraction of the square the charge may fill (WappenWiki reference: ~0.80)")
    p.add_argument("--ss", type=int, default=4, help="supersample factor")
    p.add_argument("--full-bleed", action="store_true",
                   help="stretch the whole shield to fill the square; charges that reach "
                        "the shield edge then span the full flag (like WappenWiki mod flags)")
    p.add_argument("--assembly", action="store_true",
                   help="mod standard mode: crop the full artwork bbox, scale to 0.9*size "
                        "height, paste x-centred at --y-offset (see tools/FLAG_NOTES.md)")
    p.add_argument("--y-offset", type=int, default=None,
                   help="vertical paste offset for --assembly (default: 8 px below centre, "
                        "the approved in-game position)")
    p.add_argument("--viewbox", default=None,
                   help="override viewBox as W,H if the SVG lacks one")
    args = p.parse_args()

    svg = load_svg(args.source)
    m = re.search(r'viewBox="([\d.\-]+)[ ,]+([\d.\-]+)[ ,]+([\d.\-]+)[ ,]+([\d.\-]+)"', svg)
    if args.viewbox:
        vx, vy, vw, vh = map(float, args.viewbox.split(","))
    elif m:
        vx, vy, vw, vh = map(float, m.groups())
    else:
        sys.exit("no viewBox found; pass --viewbox W,H")
    W, H = vw * args.ss, vh * args.ss

    # 1) field colour from the untouched artwork
    if args.bg == "auto":
        bg = dominant_colour(render(svg, W, H))
    else:
        bg = tuple(int(c) for c in args.bg.split(","))
    print(f"field colour: {bg}")

    # 2) whole-artwork assembly (mod standard, see FLAG_NOTES.md)
    if args.assembly:
        art = render(svg, W, H)
        bbox = art.getchannel("A").getbbox()
        if bbox is None:
            sys.exit("render is empty")
        art = art.crop(bbox)
        target_h = round(args.size * 0.9)
        w, h = art.size
        art = art.resize((max(1, round(w * target_h / h)), target_h), Image.LANCZOS)
        y = args.y_offset if args.y_offset is not None else (args.size - target_h) // 2 + 8
        flag = Image.new("RGB", (args.size, args.size), bg)
        flag.paste(art, ((args.size - art.width) // 2, y), art)
        flag.save(args.out)
        print(f"saved {args.out} ({art.width}x{target_h} at y={y}, "
              f"top gap {y}, bottom gap {args.size - y - target_h})")
        return

    # 3) charge only
    if args.full_bleed:
        shield = render(svg, W, H)
        bbox = shield.getchannel("A").getbbox()
        shield.crop(bbox).resize((args.size, args.size), Image.LANCZOS).save(args.out)
        print(f"saved {args.out} ({args.size}x{args.size}, full bleed)")
        return
    charge_svg = drop_ids(svg, args.drop_id)
    charge_svg = drop_indexes(charge_svg, args.drop_index)
    charge = render(charge_svg, W, H)
    bbox = charge.getchannel("A").getbbox()
    if bbox is None:
        sys.exit("charge render is empty - check --drop-id")
    charge = charge.crop(bbox)

    # 3) fit into the square, paste centred
    S, M = args.size, round(args.size * args.margin)
    w, h = charge.size
    sc = min(M / w, M / h)
    charge = charge.resize((round(w * sc), round(h * sc)), Image.LANCZOS)
    flag = Image.new("RGB", (S, S), bg)
    flag.paste(charge, ((S - charge.width) // 2, (S - charge.height) // 2), charge)
    flag.save(args.out)
    print(f"saved {args.out} ({S}x{S})")


if __name__ == "__main__":
    main()
