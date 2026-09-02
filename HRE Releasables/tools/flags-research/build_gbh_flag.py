#!/usr/bin/env python3
"""build_gbh_flag.py - GBH (Grubenhagen) flag, 1444-correct arms.

The user chose a per fess layout: the Brunswick arms fill the whole top band,
with two quarters below.

Layout:
  Top band:        Braunschweig, gules, two lions passant guardant or
  Bottom-left:     Everstein, azure, a lion rampant argent crowned or
  Bottom-right:    Homburg, within a bordure compony azure and argent,
                   gules, a lion rampant or

The armorial contents come from the quarterly arms the Grubenhagen line bore
after the fall of Everstein (1408) and Homburg (1409) to the Welfen (Heinrich
III 1437-1464, Albrecht II co-regent from 1441). The full quarterly also
carried the Lüneburg quarter (or, semy of hearts azure-lion) which the user
replaced with the Brunswick two-lions across the top. The 5-field Schildfuß
variant with Lauterberg appears only from 1593, not in 1444.

Sources:
  Top:      BRU.tga (WappenWiki Flags for EUIV - Custom mod), top half
            transplanted pixel-for-pixel = Braunschweig, gules two lions
            passant guardant or
  Bottom-L: svg-sources/GBH_Everstein.svg (azure, argent lion, or crown)
  Bottom-R: Ernst II Braunschweig-Lüneburg arms, 4th quarter (Homburg:
            within a bordure compony azure and argent, gules a lion rampant
            or). The quarter is rebuilt as a square: the gules field fills
            the whole quarter, the compony bordure is adapted from the
            Ernst II band (three cells per edge, azure/argent alternation,
            original separator colour), and the lion is extracted from the
            quarter art and centred on the field.

Historical quarterly blazon (reference only):
  Q1 Braunschweig gules two lions passant guardant or; Q2 Lüneburg or semy
  of hearts gules a lion rampant azure armed/langued gules; Q3 Everstein
  azure a lion rampant argent crowned or; Q4 Homburg within a bordure
  compony azure and argent gules a lion rampant or armed/langued azure.

Build: 4x supersample; fields painted with exact mod palette RGB; charge
groups extracted by color-masking + connected components, scaled to fill
90% of their area, black outlines kept (RZB precedent); LANCZOS downscale;
byte-exact EU4 TGA v2 (256x256, type 2, 24-bit, 196652 bytes, TRUEVISION
footer identical to existing mod flags).

Usage:
  python3 tools/flags-research/build_gbh_flag.py            # install
  python3 tools/flags-research/build_gbh_flag.py -o out.tga
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import deque

import cairosvg
from PIL import Image

SVGNS = "{http://www.w3.org/2000/svg}"

# Mod palette (WappenWiki fills, exact RGB):
OR = (242, 188, 81)       # #F2BC51
AZURE = (13, 103, 147)    # #0D6793
ARGENT = (246, 246, 246)  # #F6F6F6
GULES = (188, 46, 46)     # #BC2E2E

VENV = os.path.expanduser("~/.local/share/svg2flag/venv")
MOD_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "svg-sources")
DEFAULT_OUT = os.path.join(MOD_ROOT, "gfx", "flags", "GBH.tga")
# Braunschweig-Lüneburg flag in the WappenWiki Flags for EUIV - Custom mod.
# Its top half is the Brunswick arms (gules, two lions passant guardant or),
# transplanted pixel-for-pixel as the new GBH top band.
BRU_TGA = "/home/rick/Paradox/Mods/Europa Universalis IV/WappenWiki Flags for EUIV - Custom/gfx/flags/BRU.tga"
# WappenWiki "Ernst II Braunschweig-Lüneburg" arms
# (https://wappenwiki.org/images/1/1b/Ernst_II_Braunschweig-Luneburg.svg).
# Its fourth quarter is the Homburg arms (within a bordure compony azure-argent,
# gules a lion rampant or). The bottom-right quarter of the GBH flag reuses that
# quarter wholesale (gules field, gold lion, and the genuine checked bordure),
# instead of drawing a synthetic checkerboard.
ERNST_II_SVG = "GBH_Ernst_II_15th_century.svg"
# Homburg quarter crop box in viewBox units (bottom-right of the 4-field arms).
HOMBURG_Q4_VB = (394, 451, 766, 773)

SS = 4          # supersample: 1 viewBox unit = SS render px
FIT = 0.90      # charge group fills 90% of its quarter


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


def strip_svg(x):
    x = re.sub(r"<!DOCTYPE.*?\]>", "", x, flags=re.S)
    return re.sub(r"&(ns_\w+);", "urn:x", x)


def load(rel):
    path = os.path.join(SRC_DIR, rel)
    return path, ET.fromstring(strip_svg(open(path, encoding="utf-8", errors="replace").read()))


def render(el, vb, scale=SS):
    vx, vy, vw, vh = vb
    xml = ET.tostring(el, encoding="unicode")
    doc = (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'xmlns:i="urn:x" xmlns:graph="urn:x" version="1.1" '
        f'viewBox="{vx} {vy} {vw} {vh}" width="{int(vw * scale)}" height="{int(vh * scale)}">'
        f"{xml}</svg>"
    )
    png = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    try:
        cairosvg.svg2png(
            bytestring=doc.encode(),
            write_to=png,
            output_width=int(vw * scale),
            output_height=int(vh * scale),
            background_color="rgba(0,0,0,0)",
        )
        return Image.open(png).convert("RGBA")
    finally:
        os.unlink(png)


def mask_field(im, rgb, tol=45):
    """Set field-colored pixels transparent. In-place."""
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 40 and abs(r - rgb[0]) < tol and abs(g - rgb[1]) < tol and abs(b - rgb[2]) < tol:
                px[x, y] = (0, 0, 0, 0)


def label_components(im, thresh=60, downsample=4):
    """Label opaque components of the alpha channel.

    Returns (label_grid rows, comps) where comps is a list of
    (bbox 4x-px, cell_count, grid_label) sorted descending by cell_count.
    """
    w, h = im.size
    m = im.getchannel("A").resize((w // downsample, h // downsample), Image.NEAREST)
    sw, sh = m.size
    px = m.load()
    grid = [[0] * sw for _ in range(sh)]
    comps = []
    cid = 0
    for sy in range(sh):
        row = grid[sy]
        for sx in range(sw):
            if row[sx] or px[sx, sy] <= thresh:
                continue
            cid += 1
            q = deque([(sx, sy)])
            row[sx] = cid
            minx = maxx = sx
            miny = maxy = sy
            n = 0
            while q:
                x, y = q.popleft()
                n += 1
                if x < minx: minx = x
                if x > maxx: maxx = x
                if y < miny: miny = y
                if y > maxy: maxy = y
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < sw and 0 <= ny < sh and not grid[ny][nx] and px[nx, ny] > thresh:
                            grid[ny][nx] = cid
                            q.append((nx, ny))
            comps.append(
                ((minx * downsample, miny * downsample, maxx * downsample, maxy * downsample), n, cid)
            )
    comps.sort(key=lambda c: -c[1])
    return grid, comps


def keep_components(im, grid, keep_ids, downsample=4):
    """Zero alpha outside the kept component ids. In-place.

    mask is an 'L' image with 255 where the component id is kept, 0 elsewhere,
    at the downsample resolution. Upscale mask to full res (NEAREST) and multiply
    the alpha channel by it (ImageChops.multiply scales 0-255 as 0-1).
    """
    from PIL import ImageChops
    keep = set(keep_ids)
    sw, sh = len(grid[0]), len(grid)
    mask = Image.new("L", (sw, sh), 0)
    mask.putdata([255 if v in keep else 0 for r in grid for v in r])
    mask = mask.resize((im.size[0], im.size[1]), Image.NEAREST)
    im.putalpha(ImageChops.multiply(im.getchannel("A"), mask))


def crop_rgba(im, bb, pad=0):
    x0, y0, x1, y1 = bb
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(im.size[0], x1 + pad)
    y1 = min(im.size[1], y1 + pad)
    return im.crop((x0, y0, x1, y1))


def recolor(im, pred):
    """Recolor pixels matching pred in-place (pred(r,g,b)->bool)."""
    px = im.load()
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            r, g, b, a = px[x, y]
            if a > 40 and pred(r, g, b):
                px[x, y] = (OR[0], OR[1], OR[2], a)


def ascii_preview(im, w=100, label=""):
    ow, oh = im.size
    h = max(1, int(oh * w / ow * 0.5))
    has_alpha = "A" in im.getbands()
    im2 = im.resize((w, h), Image.LANCZOS)
    px = im2.load()
    out = []
    for y in range(h):
        row = ""
        for x in range(w):
            pxv = px[x, y]
            if has_alpha and pxv[3] < 40:
                row += " "
                continue
            r, g, b = pxv[0], pxv[1], pxv[2]
            if r > 150 and g > 120 and b < 110:
                row += "O"
            elif b > 110 and r < 100:
                row += "B"
            elif r > 120 and g < 95 and b < 95:
                row += "R"
            elif r > 200 and g > 200 and b > 200:
                row += "W"
            elif max(r, g, b) < 60:
                row += "#"
            else:
                row += "."
        out.append(row)
    print(f"--- {label} ({ow}x{oh}) ---")
    print("\n".join(out))


def extract_q3():
    """Azure, a lion rampant argent crowned or, armed/langued gules."""
    path, root = load("GBH_Everstein.svg")
    vb = [float(x) for x in re.split(r"[ ,]+", root.get("viewBox"))]
    im = render(root, vb)
    mask_field(im, AZURE)
    grid, comps = label_components(im)
    if not comps:
        sys.exit(f"Q3: no components in {path}")
    keep_components(im, grid, [comps[0][2]])  # largest comp = the lion
    crop = crop_rgba(im, comps[0][0], pad=SS)
    return crop, (comps[0][0][2] - comps[0][0][0]) / SS, (comps[0][0][3] - comps[0][0][1]) / SS


def extract_q4_ernst():
    """Homburg quarter (within a bordure compony azure and argent, gules a lion
    rampant or) lifted wholesale from the Ernst II Braunschweig-Lüneburg arms.
    """
    path, root = load(ERNST_II_SVG)
    vb = [float(x) for x in re.split(r"[ ,]+", root.get("viewBox"))]
    im = render(root, vb, scale=SS)
    x0, y0, x1, y1 = (int((HOMBURG_Q4_VB[0] - vb[0]) * SS),
                      int((HOMBURG_Q4_VB[1] - vb[1]) * SS),
                      int((HOMBURG_Q4_VB[2] - vb[0]) * SS),
                      int((HOMBURG_Q4_VB[3] - vb[1]) * SS))
    crop = im.crop((x0, y0, x1, y1)).convert("RGBA")
    palette = (OR, AZURE, ARGENT, GULES)
    for y in range(crop.size[1]):
        for x in range(crop.size[0]):
            r, g, b, a = crop.getpixel((x, y))
            if a < 40:
                crop.putpixel((x, y), (*GULES, 255))
                continue
            nearest = min(palette, key=lambda p: (r - p[0]) ** 2 + (g - p[1]) ** 2 + (b - p[2]) ** 2)
            crop.putpixel((x, y), (*nearest, 255))
    _fill_edge_dark(crop, GULES)
    return crop


def _fill_edge_dark(im, rgb):
    """Fill near-black blobs connected to the crop border with rgb, so the
    quarterly field-divider and shield-outline lines do not leak into the flag.
    """
    from collections import deque
    w, h = im.size
    vis = [[0] * w for _ in range(h)]
    q = deque()

    def dark(px): return max(px[0], px[1], px[2]) < 70
    for x in range(w):
        for y in (0, h - 1):
            if not vis[y][x] and dark(im.getpixel((x, y))):
                vis[y][x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not vis[y][x] and dark(im.getpixel((x, y))):
                vis[y][x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        im.putpixel((x, y), (*rgb, 255))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not vis[ny][nx] and dark(im.getpixel((nx, ny))):
                vis[ny][nx] = 1
                q.append((nx, ny))


def tga_check(path):
    data = open(path, "rb").read()
    ref = open(os.path.join(MOD_ROOT, "gfx", "flags", "LGN.tga"), "rb").read()
    size = len(data)
    img_type = data[2]
    depth = data[16]
    footer_ok = size == 196652 and img_type == 2 and depth == 24 and data[-26:] == ref[-26:]
    return size, img_type, depth, footer_ok


def main():
    p = argparse.ArgumentParser(description="GBH (Grubenhagen) flag: Brunswick top band over Everstein/Homburg")
    p.add_argument("-o", "--out", default=DEFAULT_OUT, help="output TGA path")
    p.add_argument("--preview", action="store_true", help="print ASCII preview of charges and flag")
    args = p.parse_args()

    C = SS * 256  # 1024
    comp = Image.new("RGB", (C, C), GULES)

    # --- extract charge groups ---
    crop3, w3, h3 = extract_q3()
    crop4 = extract_q4_ernst()

    if args.preview:
        for name, crop, w, h in (("Everstein", crop3, w3, h3),):
            ascii_preview(crop, 60, f"{name} charge crop ({w:.0f}x{h:.0f} vb units)")
        ascii_preview(crop4, 60, "Homburg quarter w/ Ernst bordure")

    # Per fess layout. Top band = top half of BRU.tga (Brunswick arms, two
    # lions), transplanted pixel-for-pixel. Bottom splits into left Everstein
    # (azure) and right Homburg (gules, bordered). At SS=4, C=1024: top band
    # y 0..512; bottom-left x 0..512 y 512..1024; bottom-right x 512..1024.
    TOP_H = SS * 128      # top band height
    BOT_W = SS * 128      # each bottom half width

    bru = Image.open(BRU_TGA).convert("RGB")
    top = bru.crop((0, 0, bru.size[0], bru.size[1] // 2)).resize((C, TOP_H), Image.LANCZOS)
    comp.paste(top, (0, 0))
    print(f"top band: BRU.tga top half ({bru.size[0]}x{bru.size[1]//2}) upscaled to {C // SS}x{TOP_H // SS} px")

    comp.paste(Image.new("RGB", (BOT_W, TOP_H), AZURE), (0, TOP_H))
    s = min(FIT * 128 / w3, FIT * 128 / h3)
    tw, th = round(w3 * s * SS), round(h3 * s * SS)
    g3 = crop3.resize((tw, th), Image.LANCZOS)
    comp.paste(g3, ((BOT_W - tw) // 2, TOP_H + (TOP_H - th) // 2), g3)
    print(f"Everstein: lion {w3:.0f}x{h3:.0f} -> {tw // SS}x{th // SS} px in bottom-left")

    comp.paste(Image.new("RGB", (BOT_W, TOP_H), GULES), (BOT_W, TOP_H))
    comp.paste(crop4.resize((BOT_W, TOP_H), Image.LANCZOS), (BOT_W, TOP_H))
    print("Homburg: Ernst II quarter (gules, gold lion, checked bordure) fills bottom-right")

    flag = comp.resize((256, 256), Image.LANCZOS)
    flag.save(args.out)

    size, img_type, depth, ok = tga_check(args.out)
    print(f"saved {args.out}")
    print(f"  {size} bytes, type {img_type}, {depth}-bit, footer matches LGN: {ok}")
    if not ok:
        sys.exit("TGA header check FAILED - expected 196652 bytes, type 2, 24-bit, LGN footer")

    px = flag.load()
    counts = {}
    for name, color in (("or", OR), ("azure", AZURE), ("argent", ARGENT), ("gules", GULES)):
        counts[name] = sum(
            1 for y in range(256) for x in range(256)
            if abs(px[x, y][0] - color[0]) < 8 and abs(px[x, y][1] - color[1]) < 8
            and abs(px[x, y][2] - color[2]) < 8)
    near_black = sum(1 for y in range(256) for x in range(256) if max(px[x, y]) < 40)
    print("  palette: " + ", ".join(
        f"{k} {v}px ({v / 65536 * 100:.0f}%)" for k, v in counts.items())
        + f", near-black {near_black}px")

    if args.preview:
        ascii_preview(flag, 70, "GBH.tga final")


if __name__ == "__main__":
    main()