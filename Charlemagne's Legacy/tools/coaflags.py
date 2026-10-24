"""Render CK3 coats of arms into EU4 flag TGAs.

A tag takes either its 867 ruler's house/dynasty arms or the arms of its
landed title (d_/c_ key): the composition comes from CK3's authored
designs (common/coat_of_arms/coat_of_arms/ blocks keyed by dynasty id,
house key or title): a pattern texture whose RGB channels are colour-slot
masks (R->color1, G->color2, B->color3, alpha=opacity), shape, and
colour-slot masks in RGB (B->color1, G->color2, R->color3) placed at
normalized position/scale.
All colours snap to the WappenWiki tincture canon from FLAG_NOTES
before rendering, so the flags match the family palette exactly.
"""
import os, re, struct, sys
from paths import CK3_GAME, PATRUM

CK3 = CK3_GAME
# Patrum Scuta carries the authored dynasty designs the user wants drawn;
# base game blocks stay as fallback for dynasties it does not override.
PS = PATRUM
COA_DIRS = [
    os.path.join(PS, "common", "coat_of_arms", "coat_of_arms"),
    os.path.join(CK3, "common", "coat_of_arms", "coat_of_arms"),
]
TEX_DIRS = {
    "patterns": [os.path.join(PS, "gfx", "coat_of_arms", "patterns"),
                 os.path.join(CK3, "gfx", "coat_of_arms", "patterns")],
    "emblems": [os.path.join(PS, "gfx", "coat_of_arms", "colored_emblems"),
                os.path.join(CK3, "gfx", "coat_of_arms", "colored_emblems")],
    "textured": [os.path.join(PS, "gfx", "coat_of_arms", "textured_emblems"),
                 os.path.join(CK3, "gfx", "coat_of_arms", "textured_emblems")],
}
GFX = TEX_DIRS  # legacy name
MODROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# WappenWiki tincture canon (tools/FLAG_NOTES.md)
TINCTURES = {
    "or": (242, 188, 81), "argent": (246, 246, 246),
    "azure": (13, 103, 147), "gules": (188, 46, 46),
    "purpure": (145, 58, 106), "sable": (51, 51, 51),
    "vert": (62, 147, 62),
    "murrey": (164, 44, 69), "sanguine": (165, 47, 45),
    "tenne": (191, 117, 50),
    "bisque": (244, 217, 163), "bleu_celeste": (53, 156, 183),
    "brunatre": (114, 89, 66), "carnation": (234, 191, 162),
    "cendree": (122, 122, 122), "orange": (229, 138, 56),
    "rose": (217, 146, 146), "senois": (151, 68, 56),
}


# CK3/PS named colours are heraldic concepts: every name in play maps
# explicitly to a WappenWiki tincture. When a new colour shows up, the
# fix is a hand-added row here - never a nearest-colour guess.
_SEMANTIC = {
    "white": "argent", "silver": "argent",
    "black": "sable", "black_mid": "cendree",       # PS: lighter black
    "blue": "azure", "blue_light": "bleu_celeste",
    "red": "gules", "red_light": "gules", "red_mid": "gules",
    "red_dark": "sanguine",
    "yellow": "or", "yellow_light": "or", "yellow_mid": "or",
    "yellow_dark": "or",                            # PS: charges Or on Argent
    "green": "vert", "green_light": "vert", "sinople": "vert",
    "purple": "purpure", "orange": "orange",
    "grey": "cendree", "grey_dark": "cendree",
    "brown": "brunatre", "brunatre": "brunatre",
    "brunatre_dark": "senois",
    "carnation": "carnation",
}


def resolve(name_or_rgb):
    """CK3/PS named colour -> WappenWiki tincture RGB, deterministically
    through _SEMANTIC. An unmapped colour is an error: add an explicit
    row (name -> canon tincture), never guess."""
    if isinstance(name_or_rgb, str):
        tname = _SEMANTIC.get(name_or_rgb.lower())
        if tname is None:
            raise ValueError(
                f"unmapped CK3 colour {name_or_rgb!r}: add an explicit "
                "_SEMANTIC row mapping it to a WappenWiki tincture")
        return TINCTURES[tname]
    raise ValueError(name_or_rgb)


def read_dds(path):
    """RGBA float array, 0..1. Pillow handles DXT1/DXT5/DX10; the
    uncompressed BGRA raster DDS files (ce_block_02.dds and the other
    raw-32bpp textures) decode by hand - Pillow cannot read uncompressed
    DDS and mangles them into a constant colour."""
    import numpy as np
    from PIL import Image
    data = open(path, "rb").read()
    if data[:4] != b"DDS ":
        raise NotImplementedError(f"{path}: not a DDS")
    h, w = struct.unpack("<II", data[12:20])
    _pfsize, pf_flags, fourcc, bpp = struct.unpack("<4I", data[76:92])
    fc = fourcc.to_bytes(4, "little").decode("latin1").strip("\x00 ")
    if not fc and bpp == 32 and pf_flags & 0x40:
        raw = np.frombuffer(data[128:128 + w * h * 4], np.uint8)
        raw = raw.reshape(h, w, 4).astype(np.float32)
        # masks: R=0xff0000, G=0xff00, B=0xff -> BGRA byte order
        return np.concatenate([raw[..., 2:3], raw[..., 1:2],
                               raw[..., 0:1], raw[..., 3:4]], axis=2) / 255
    return np.asarray(Image.open(path).convert("RGBA")).astype(np.float32) / 255


def parse_blocks(path):
    """Top-level `key = {...}` blocks of a CoA file."""
    txt = open(path, encoding="utf-8-sig").read()
    # strip comments
    txt = re.sub(r'#.*', '', txt)
    for m in re.finditer(r'([@\w]+)\s*=\s*{', txt):
        start = m.end()
        depth, i = 1, start
        while depth and i < len(txt):
            if txt[i] == '{':
                depth += 1
            elif txt[i] == '}':
                depth -= 1
            i += 1
        yield m.group(1), txt[start:i - 1], m.group(0) + txt[start:i]


def _top_level_pairs(block):
    """(key, value) pairs of a block body at depth 0 only."""
    out, depth, i, n = [], 0, 0, len(block)
    while i < n:
        ch = block[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
        elif depth == 0 and ch.isalpha() or depth == 0 and ch == '_':
            m = re.match(r'(\w+)\s*=\s*("[^"]+"|[^\s{}]+)', block[i:])
            if m:
                out.append((m.group(1), m.group(2).strip('"')))
                i += m.end()
                continue
        i += 1
    return out


def parse_coa(block):
    """A CoA definition block -> {pattern, colors, emblems:[...]}.
    Emblem entries may carry `mask={r g b}` (the shader's MaskColor:
    pattern-region gating) and instances may carry `rotation` in
    degrees; a negative scale axis mirrors the instance."""
    coa = {"pattern": None, "colors": {}, "emblems": []}
    for k, v in _top_level_pairs(block):
        if k == "pattern":
            coa["pattern"] = v
        elif re.fullmatch(r'color\d', k):
            coa["colors"][k] = v
    for em in re.finditer(r'(colored|textured)_emblem\s*=\s*{', block):
        s = em.end()
        depth, i = 1, s
        while depth and i < len(block):
            if block[i] == '{':
                depth += 1
            elif block[i] == '}':
                depth -= 1
            i += 1
        body = block[s:i - 1]
        emdat = {"texture": None, "colored": em.group(1) == "colored",
                 "colors": {}, "mask": None, "instances": []}
        m = re.search(r'texture\s*=\s*"([^"]+)"', body)
        if m:
            emdat["texture"] = m.group(1)
        for cm in re.finditer(r'color(\d)\s*=\s*("[^"]+"|\S+)', body):
            emdat["colors"][f"color{cm.group(1)}"] = cm.group(2).strip('"')
        mk = re.search(r'mask\s*=\s*{\s*([\d-]+)\s+([\d-]+)\s+([\d-]+)', body)
        if mk:
            emdat["mask"] = (int(mk.group(1)), int(mk.group(2)),
                             int(mk.group(3)))
        for im in re.finditer(r'instance\s*=\s*{', body):
            s = im.end()
            depth, i = 1, s
            while depth and i < len(body):
                if body[i] == '{':
                    depth += 1
                elif body[i] == '}':
                    depth -= 1
                i += 1
            ib = body[s:i - 1]
            pos = re.search(r'position\s*=\s*{\s*(-?[\d.]+)\s+(-?[\d.]+)\s*}', ib)
            scl = re.search(r'scale\s*=\s*{\s*(-?[\d.]+)\s+(-?[\d.]+)\s*}', ib)
            dep = re.search(r'depth\s*=\s*(-?[\d.]+)', ib)
            rot = re.search(r'rotation\s*=\s*([\d.+-]+)', ib)
            emdat["instances"].append({
                "position": (float(pos.group(1)), float(pos.group(2)))
                            if pos else (0.5, 0.5),
                "scale": (float(scl.group(1)), float(scl.group(2)))
                         if scl else (1.0, 1.0),
                "depth": float(dep.group(1)) if dep else 1.0,
                "rotation": float(rot.group(1)) if rot else 0.0,
            })
        # a colored_emblem with no instance fills the canvas centred
        if not emdat["instances"]:
            emdat["instances"].append({"position": (0.5, 0.5),
                                       "scale": (1.0, 1.0), "depth": 1.0,
                                       "rotation": 0.0})
        coa["emblems"].append(emdat)
    return coa


def find_house_coa(hkey):
    """CoA definition for a house/dynasty key: Patrum Scuta first (its
    files load after the base game, so its blocks win in-game), then the
    vanilla files; within one dir the alphabetically last file wins,
    matching the engine's overwrite order."""
    for coa_dir in COA_DIRS:
        found = None
        if not os.path.isdir(coa_dir):
            continue
        for fn in sorted(os.listdir(coa_dir)):
            if not fn.endswith(".txt"):
                continue
            path = os.path.join(coa_dir, fn)
            for key, _body, _full in parse_blocks(path):
                if key == hkey:
                    found = parse_coa(_body)
                    break
        if found is not None:
            return found
    return None


def find_tex(kind, name):
    for root in TEX_DIRS[kind]:
        path = os.path.join(root, name)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"{kind}/{name}: not in Patrum Scuta nor base game")


def save_dynasty_coa(path, key):
    """A save's dynasty record carries key=<CK3 dynasty> plus
    coat_of_arms_id - the CoA the dynasty and all its members display.
    """
    import re
    lines = _save_text(path)
    opener = re.compile(r"^(\d+)=\{")
    pat = re.compile(rf"^\tkey={re.escape(str(key))}$")
    hit = None
    for i, ln in enumerate(lines):
        if pat.match(ln):
            hit = i
            break
    if hit is None:
        return None
    start = None
    for i in range(hit, -1, -1):
        if opener.match(lines[i]):
            start = i
            break
    if start is None:
        return None
    top, depth = None, 1
    for ln in lines[start + 1:]:
        fell = depth
        depth += ln.count("{") - ln.count("}")
        if fell == 1 and depth > 0:
            got = re.match(r"^\tcoat_of_arms_id=(\d+)", ln)
            if got and top is None:
                top = int(got.group(1))
        if depth == 0:
            break
    return top



def compose(coa, size=1024):
    """Render a CoA to a square RGBA array (float, 0..1)."""
    import numpy as np
    canvas = np.zeros((size, size, 4), np.float32)
    cols = [np.asarray(resolve(coa["colors"].get(f"color{i}", "black")),
                       np.float32) / 255 for i in (1, 2, 3)]
    if coa["pattern"]:
        from PIL import Image
        tex = read_dds(find_tex("patterns", coa["pattern"]))
        big = Image.fromarray((tex * 255).astype(np.uint8), "RGBA")
        big = big.resize((size, size), Image.LANCZOS)
        big = np.asarray(big).astype(np.float32) / 255
        # shipped pattern shader: lerp(Fallback, Color1, r), then g/b
        # toward Color2/3 - raw 0..1 channels, no saturate (the fallback
        # is never reached: these patterns keep r=255 everywhere)
        r, g, b = big[..., 0:1], big[..., 1:2], big[..., 2:3]
        col = r * cols[0]
        col = col * (1 - g) + g * cols[1]
        col = col * (1 - b) + b * cols[2]
        canvas[..., :3] = col
        canvas[..., 3:4] = big[..., 3:4]
        # pattern-mask gate uses the raw pattern CHANNEL map (the shipped
        # shader derives slot coverages from it: r-g-b, then g-b)
        pat_ch = big[..., :3].copy()
    else:
        pat_ch = np.zeros((size, size, 3), np.float32)
    # emblems stack in file order, depth overrides
    ems = sorted(enumerate(coa["emblems"]),
                 key=lambda iv: (iv[1].get("depth", 1.0), iv[0]))
    for idx, em in ems:
        if not em["texture"]:
            continue
        kind = "emblems" if em.get("colored", True) else "textured"
        try:
            path = find_tex(kind, em["texture"])
        except FileNotFoundError:
            print(f"  (missing {kind} texture {em['texture']}, skipped)")
            continue
        tex = read_dds(path)
        mk = em.get("mask")
        # shipped colored-emblem shader: base Color1 everywhere, g lerps
        # toward Color2, r toward Color3, then b overlays as shading ink
        # (b~126/255 = overlay-neutral). mask={r g b} =.MaskColor: the
        # emblem shows only where the PATTERN's slot coverage opens the
        # gate: t = saturate(cover1*mask.r + cover2*mask.g + b*mask.b)
        t = None
        if mk:
            c1 = np.clip(pat_ch[..., 0:1] - pat_ch[..., 1:2]
                         - pat_ch[..., 2:3], 0, 1)
            c2 = np.clip(pat_ch[..., 1:2] - pat_ch[..., 2:3], 0, 1)
            t = np.clip(c1 * mk[0] + c2 * mk[1] + pat_ch[..., 2:3] * mk[2],
                        0, 1)
        for inst in em["instances"]:
            sx, sy = inst["scale"]
            # negative scale = mirrored quad (the vertex shader flips
            # the UV axis); the box still spans |scale|
            px = int(round(abs(sx) * size))
            py = int(round(abs(sy) * size))
            if px <= 0 or py <= 0 or not size:
                continue
            from PIL import Image
            big = Image.fromarray((tex * 255).astype(np.uint8),
                                  "RGBA")
            inst_img = big.resize((max(px, 1), max(py, 1)), Image.LANCZOS)
            if sx < 0:
                inst_img = inst_img.transpose(Image.FLIP_LEFT_RIGHT)
            if sy < 0:
                inst_img = inst_img.transpose(Image.FLIP_TOP_BOTTOM)
            rot = inst.get("rotation", 0.0)
            if rot:
                inst_img = inst_img.rotate(-rot, resample=Image.BICUBIC,
                                           expand=False)
            inst_tex = np.asarray(inst_img).astype(np.float32) / 255
            if not em.get("colored", True):
                # textured emblems carry their own artwork colours
                rgb = inst_tex[..., :3]
            else:
                # missing colourN = engine zero-init -> sable (confirmed
                # in-game: DLF's color1-only sabre renders a sable blade)
                c1 = np.asarray(resolve(em["colors"].get("color1", "black")),
                                np.float32) / 255
                c2 = np.asarray(resolve(em["colors"].get("color2", "black")),
                                np.float32) / 255
                c3 = np.asarray(resolve(em["colors"].get("color3", "black")),
                                np.float32) / 255
                gw = inst_tex[..., 1:2]
                rw = inst_tex[..., 0:1]
                bw = inst_tex[..., 2:3]
                col = gw * 0.0 + c1
                col = col * (1 - gw) + gw * c2
                col = col * (1 - rw) + rw * c3
                # standard overlay: mask<=0.5 darkens toward black, else
                # brightens toward white
                col = np.where(bw <= 0.5, 2 * col * bw,
                               1 - 2 * (1 - col) * (1 - bw))
                rgb = col
            cx, cy = inst["position"]
            x0 = int(round((cx - abs(sx) / 2) * size))
            y0 = int(round((cy - abs(sy) / 2) * size))
            dst = canvas
            h, w = rgb.shape[:2]
            ys, xs = max(0, y0), max(0, x0)
            ye, xe = min(size, y0 + h), min(size, x0 + w)
            if ye <= ys or xe <= xs:
                continue
            sub_rgb = rgb[ys - y0:ye - y0, xs - x0:xe - x0]
            sub_a = inst_tex[ys - y0:ye - y0, xs - x0:xe - x0, 3:4]
            if t is not None:
                sub_a = sub_a * t[ys - y0:ye - y0, xs - x0:xe - x0]
            # dst alpha handling: composite over what is there
            for c in range(3):
                dst[ys:ye, xs:xe, c] = (
                    dst[ys:ye, xs:xe, c] * (1 - sub_a[..., 0])
                    + sub_rgb[..., c] * sub_a[..., 0])
            dst[ys:ye, xs:xe, 3] = np.maximum(dst[ys:ye, xs:xe, 3],
                                              sub_a[..., 0])
    return canvas


def bake(canvas, tag, size=256, outdir=None):
    """Square CoA canvas -> EU4 TGA (24bpp, BGR, top-first, desc 0x20)."""
    import numpy as np
    from PIL import Image
    im = Image.fromarray((np.clip(canvas, 0, 1) * 255).astype(np.uint8),
                         "RGBA")
    # keys on a black underlay (EU4 flags have no transparency)
    bg = Image.new("RGBA", im.size, (17, 17, 17, 255))
    bg.alpha_composite(im)
    im = bg.convert("RGB")
    # WappenWiki discipline: clamp LANCZOS ringing to the tincture value
    # range, snap pixels sitting on a tainted flat region to their
    # nearest tincture, but keep antialiased mid-tones untouched.
    px = np.asarray(im).astype(np.float32)
    px = np.clip(px, 51, 246)
    names = list(TINCTURES.items())
    pal = np.asarray([v for _, v in names], np.float32)
    d = ((px[..., None, :] - pal[None, None, ...]) ** 2).sum(-1)
    near = d.argmin(-1)
    dist2 = d.min(-1)
    mask = (dist2 < 30 ** 2)[..., None]
    snapped = np.where(mask, pal[near], px)
    im = Image.fromarray(snapped.astype(np.uint8))
    arr = np.asarray(im.resize((size, size), Image.LANCZOS))
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0,
                      size, size, 24, 0x20)
    assert len(hdr) == 18
    out = os.path.join(outdir or os.path.join(MODROOT, "gfx", "flags"),
                       f"{tag}.tga")
    open(out, "wb").write(hdr + arr[..., ::-1].tobytes())
    return out


def dump_coa(coa, label=None):
    """Human-readable definition for --dry."""
    if label:
        print(label)
    print("pattern:", coa["pattern"], "| colors:", coa["colors"])
    for em in coa["emblems"]:
        print("  emblem:", em["texture"], em["colors"], len(em["instances"]))


def _dynasty_ids_tags():
    """Every tags.db tag whose name ends in `-ids` (the dynasty-named
    realms the user wants done first)."""
    import tagdb
    from db import Session
    from sqlalchemy import text
    s = Session()
    kept = {"PMS"}  # Přemyslids keep their old WappenWiki flag, not a CK3 CoA
    return [r[0] for r in s.execute(
        text("select tag from tags where name like '%ids' order by tag")).all()
        if r[0] not in kept]


def _tag_titles():
    """tag -> ck3_title for every tag in the DB (the save fallback
    reaches any tag through its title entity)."""
    from db import Session
    from sqlalchemy import text
    s = Session()
    return dict(s.execute(
        text("select tag, ck3_title from tags order by tag")).all())


def _save_text(path):
    """A save's plain text: newer saves are zips with one `gamestate`
    member, older ones are plaintext - return the lines either way."""
    import zipfile
    with zipfile.ZipFile(path) as z:
        return z.read("gamestate").decode(errors="replace").split("\n")


def load_save_database(path):
    """CK3 saves materialise every generated CoA instance:
    coat_of_arms_manager_database = { <idx> = { pattern... } } - parse
    each numbered entry with the same reader used for authored files."""
    import re
    lines = _save_text(path)
    i = next(k for k, ln in enumerate(lines)
             if "coat_of_arms_manager_database={" in ln)
    out, idx, buf, depth = {}, None, [], 0
    for ln in lines[i + 1:]:
        if depth == 0:
            m = re.match(r"^(\d+)=\{", ln)
            if m:
                idx, buf, depth = m.group(1), [], 1
                continue
            if ln.startswith("}"):
                break
            continue
        buf.append(ln)
        depth += ln.count("{") - ln.count("}")
        if depth == 0:
            out[int(idx)] = parse_coa("\n".join(buf))
            idx, buf = None, []
    return out


def save_title_coa(path, title):
    """The exact CoA instance a save's title holder uses at the save
    date: the title entity's top-level coat_of_arms_id indexes the
    database - the 867 bookmark saves carry the start generation."""
    import re
    lines = _save_text(path)
    opener = re.compile(r"^(\d+)=\{")
    pat = re.compile(rf"^\tkey={re.escape(title)}$")
    hit = None
    for i, ln in enumerate(lines):
        if pat.match(ln):
            hit = i
            break
    if hit is None:
        return None
    start = None
    for i in range(hit, -1, -1):
        if opener.match(lines[i]):
            start = i
            break
    if start is None:
        return None
    top, depth = None, 1
    for ln in lines[start + 1:]:
        fell = depth
        depth += ln.count("{") - ln.count("}")
        if fell == 1 and depth > 0:
            got = re.match(r"^\tcoat_of_arms_id=(\d+)", ln)
            if got and top is None:
                top = int(got.group(1))
        if depth == 0:
            break
    return top


def save_char_dyn_coa(path, char_id):
    """A ruler with no CK3 dynasty still gets a generated one by save
    time: character_lookup maps the game char to the save's internal
    index, and the dynasty whose dynasty_head is that index carries the
    CoA (the Shujahid precedent: fictional Hadramawt ruler Shujah)."""
    import re
    lines = _save_text(path)
    i = next((k for k, ln in enumerate(lines)
              if ln.startswith("character_lookup={")), None)
    if i is None:
        return None
    internal = None
    for ln in lines[i + 1:]:
        if not ln.startswith("\t"):
            break
        m = re.match(rf"^\t{re.escape(str(char_id))}=(\d+)$", ln)
        if m:
            internal = m.group(1)
            break
    if internal is None:
        return None
    hit = next((k for k, ln in enumerate(lines)
                if ln == f"\tdynasty_head={internal}"), None)
    if hit is None:
        return None
    opener = re.compile(r"^(\d+)=\{")
    start = max(k for k in range(hit, -1, -1) if opener.match(lines[k]))
    top, depth = None, 1
    for ln in lines[start + 1:]:
        fell = depth
        depth += ln.count("{") - ln.count("}")
        if fell == 1 and depth > 0:
            got = re.match(r"^\tcoat_of_arms_id=(\d+)", ln)
            if got and top is None:
                top = int(got.group(1))
        if depth == 0:
            break
    return top


def ruler_coa(tags=None, quiet=False, save_path=None):
    """tag -> rendered flag for every Islamic tag: the 867 holder's CK3
    identity (house key, else dynasty id) resolved against Patrum Scuta's
    authored CoAs first, base game second, and a CK3 save (which carries
    the CoAs the engine generated) last."""
    import ck3
    titles = ck3.load_titles()
    chars = ck3.load_chars()
    houses = ck3.load_houses()
    dyns = ck3.load_dynasties()
    db = thandles = None
    if save_path:
        db = load_save_database(save_path)
        thandles = _tag_titles()
    done, misses = [], []
    if tags is None:
        tags = _dynasty_ids_tags()
    for tag in tags:
        got = ck3.resolve(tag, titles, chars, dyns, houses)
        if got.get("error"):
            misses.append((tag, got["error"]))
            continue
        cid = got["char"]
        ev = ck3.dynasty_events(chars[cid])
        _d, kind, key = ev[-1] if ev else (None, None, None)
        # candidates: the ruler's own identity, then its parent dynasty
        # (a house may have no authored CoA while its dynasty does)
        cands = [key] if kind in ("dynasty", "house") else []
        dynkey = None
        if kind == "house":
            nested = houses.get(key, (None, None))[1]
            if nested:
                cands.append(nested)
                dynkey = nested
        coa = None
        used = None
        for cand in cands:
            coa = find_house_coa(cand)
            if coa is not None and (coa["pattern"] or coa["emblems"]):
                used = cand
                break
            coa = None
        if coa is None and db is not None:
            # the dynasty's own record (what the dynasty displays in-game)
            # before the title's standalone design
            if kind == "dynasty":
                dynkey = key
            if dynkey is not None:
                didx = save_dynasty_coa(save_path, str(dynkey))
                if didx is not None and didx in db:
                    coa = db[didx]
                    used = f"save-dyn#{didx}"
        if coa is None and db is not None and kind is None:
            # dynasty-less ruler: the save generated a dynasty for him
            didx = save_char_dyn_coa(save_path, cid)
            if didx is not None and didx in db:
                coa = db[didx]
                used = f"save-char-dyn#{didx}"
        if coa is None and db is not None:
            tidx = save_title_coa(save_path, thandles.get(tag))
            if tidx is not None and tidx in db:
                coa = db[tidx]
                used = f"save#{tidx}"
        if coa is None:
            hint = (", no authored design and no --save given so far"
                    if db is None else "")
            why = (f"{kind}={key}: no CoA" if key else
                   f"ruler char {cid} has no dynasty")
            misses.append((tag, why + hint))
            continue
        out = bake(compose(coa), tag)
        done.append((tag, used))
        if not quiet:
            print(f"{tag:4} {used:24}")
    if misses:
        for tag, why in misses:
            print("MISS", f"{tag:4}", why)
    return done, misses


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tag", nargs="*", help="tag(s) to render")
    ap.add_argument("--house", help="house/dynasty key override (one tag)")
    ap.add_argument("--title", action="store_true",
                    help="render each tag's own CK3 landed-title arms"
                         " (ck3_title) instead of the ruler's house CoA")
    ap.add_argument("--all", action="store_true", help="all -ids dynasty tags")
    ap.add_argument("--dry", action="store_true",
                    help="print the CoA definition, no render")
    ap.add_argument("--save", metavar="PATH",
                    help="CK3 save carrying generated CoAs for the"
                         " dynasties with no authored design")
    a = ap.parse_args()
    if a.title and (a.house or a.all):
        ap.error("--title picks the landed-title arms; drop --house/--all")
    if a.title:
        if not a.tag:
            ap.error("--title needs at least one tag")
        handles = _tag_titles()
        done, misses = [], []
        for tag in a.tag:
            title = handles.get(tag)
            if not title:
                misses.append((tag, "no ck3_title in tags.db"))
                continue
            coa = find_house_coa(title)
            if coa is None or not (coa["pattern"] or coa["emblems"]):
                misses.append((tag, f"{title}: no authored CoA"))
                continue
            if a.dry:
                dump_coa(coa, f"{tag} {title}")
            else:
                bake(compose(coa), tag)
                print(f"{tag:4} {title:24}")
            done.append((tag, title))
        for tag, why in misses:
            print("MISS", f"{tag:4}", why)
        print(f"{len(done)} rendered, {len(misses)} misses")
    elif a.house or (a.dry and a.tag and not a.all):
        # explicit source override / definition dump: single tag only
        if len(a.tag) != 1:
            ap.error("--house/--dry needs exactly one tag")
        coa = find_house_coa(a.house)
        if coa is None:
            sys.exit(f"no authored CK3 CoA for {a.house}")
        if not a.dry:
            bake(compose(coa), a.tag[0])
        dump_coa(coa)
    elif a.all:
        done, misses = ruler_coa(save_path=a.save)
        print(f"{len(done)} rendered, {len(misses)} misses")
    elif a.tag:
        done, misses = ruler_coa(a.tag, save_path=a.save)
        print(f"{len(done)} rendered, {len(misses)} misses")
    else:
        ap.error("need a tag or --all")
