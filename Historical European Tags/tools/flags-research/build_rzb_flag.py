#!/usr/bin/env python3
"""build_rzb_flag.py - RZB (Ratzeburg) banner flag.

Design (user-specified, 2026-08-27):
- Per pale: gold field left, blue field right. "Blue castle on gold, gold
  staff on blue".
- The full blue castle is centred exactly at the flag centre (128,128).
  An opaque blue overlay covers the right half, so exactly half the castle
  stays visible on the gold half. This is by design.
- The gold staff (mod-standard 230 px tall, keeping the SVG proportions)
  is centred in the right half (x=192).
- Both charges scale together (one global factor).

Compositing detail: each charge is pasted over its own field colour at FULL
render resolution, and only then downscaled as an opaque RGB image. Downscaling
the raw RGBA crops instead would blend the transparent edges against black,
which reads as a black background around the charges on the finished flag.

Layers used from RZB_Ratzeburg.svg: layer 1 (castle group) and layer 3 (staff
group). The field polygons (layers 0 and 2) and the black shield outline
(layer 4) are not used. The charges keep their black outlines.

Output: the mod's byte-exact EU4 TGA v2 flag (256x256, type 2 uncompressed
truecolor 24-bit, 196652 bytes, TRUEVISION footer identical to the existing
mod flags).

Usage:
  python3 tools/flags-research/build_rzb_flag.py            # install to gfx/flags/RZB.tga
  python3 tools/flags-research/build_rzb_flag.py -o out.tga # write elsewhere
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
SOURCE = os.path.join(MOD_ROOT, "tools", "flags-research", "svg-sources", "RZB_Ratzeburg.svg")
DEFAULT_OUT = os.path.join(MOD_ROOT, "gfx", "flags", "RZB.tga")

GOLD = (242, 188, 81)     # Or - exact mod palette value = SVG fill #F2BC51
BLUE = (13, 103, 147)     # Azure - exact mod palette value = SVG fill #0D6793
SS = 4                    # supersample: 1 viewBox unit = SS render px
VIEWBOX = (-10.0, 119.55, 820.0, 952.0)
CHARGE_H = 230            # mod-standard charge height (px, final flag scale)


def ensure_deps():
    """Re-exec inside the private venv with cairosvg+pillow if imports fail."""
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
    svg = re.sub(r"<!DOCTYPE.*?\]>", "", svg, flags=re.S)  # Adobe entity block
    svg = re.sub(r"&(ns_\w+);", "urn:x", svg)              # entity references in attrs
    return svg


def main_group(svg):
    """Return the main artwork group under the switch (i:extraneous="self")."""
    root = ET.fromstring(svg)
    switches = [c for c in root if c.tag.split("}")[-1] == "switch"]
    if not switches:
        sys.exit("no <switch> element found")
    for switch in switches:
        for sub in switch:
            attrs = {k.split("}")[-1]: v for k, v in sub.attrib.items()}
            if attrs.get("extraneous") == "self":
                return list(sub)
    sys.exit("no main group (extraneous=self) found")


def render(inner):
    v0, v1, vw, vh = VIEWBOX
    w, h = int(vw * SS), int(vh * SS)
    doc = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="%s %s %s %s">%s</svg>') % (w, h, v0, v1, vw, vh, inner)
    png = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    cairosvg.svg2png(bytestring=doc.encode(), write_to=png,
                     output_width=w, output_height=h,
                     background_color="rgba(0,0,0,0)")
    im = Image.open(png).convert("RGBA")
    os.unlink(png)
    return im


def opaque_bbox(im):
    """Alpha bounding box using only pixels with a > 60 (skips AA fringe)."""
    mask = im.getchannel("A").point(lambda a: 255 if a > 60 else 0)
    return mask.getbbox()


def composite_over(im, bg):
    """Blend an RGBA image over a solid colour (no transparent-black edges)."""
    base = Image.new("RGB", im.size, bg)
    base.paste(im, (0, 0), im)
    return base


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
    p = argparse.ArgumentParser(description="RZB (Ratzeburg) banner flag")
    p.add_argument("-o", "--out", default=DEFAULT_OUT, help="output TGA path")
    p.add_argument("--source", default=SOURCE, help="source SVG path")
    args = p.parse_args()

    svg = load_svg(args.source)
    children = main_group(svg)
    assert len(children) == 5, f"expected 5 top-level layers, found {len(children)}"

    # Layer 1 = the castle group, layer 3 = the staff group. The other layers
    # (gold field, blue field, shield outline) are not part of this design.
    castle = render(ET.tostring(children[1], encoding="unicode"))
    staff = render(ET.tostring(children[3], encoding="unicode"))

    cb = opaque_bbox(castle)
    sb = opaque_bbox(staff)
    if cb is None or sb is None:
        sys.exit("castle or staff layer rendered empty")

    # One global scale: the staff (the tallest element) is CHARGE_H px tall.
    # The castle keeps its SVG-relative proportions. Compose each charge over
    # its own field colour BEFORE downscaling, so the edges stay clean.
    k = CHARGE_H / ((sb[3] - sb[1]) / SS)        # comp px per viewBox unit
    cw = round((cb[2] - cb[0]) * k * SS / SS)    # comp px
    ch = round((cb[3] - cb[1]) * k * SS / SS)
    sw = round((sb[2] - sb[0]) * k * SS / SS)
    sh = round((sb[3] - sb[1]) * k * SS / SS)
    print(f"castle: {cw // SS}x{ch // SS}, staff: {sw // SS}x{sh // SS}, scale {k:.4f}")

    # Compose at 4x (1024x1024), then downscale to 256 once. Left half gold,
    # right half blue. The castle bbox centre lands exactly on (128,128).
    C = SS * 256
    comp = Image.new("RGB", (C, C), GOLD)
    comp.paste(Image.new("RGB", (C // 2, C), BLUE), (C // 2, 0))

    castle_c = composite_over(castle.crop(cb), GOLD).resize((cw, ch), Image.LANCZOS)
    comp.paste(castle_c, (round((C - cw) / 2), round((C - ch) / 2)))

    # Opaque blue overlay on the right half: obscures exactly half the castle.
    comp.paste(Image.new("RGB", (C // 2, C), BLUE), (C // 2, 0))

    # Staff: centred in the right half (x=192), vertically centred like the
    # castle (y=128).
    staff_c = composite_over(staff.crop(sb), BLUE).resize((sw, sh), Image.LANCZOS)
    comp.paste(staff_c, (round(192 * SS - sw / 2), round(128 * SS - sh / 2)))

    flag = comp.resize((256, 256), Image.LANCZOS)
    flag.save(args.out)

    size, img_type, depth, ok = tga_check(args.out)
    print(f"saved {args.out}")
    print(f"  {size} bytes, type {img_type}, {depth}-bit, footer matches LGN: {ok}")
    if not ok:
        sys.exit("TGA header check FAILED - expected 196652 bytes, type 2, 24-bit, LGN footer")


if __name__ == "__main__":
    main()