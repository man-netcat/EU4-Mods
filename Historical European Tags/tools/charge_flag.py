#!/usr/bin/env python3
"""charge_flag.py - build a plain-field EU4 flag from a WappenWiki SVG.

Produces the mod's "charge on plain field" style: no shield shape and no black
outline. The flag is the field colour with only the charge pasted on it.

Workflow
--------
1. Strip the Adobe DOCTYPE/entity block from the SVG.
2. Split the SVG into layers by top-level <g id=...> groups.
3. Identify the charge: the layer that is NOT the field/shield. The field is
   the full-screen region; the charge is the shape(s) drawn on top of it.
   (Select it by layer id, or pass --charge-id to choose it by hand.)
4. Render only the charge at high resolution.
5. Remove the black outline: set near-black pixels to transparent, so the
   charge is a clean solid shape on the plain field.
6. Crop to the charge alpha bbox, scale to 0.9*c (230 px for a 256 canvas),
   and paste x-centred at the mod position (8 px below centre, y=21).
7. Fill the rest with the field colour (auto-detected, or --bg R,G,B).

The field colour is the most common opaque colour of the FULL render (shield
included), or you can force it with --bg.

Approved on 2026-08-27: flags use a plain field with the charge, no shield
outline. See tools/FLAG_NOTES.md.

Examples
--------
  # Worms: auto-detect azure field, charge = Layer_2 (the white key)
  charge_flag.py Worms.svg -o WRM.tga --charge-id Layer_2

  # force a different field colour
  charge_flag.py Some.svg -o NAM.tga --charge-id Layer_2 --bg 188,46,46

Requires cairosvg + pillow (bootstraps its own venv, like svg2flag.py).
"""

import os
import re
import sys
import subprocess
import argparse
import tempfile

VENV = os.path.expanduser("~/.local/share/svg2flag/venv")


def ensure_deps():
    try:
        import cairosvg  # noqa: F401
        import PIL  # noqa: F401
        return
    except ImportError:
        pass
    if not os.path.exists(os.path.join(VENV, "bin", "python")):
        subprocess.run([sys.executable, "-m", "venv", VENV], check=True)
        subprocess.run(
            [os.path.join(VENV, "bin", "pip"), "install", "-q", "cairosvg", "pillow"],
            check=True,
        )
    os.execv(os.path.join(VENV, "bin", "python"), [VENV + "/bin/python", __file__] + sys.argv[1:])


ensure_deps()

import cairosvg  # noqa: E402
from PIL import Image  # noqa: E402


def extract_tag(s, tag, attr, idval):
    """Return the substring of a balanced <tag id=idval>...</tag>, inclusive."""
    m = re.search(r'<' + tag + r'\b[^>]*\b' + attr + r'="' + re.escape(idval) + r'"[^>]*>', s)
    if not m:
        return None
    start = m.end()
    depth = 1
    i = start
    while depth > 0 and i < len(s):
        nxt = re.search(r'<' + tag + r'\b[^>]*>|</' + tag + r'>', s[i:], re.S)
        if not nxt:
            break
        if nxt.group(0).startswith('</'):
            depth -= 1
        else:
            depth += 1
        i += nxt.end()
    return s[m.start():i]


def load_svg(source):
    with open(source, "rb") as f:
        data = f.read()
    svg = data.decode("utf-8", errors="replace")
    svg = re.sub(r"<!DOCTYPE.*?\]>", "", svg, flags=re.S)
    svg = re.sub(r"&(ns_\w+);", "urn:x", svg)
    return svg


def root_attrs(svg):
    """Return the root <svg ...> opening tag attributes with namespace URIs."""
    m = re.search(r"<svg\b([^>]*)>", svg, re.S)
    if not m:
        return ""
    tag = m.group(1)
    # keep only xmlns/version/width/height/viewBox declarations we need
    keep = []
    for name in ["xmlns:dc", "xmlns:cc", "xmlns:rdf", "xmlns:svg",
                 "xmlns:sodipodi", "xmlns:inkscape", "xmlns:xlink",
                 "xmlns:i", "xmlns:x", "xmlns:graph", "version"]:
        mm = re.search(r'\b' + re.escape(name) + r'="[^"]*"', tag)
        if mm:
            keep.append(mm.group(0))
    return " ".join(keep)


def svg_inner(svg):
    """Return the content between the root <svg>...</svg> tags (no wrapper)."""
    m = re.search(r"<svg\b[^>]*>(.*)</svg>", svg, re.S)
    if not m:
        return svg
    return m.group(1)


def viewbox(svg):
    m = re.search(r'viewBox="([\d.\-]+)[ ,]+([\d.\-]+)[ ,]+([\d.\-]+)[ ,]+([\d.\-]+)"', svg)
    if not m:
        sys.exit("no viewBox found")
    return list(map(float, m.groups()))


def render(inner, ns, vx, vy, vw, vh, w, h):
    png = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    doc = ('<svg xmlns="http://www.w3.org/2000/svg" %s viewBox="%s %s %s %s" '
           'width="%d" height="%d">%s</svg>') % (ns, vx, vy, vw, vh, w, h, inner)
    cairosvg.svg2png(bytestring=doc.encode(), write_to=png,
                     output_width=w, output_height=h, background_color="rgba(0,0,0,0)")
    im = Image.open(png).convert("RGBA")
    os.unlink(png)
    return im


def dominant_colour(im):
    rgb = Image.new("RGB", im.size, (255, 255, 255))
    rgb.paste(im, mask=im.getchannel("A"))
    counts = rgb.getcolors(maxcolors=1 << 24)
    counts.sort(reverse=True)
    return counts[0][1]


def remove_black(im, threshold=40):
    """Set near-black opaque pixels (the outline) to transparent."""
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0 and max(r, g, b) < threshold:
                px[x, y] = (r, g, b, 0)
    return im


def main():
    p = argparse.ArgumentParser(description="plain-field charge flag from WappenWiki SVG")
    p.add_argument("source")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--charge-id", nargs="+", default=[],
                   help="layer/group id(s) holding the charge (repeatable). If empty, "
                        "auto-pick the layer with the smallest alpha bbox area.")
    p.add_argument("--bg", default="auto", help="'auto' or R,G,B field colour")
    p.add_argument("--size", type=int, default=256)
    p.add_argument("--ss", type=int, default=4, help="supersample factor")
    p.add_argument("--keep-outline", action="store_true",
                   help="keep the charge's black outline (off by default)")
    p.add_argument("--height-fraction", type=float, default=0.9,
                   help="charge height as a fraction of the canvas (Trieste-style ~0.80)")
    p.add_argument("--center", action="store_true",
                   help="centre the charge vertically (default: mod's 8px downward bias)")
    args = p.parse_args()

    svg = load_svg(args.source)
    vx, vy, vw, vh = viewbox(svg)
    NS = root_attrs(svg)
    W, H = int(vw * args.ss), int(vh * args.ss)

    # field colour from full render (shield included)
    full = render(svg_inner(svg), NS, vx, vy, vw, vh, W, H)
    bg = dominant_colour(full) if args.bg == "auto" else tuple(int(c) for c in args.bg.split(","))
    print(f"field colour: {bg}")

    # pick the charge layer(s)
    layer_ids = re.findall(r'<g\s+[^>]*\bid="([^"]+)"', svg)
    if not args.charge_id:
        # auto-pick: layer whose alpha bbox is smallest (the charge), skip full-area
        best, best_area = None, None
        for lid in layer_ids:
            sub = extract_tag(svg, "g", "id", lid)
            if sub is None:
                continue
            bbox = render(sub, NS, vx, vy, vw, vh, W, H).getchannel("A").getbbox()
            if bbox is None:
                continue
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            if best_area is None or area < best_area:
                best, best_area = lid, area
        if best is None:
            sys.exit("could not auto-pick a charge layer; use --charge-id")
        print(f"auto-picked charge layer: {best}")
        args.charge_id = [best]

    charge_inner = "".join(
        extract_tag(svg, "g", "id", lid) for lid in args.charge_id if extract_tag(svg, "g", "id", lid)
    )
    if not charge_inner:
        sys.exit("no charge layer found; check --charge-id")
    charge = render(charge_inner, NS, vx, vy, vw, vh, W, H)
    if not args.keep_outline:
        charge = remove_black(charge)

    bbox = charge.getchannel("A").getbbox()
    if bbox is None:
        sys.exit("charge render is empty")
    charge = charge.crop(bbox)

    target_h = round(args.size * args.height_fraction)
    w, h = charge.size
    charge = charge.resize((max(1, round(w * target_h / h)), target_h), Image.LANCZOS)
    if args.center:
        y = (args.size - target_h) // 2
    else:
        y = (args.size - target_h) // 2 + 8
    flag = Image.new("RGB", (args.size, args.size), bg)
    flag.paste(charge, ((args.size - charge.width) // 2, y), charge)
    flag.save(args.out)
    print(f"saved {args.out} ({charge.width}x{target_h} at y={y}, "
          f"top gap {y}, bottom gap {args.size - y - target_h})")


if __name__ == "__main__":
    main()
