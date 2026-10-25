#!/usr/bin/env python3
"""Hand-placed WappenWiki flags (flag path 1 in FLAG_NOTES.md).

Each entry: TAG -> (WappenWiki file title, why this arms fits the tag).
The source of every flag is the WappenWiki file page
https://wappenwiki.org/index.php/File:<Title>.svg (Finellach's SVG, CC BY-NC-SA 3.0),
mirrored locally in MIRROR. The shield outline is stripped, its fill becomes
the flat field, and the charge is fitted into a 256x256 canvas.

    python3 tools/wwflags.py [TAG ...]
"""
import re, subprocess, sys, tempfile, os
from pathlib import Path
from PIL import Image

MIRROR = Path(os.environ.get("WAPPENWIKI", "/home/rick/Paradox/heraldry/wappenwiki-finellach"))
FLAGS = Path(__file__).resolve().parent.parent / "gfx" / "flags"

# Source: https://wappenwiki.org/index.php/File:<title>.svg
SOURCES = {
    # Gille: the family Patrum Scuta cites for c_trandheim
    "TRD": "Gille",
    # Losna: the family Patrum Scuta cites for Telemark
    "TEL": "Losna",
    # Sigurd Brynjulvsson Galte: the family Patrum Scuta cites for Hordaland
    "HRD": "Sigurd Brynjulvsson Galte",
    # Hjorthorn: the family Patrum Scuta cites for Varmland
    "VAR": "Hjorthorn",
    # Gotland: the region's arms
    "GOT": "Gotland",
    # Jemtland: the region's arms
    "JAM": "Jemtland",
    # Krag Sjaelland: noble family of Zealand standing in for the region
    "SJA": "Krag Sjælland",
    # Hvide (af Jylland): Jutland family standing in for the region
    "JYL": "Hvide (af Jylland)",
    # De Tonsberg: family of Tonsberg, a loose fit for Vestfold
    "VFD": "De Tonsberg",
}
# Arms whose bordure follows the shield outline: keep the charge only (fractions of the render)
INNER = {"JAM": (0.15, 0.14, 0.85, 0.75)}
SHIELD_RE = re.compile(r"<(polygon|path)\b[^>]*?(?:/>|>\s*</\1>)", re.S)


def build(tag, title, size=256, height=218, inner=None):
    s = (MIRROR / f"{title}.svg").read_text(errors="replace")
    s = re.sub(r"<!DOCTYPE.*?\]>", "", s, flags=re.S)
    s = re.sub(r"&ns_[a-z_]+;", "", s)
    s = re.sub(r"<foreignObject.*?</foreignObject>", "", s, flags=re.S)
    m = SHIELD_RE.search(s)
    shield = m.group(0)
    f = re.search(r"fill:\s*(#[0-9a-fA-F]{6})", shield) or re.search(r'fill="(#[0-9a-fA-F]{6})"', shield)
    field = tuple(int(f.group(1)[i:i + 2], 16) for i in (1, 3, 5))
    # drop the shield and any outline/overlay copy of the same geometry
    geo = re.search(r'(?:points|d)="\s*M?\s*([-\d.,]+)', shield).group(1)[:10]
    # (the shield outline is often a separate unfilled polygon with ~100 points)
    s = SHIELD_RE.sub(lambda x: "" if geo in x.group(0) or (
        x.group(1) == "polygon" and re.search(r'fill[:=]"?\s*none', x.group(0))
        and x.group(0).count(" ") > 100) else x.group(0), s)
    with tempfile.TemporaryDirectory() as d:
        src, png = Path(d, "a.svg"), Path(d, "a.png")
        src.write_text(s)
        subprocess.run(["inkscape", str(src), "-h", "2400", "-o", str(png)], check=True,
                       capture_output=True)
        im = Image.open(png).convert("RGBA")
    if inner:  # keep only the central part (drops a shield-shaped bordure)
        w, h = im.size
        im = im.crop((round(w * inner[0]), round(h * inner[1]), round(w * inner[2]), round(h * inner[3])))
        # drop bordure fragments cut off by the crop (small detached islands)
        import numpy as np
        from scipy import ndimage
        a = np.array(im.getchannel("A")) > 8
        lab, n = ndimage.label(ndimage.binary_dilation(a, iterations=6))
        sizes = ndimage.sum(a, lab, range(1, n + 1))
        keep = np.isin(lab, [i + 1 for i, z in enumerate(sizes) if z > 0.1 * max(sizes)])
        im.putalpha(Image.fromarray((np.array(im.getchannel("A")) * keep).astype("uint8")))
    im = im.crop(im.getchannel("A").getbbox())
    k = min(height / im.height, height / im.width)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), field + (255,))
    out.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    rgb = out.convert("RGB")
    old = (FLAGS / "DEH.tga").read_bytes()[:18]
    px = rgb.tobytes("raw", "BGR")
    (FLAGS / f"{tag}.tga").write_bytes(old + px)
    return field




def jemtland(tag="JAM", size=256, band=28, marks=6, S=4):
    """Jemtland with its bordure squared: the shield-shaped bordure is rebuilt as a
    square ring, its keyhole marks cut from the original's top edge and rotated
    onto each side (same approach as Deheubarth's squared field)."""
    import numpy as np
    from scipy import ndimage
    from PIL import ImageDraw
    s = (MIRROR / "Jemtland.svg").read_text(errors="replace")
    s = re.sub(r"<!DOCTYPE.*?\]>", "", s, flags=re.S)
    s = re.sub(r"&ns_[a-z_]+;", "", s)
    m = SHIELD_RE.search(s)
    geo = re.search(r'(?:points|d)="\s*M?\s*([-\d.,]+)', m.group(0)).group(1)[:10]
    s = SHIELD_RE.sub(lambda x: "" if geo in x.group(0) else x.group(0), s)
    with tempfile.TemporaryDirectory() as d:
        src, png = Path(d, "a.svg"), Path(d, "a.png")
        src.write_text(s)
        subprocess.run(["inkscape", str(src), "-h", "2400", "-o", str(png)], check=True, capture_output=True)
        im = Image.open(png).convert("RGBA")
    W = im.width
    red = (188, 46, 46, 255)
    # charge: the lion and axe inside the inner field, bordure fragments dropped
    box = (round(W * .13), round(2400 * .09), round(W * .87), round(2400 * .88))
    ch = im.crop(box)
    a = np.array(ch.getchannel("A")) > 8
    lab, n = ndimage.label(ndimage.binary_dilation(a, iterations=6))
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    ch.putalpha(Image.fromarray((np.array(ch.getchannel("A")) * ~np.isin(lab, [e for e in edge if e])).astype("uint8")))
    ch = ch.crop(ch.getchannel("A").getbbox())
    out_size, size, band = size, size * S, band * S
    o = 0
    inner = size - 2 * band - 14 * S
    k = min(inner / ch.width, inner / ch.height)
    ch = ch.resize((round(ch.width * k), round(ch.height * k)), Image.LANCZOS)
    # square ring
    out = Image.new("RGBA", (size, size), red)
    dr = ImageDraw.Draw(out)
    dr.rectangle((0, 0, size - 1, size - 1), fill=(246, 246, 246, 255))
    i0 = o + band
    dr.rectangle((i0, i0, size - 1 - i0, size - 1 - i0), fill=red, outline=(0, 0, 0, 255), width=round(1.6 * S))
    # marks: one period of the original's top band (marks 190 + 241*i px at full res)
    L = size - 2 * (o + band)
    tw = L // marks
    for i in range(marks):
        t = im.crop((70 + 241 * i, 88, 70 + 241 * (i + 1), 212)).convert("RGBA")
        lum = np.array(t.convert("L")).astype(float)
        ink = Image.fromarray((255 - lum).clip(0, 255).astype("uint8"))
        arr = np.array(ink)
        lb, nn = ndimage.label(ndimage.binary_dilation(arr > 90, iterations=4))
        big = 1 + int(np.argmax(ndimage.sum(arr > 90, lb, range(1, nn + 1))))
        ink = Image.fromarray(arr * ndimage.binary_dilation(lb == big, iterations=2))
        bb = ink.point(lambda v: 255 if v > 90 else 0).getbbox()
        ink = ink.crop(bb)
        k2 = (band * .72) / max(ink.size)
        ink = ink.resize((max(1, round(ink.width * k2)), max(1, round(ink.height * k2))), Image.LANCZOS)
        mk = Image.new("RGBA", ink.size, (0, 0, 0, 255))
        mk.putalpha(ink)
        cx = o + band + i * tw + tw // 2 + (L - tw * marks) // 2
        cy = o + band // 2
        for ang, (px, py) in ((0, (cx, cy)), (180, (cx, size - 1 - cy)), (90, (cy, cx)), (-90, (size - 1 - cy, cx))):
            r = mk.rotate(ang, expand=True)
            out.alpha_composite(r, (px - r.width // 2, py - r.height // 2))
    out.alpha_composite(ch, ((size - ch.width) // 2, (size - ch.height) // 2))
    rgb = out.resize((out_size, out_size), Image.LANCZOS).convert("RGB")
    (FLAGS / f"{tag}.tga").write_bytes((FLAGS / "DEH.tga").read_bytes()[:18] + rgb.tobytes("raw", "BGR"))


# Animal charges from Armoria's bundled charge set. Armoria's charges are themselves
# WappenWiki artwork (each SVG's <metadata> names http://wappenwiki.org, CC BY-NC-SA 3.0),
# placed on the tinctures CK3 gives the title arms.
ARMORIA = Path(os.environ.get("ARMORIA", "/home/rick/Paradox/heraldry/Armoria")) / "public" / "charges"
WHITE, BLACK, BLUE, RED, GOLD = "#f6f6f6", "#333333", "#0d6793", "#bc2e2e", "#f2bc51"
# TAG: (charge, field, primary, secondary, tertiary)   # CK3 arms it follows
ARMORIA_FLAGS = {
    "AUD": ("raven", WHITE, BLACK, WHITE, BLACK),          # c_austisland: black raven on white
    "DLR": ("boarRampant", GOLD, BLACK, RED, RED),         # d_dalir: black boar, red tongue/hooves, on gold
    "VES": ("falcon", BLUE, WHITE, WHITE, BLUE),           # c_vestisland: white falcon on blue
    "VSV": ("griffinRampant", RED, GOLD, GOLD, GOLD),      # c_vastvag: gold griffin on red
    "OLA": ("stagPassant", BLACK, GOLD, RED, GOLD),        # c_olavinlinna: gold elk, red antlers, on sable
    "OUL": ("salmon", WHITE, BLUE, BLUE, BLUE),            # c_oulu: blue fish on white
}


def armoria(tag, size=256, height=218):
    charge, field, c1, c2, c3 = ARMORIA_FLAGS[tag]
    s = (ARMORIA / f"{charge}.svg").read_text()
    s = s.replace('fill="#d7374a"', f'fill="{c1}"', 1)
    s = s.replace("</metadata>", "</metadata>")
    css = f'<style>.secondary{{fill:{c2}}} .tertiary{{fill:{c3}}}</style>'
    s = re.sub(r"(<svg[^>]*>)", lambda m: m.group(1) + css, s, count=1)
    with tempfile.TemporaryDirectory() as d:
        src, png = Path(d, "a.svg"), Path(d, "a.png")
        src.write_text(s)
        subprocess.run(["inkscape", str(src), "-h", "2400", "-o", str(png)], check=True, capture_output=True)
        im = Image.open(png).convert("RGBA")
    im = im.crop(im.getchannel("A").getbbox())
    k = min(height / im.height, 238 / im.width)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    fc = tuple(int(field[i:i + 2], 16) for i in (1, 3, 5))
    out = Image.new("RGBA", (size, size), fc + (255,))
    out.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    (FLAGS / f"{tag}.tga").write_bytes((FLAGS / "DEH.tga").read_bytes()[:18] + out.convert("RGB").tobytes("raw", "BGR"))


# CK3 bakes whose emblem sits off-centre in the title arms; re-centred on the ink bbox
# after `coaflags.py --title` (re-run `python3 tools/wwflags.py center` after re-baking them).
RECENTER = ["ANG", "HJL", "NES", "NYL", "TAO", "SNK"]


def recenter(tag, size=256):
    import numpy as np
    path = FLAGS / f"{tag}.tga"
    raw = path.read_bytes()
    a = np.frombuffer(raw[18:18 + size * size * 3], "u1").reshape(size, size, 3).copy()
    bg = a[2, 2].copy()
    ys, xs = np.where(np.abs(a.astype(int) - bg).sum(2) > 40)
    dx = (size - 1 - xs.max() - xs.min()) // 2
    dy = (size - 1 - ys.max() - ys.min()) // 2
    out = np.empty_like(a)
    out[:] = bg
    sy, sx = slice(max(0, -dy), size - max(0, dy)), slice(max(0, -dx), size - max(0, dx))
    ty, tx = slice(max(0, dy), size - max(0, -dy)), slice(max(0, dx), size - max(0, -dx))
    out[ty, tx] = a[sy, sx]
    path.write_bytes(raw[:18] + out.tobytes() + raw[18 + size * size * 3:])
    return dx, dy


if __name__ == "__main__":
    if sys.argv[1:] == ["center"]:
        for t in RECENTER:
            print(t, "shifted", recenter(t))
        sys.exit()
    for t in (sys.argv[1:] or [*SOURCES, *ARMORIA_FLAGS]):
        if t in ARMORIA_FLAGS:
            armoria(t)
            print(t, ARMORIA_FLAGS[t][0], "Armoria")
        elif t == "JAM":
            jemtland()
            print(t, SOURCES[t], "squared bordure")
        else:
            print(t, SOURCES[t], build(t, SOURCES[t], inner=INNER.get(t)))
