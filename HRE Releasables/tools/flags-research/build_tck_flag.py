#!/usr/bin/env python3
"""build_tck_flag.py - TCK (County of Tecklenburg) plain-field flag.

Blazon: argent, three water-lily leaves gules. Source TCK_Tecklemburg.svg.
This is the historic arms of the county (1139-1247 origin), correct for the
1444 start. The quartered Tecklenburg-Lingen arms are post-1493 and are NOT
used.

SVG structure (Inkscape export, no Adobe switch):
  svg -> g#g844 (translate 10,178.7) -> [g#g4 (white field polygon + black
  stroke), path#path6, path#path8, path#path10 (the three red leaves)].

The mod style is plain field + charge: solid Argent canvas, the three leaves
form one charge scaled to the mod-standard 230 px height, placed 8 px below
geometric centre (y = 21). The black strokes on the SVG (shield outline and
leaf outlines) are removed: near-black pixels become transparent, then the
leaves are composited over Argent at full resolution so the edges stay clean
after the single downscale.

Output: the mod's byte-exact EU4 TGA v2 flag (256x256, type 2 uncompressed
truecolor 24-bit, 196652 bytes, TRUEVISION footer identical to the existing
mod flags). Installs as gfx/flags/TCK.tga.

Usage:
  python3 tools/flags-research/build_tck_flag.py
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

VENV = os.path.expanduser("~/.local/share/svg2flag/venv")

MOD_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SOURCE = os.path.join(MOD_ROOT, "tools", "flags-research", "svg-sources", "TCK_Tecklemburg.svg")
DEFAULT_OUT = os.path.join(MOD_ROOT, "gfx", "flags", "TCK.tga")

ARGENT = (246, 246, 246)     # mod palette = SVG fill #f6f6f6
GULES = (188, 46, 46)        # mod palette = SVG fill #bc2e2e
SS = 4                       # supersample: 1 viewBox unit = SS render px
CHARGE_H = 230               # mod-standard charge height (px, final flag scale)
Y = 21                       # mod position: 8 px below geometric centre


def ensure_deps():
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


def load_svg(path):
    with open(path, "rb") as f:
        data = f.read()
    svg = data.decode("utf-8", errors="replace")
    svg = re.sub(r"<!DOCTYPE.*?\]>", "", svg, flags=re.S)
    svg = re.sub(r"&(ns_\w+);", "urn:x", svg)
    return svg


def local(tag):
    return tag.split("}")[-1]


def render(inner, vx, vy, vw, vh):
    w, h = int(vw * SS), int(vh * SS)
    doc = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="%s %s %s %s">%s</svg>') % (w, h, vx, vy, vw, vh, inner)
    png = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    cairosvg.svg2png(bytestring=doc.encode(), write_to=png,
                     output_width=w, output_height=h,
                     background_color="rgba(0,0,0,0)")
    im = Image.open(png).convert("RGBA")
    os.unlink(png)
    return im


def opaque_bbox(im):
    mask = im.getchannel("A").point(lambda a: 255 if a > 60 else 0)
    return mask.getbbox()


def remove_black(im, threshold=40):
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0 and max(r, g, b) < threshold:
                px[x, y] = (r, g, b, 0)
    return im


def composite_over(im, bg):
    base = Image.new("RGB", im.size, bg)
    base.paste(im, (0, 0), im)
    return base


def tga_check(path):
    data = open(path, "rb").read()
    ref = open(os.path.join(MOD_ROOT, "gfx", "flags", "LGN.tga"), "rb").read()
    size = len(data)
    img_type = data[2]
    depth = data[16]
    footer_ok = size == 196652 and img_type == 2 and depth == 24 and data[-26:] == ref[-26:]
    return size, img_type, depth, footer_ok


def main():
    p = argparse.ArgumentParser(description="TCK (Tecklenburg) plain-field flag")
    p.add_argument("-o", "--out", default=DEFAULT_OUT, help="output TGA path")
    p.add_argument("--source", default=SOURCE, help="source SVG path")
    args = p.parse_args()

    svg = load_svg(args.source)
    root = ET.fromstring(svg)
    vb = [float(x) for x in root.attrib["viewBox"].split()]
    vx, vy, vw, vh = vb

    container = [c for c in root if local(c.tag) == "g"]
    assert len(container) == 1, f"expected 1 top-level group, found {len(container)}"
    container = container[0]
    kids = list(container)
    assert len(kids) == 4, f"expected 4 children under the container, found {len(kids)}"
    field_g, *leaf_paths = kids
    assert local(field_g.tag) == "g", "first child must be the white field group"
    for lp in leaf_paths:
        assert local(lp.tag) == "path", "leaf elements must be bare paths"
        assert "bc2e2e" in lp.attrib.get("style", ""), "leaf fill must be gules #bc2e2e"

    # The leaves sit inside g844 which carries transform="translate(10,178.7)".
    # Preserve it, or the render clips the leaf tops at the viewBox edge.
    transform = container.attrib.get("transform")
    assert transform, "container group must carry the translate transform"
    inner = ('<g transform="%s">%s</g>' % (
        transform, "".join(ET.tostring(c, encoding="unicode") for c in leaf_paths)))
    leaves = render(inner, vx, vy, vw, vh)
    leaves = remove_black(leaves)
    bb = opaque_bbox(leaves)
    if bb is None:
        sys.exit("leaf render is empty")
    crop = leaves.crop(bb)
    print(f"leaves bbox: ({bb[0] / SS:.0f},{bb[1] / SS:.0f})-({bb[2] / SS:.0f},{bb[3] / SS:.0f})")

    scale = CHARGE_H * SS / (bb[3] - bb[1])
    cw = round((bb[2] - bb[0]) * scale)
    ch = round((bb[3] - bb[1]) * scale)
    leaf_c = composite_over(crop, ARGENT).resize((cw, ch), Image.LANCZOS)
    print(f"charge: {cw // SS}x{ch // SS} px (final)")

    C = SS * 256
    comp = Image.new("RGB", (C, C), ARGENT)
    comp.paste(leaf_c, (round((C - cw) / 2), round(Y * SS - (SS * CHARGE_H - ch) / 2)))
    flag = comp.resize((256, 256), Image.LANCZOS)
    flag.save(args.out)

    size, img_type, depth, ok = tga_check(args.out)
    print(f"saved {args.out}")
    print(f"  {size} bytes, type {img_type}, {depth}-bit, footer matches LGN: {ok}")
    if not ok:
        sys.exit("TGA header check FAILED - expected 196652 bytes, type 2, 24-bit, LGN footer")

    px = flag.load()
    near_black = sum(1 for y in range(256) for x in range(256)
                     if max(px[x, y]) < 40)
    gules = sum(1 for y in range(256) for x in range(256)
                if abs(px[x, y][0] - GULES[0]) < 8 and abs(px[x, y][1] - GULES[1]) < 8
                and abs(px[x, y][2] - GULES[2]) < 8)
    argent = sum(1 for y in range(256) for x in range(256)
                 if abs(px[x, y][0] - ARGENT[0]) < 8 and abs(px[x, y][1] - ARGENT[1]) < 8
                 and abs(px[x, y][2] - ARGENT[2]) < 8)
    print(f"  palette: argent {argent}px ({argent / 65536 * 100:.0f}%), "
          f"gules {gules}px ({gules / 65536 * 100:.0f}%), near-black {near_black}px")


if __name__ == "__main__":
    main()