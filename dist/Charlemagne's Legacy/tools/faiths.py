#!/usr/bin/env python3
"""EU4 religions are CK3 faiths.

Every religion the mod uses is the lift of exactly one CK3 faith: its name,
map colour and icon come from CK3, and a tag's religion is the religion of
the faith its 867 ruler's rite belongs to (rite -> CK3 faith, which is the religion's own key;
CK3 groups rites under faiths in common/religion/rite_types). religions.TEMPLATE
says which base-game block a faith copies the mechanics of.

Usage (from the mod folder):
    python3 tools/faiths.py            # rewrite the religions file, its loc and the
                                       # interface sprites (tools/religions.py)
    python3 tools/faiths.py icons      # copy the CK3 faith icons over the religion
                                       # strips and the CK3 rite icons over the
                                       # rite placeholders (needs the CK3 install)
validate runs faiths.verify(): faith mapped, colour and name equal CK3's,
icons present, and by name which icons are still placeholders.
"""
import glob
import os
import re
import sys

from paths import CK3_GAME

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(HERE, "..")
REL_FILE = os.path.join(MOD, "common", "religions", "00_religion.txt")
LOC_FILE = os.path.join(MOD, "localisation", "replace", "karolingian_religion_l_english.yml")

# ---- CK3 data ---------------------------------------------------------------

def ck3_rites():
    """{rite: faith} for every rite CK3 defines (None when a rite names none)."""
    out = {}
    for f in glob.glob(os.path.join(CK3_GAME, "common", "religion", "rite_types", "*.txt")):
        text = open(f, encoding="utf-8-sig", errors="replace").read()
        for m in re.finditer(r"^(\w+)\s*=\s*\{(.*?)^\}", text, re.M | re.S):
            fm = re.search(r"^\s*faith\s*=\s*(\w+)", m.group(2), re.M)
            out[m.group(1)] = fm.group(1) if fm else None
    return out


def known_faiths():
    """The CK3 faiths the mod can use: the ones religions.TEMPLATE knows a block for."""
    import religions

    return set(religions.TEMPLATE)


def rite_religion_map():
    """{CK3 rite: EU4 religion} through the rite's faith (rites of unmapped faiths are left out)."""
    known = known_faiths()
    return {r: f for r, f in ck3_rites().items() if f in known}


def _rgb(raw):
    if raw.lstrip().startswith("hsv"):  # CK3 colours may be hsv { h s v }
        import colorsys

        h, sat, v = (float(n) for n in raw.replace("{", " ").replace("}", " ").split()[1:4])
        return tuple(int(c * 255 + 0.5) for c in colorsys.hsv_to_rgb(h, sat, v))
    nums = raw.replace("{", " ").replace("}", " ").split()
    if any("." in n for n in nums):
        return tuple(int(float(n) * 255 + 0.5) for n in nums)
    return tuple(int(n) for n in nums)


def ck3_faith(faith):
    """{'name', 'color', 'icon'} of a CK3 faith, from its faith_types block and localisation."""
    blk = None
    for f in glob.glob(os.path.join(CK3_GAME, "common", "religion", "faith_types", "*.txt")):
        t = open(f, encoding="utf-8-sig", errors="replace").read()
        m = re.search(rf"^{faith} = \{{(.*?)^\}}", t, re.M | re.S)
        if m:
            blk = m.group(1)
            break
    if blk is None:
        return None
    col = re.search(r"color\s*=\s*((?:hsv|rgb)?\s*\{[^}]*\})", blk)
    ic = re.search(r"icon\s*=\s*(\w+)", blk)
    name = None
    for f in glob.glob(os.path.join(CK3_GAME, "localization", "english", "**", "*.yml"), recursive=True):
        if "relig" not in f and "faith" not in f:
            continue
        lm = re.search(rf'^ {faith}:\d* "([^"]*)"', open(f, encoding="utf-8-sig", errors="replace").read(), re.M)
        if lm:
            name = lm.group(1)
            break
    if name:
        from enc import encname

        name = encname(name)  # the game drops strings with glyphs outside Latin-1 (Shintōism -> Shintoism)
    return {"name": name, "color": _rgb(col.group(1)) if col else None,
            "icon": ic.group(1) if ic else faith}  # no icon = N: CK3 uses <faith>.dds


# CK3 religion -> EU4 religion group. Every other religion of the pagan family (rf_pagan) is `pagan`.
CK3_RELIGION_GROUP = {
    "christianity_religion": "christian",
    "islam_religion": "muslim",
    "judaism_religion": "jewish_group",
    "dualism_religion": "zoroastrian_group",
    "zoroastrianism_religion": "zoroastrian_group",
    "hinduism_religion": "dharmic",
    "jainism_religion": "dharmic",
    "buddhism_religion": "eastern",
    "confucianism_religion": "eastern",
    "taoism_religion": "eastern",
}


def ck3_religion_of(faith):
    """The CK3 religion a faith belongs to (faith_types `religion = ...`), or None."""
    for f in glob.glob(os.path.join(CK3_GAME, "common", "religion", "faith_types", "*.txt")):
        t = open(f, encoding="utf-8-sig", errors="replace").read()
        m = re.search(rf"^{faith} = \{{(.*?)^\}}", t, re.M | re.S)
        if m:
            r = re.search(r"religion\s*=\s*(\w+)", m.group(1))
            return r.group(1) if r else None
    return None


def expected_group(faith):
    rel = ck3_religion_of(faith)
    return CK3_RELIGION_GROUP.get(rel, "pagan" if rel else None)


def religion_groups(text):
    """{religion: group} of the generated religions file."""
    out, cur = {}, None
    for ln in text.split("\n"):
        m = re.match(r"^(\w+) = \{", ln)
        if m:
            cur = m.group(1)
        m = re.match(r"^\t(\w+) = \{", ln)
        if m and cur:
            out[m.group(1)] = cur
    return out


def group_misfits():
    """[(religion, group in the file, group CK3's family says)]"""
    have = religion_groups(_read(REL_FILE))
    out = []
    for key, group in have.items():
        if key in known_faiths():
            want = expected_group(key)
            if want and group != want:
                out.append((key, group, want))
    return out


def religion_of_faith():
    return {f: f for f in known_faiths()}


# ---- the 00_religion.txt side ----------------------------------------------

def _read(path, enc="cp1252"):
    raw = open(path, "rb").read().decode(enc)
    return raw


def block_span(text, key):
    m = re.search(rf"^\t{re.escape(key)}\s*=\s*\{{", text, re.M)
    if not m:
        return None
    depth, i = 0, m.end() - 1
    while True:
        c = text[i]
        if c == "#":
            i = text.index("\n", i)
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return m.start(), i + 1
        i += 1


def religion_color(text, key):
    sp = block_span(text, key)
    m = re.search(r"^\t\tcolor\s*=\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}", text[sp[0]:sp[1]], re.M)
    return tuple(int(x) for x in m.groups()) if m else None


def lifted_name(text, key):
    m = re.search(rf'^ {re.escape(key)}:\d* "([^"]*)"', text, re.M)
    return m.group(1) if m else None


def _placeholder_icon(key):
    from PIL import Image, ImageDraw

    scratch = os.environ.get("TMPDIR", "/tmp")
    path = os.path.join(scratch, f"placeholder_{key}.png")
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((2, 2, 61, 61), fill=(200, 200, 200, 255), outline=(255, 255, 255, 255), width=3)
    d.text((24, 26), key[0].upper(), fill=(0, 0, 0, 255))
    im.save(path)
    return path


# ---- icons (needs the CK3 install) ------------------------------------------

def ck3_icon_file(faith):
    info = ck3_faith(faith)
    if not info or not info["icon"]:
        return None
    p = os.path.join(CK3_GAME, "gfx", "interface", "icons", "faith", info["icon"] + ".dds")
    return p if os.path.exists(p) else None


def lift_icons():
    import addreligion

    text = _read(REL_FILE)
    done = 0
    for faith in sorted(known_faiths()):
        key = faith
        sp = block_span(text, key)
        if sp is None:
            continue
        icon = re.search(r"(?m)^\t\ticon\s*=\s*(\d+)", text[sp[0]:sp[1]])
        src = ck3_icon_file(faith)
        if not icon or not src:
            print(f"  {key}: no icon line or no CK3 icon file for {faith} - skipped")
            continue
        addreligion.replace_frame(src, int(icon.group(1)))
        done += 1
    print(f"{done} religion icons replaced with the CK3 faith icons")
    import rites

    rites.lift_icons(force="--force" in sys.argv)


# ---- verification ------------------------------------------------------------

def verify(used):
    """Errors and warnings for the religions in `used`: each is the lift of one
    CK3 faith (name, colour), and its icon state is reported by name."""
    err, warn = [], []
    text = _read(REL_FILE)
    loc = open(LOC_FILE, encoding="utf-8-sig").read()
    by_rel = religion_of_faith()
    placeholder, unverified = [], []
    strips = os.path.join(MOD, "gfx", "interface", "icon_religion.dds")
    have_strips = os.path.exists(strips)  # the strips are images: made locally, not by the text build
    for rel in used:
        faith = by_rel.get(rel)
        if faith is None:
            err.append(f"religion '{rel}' is not a CK3 faith the mod has a block for (religions.TEMPLATE)")
            continue
        info = ck3_faith(faith)
        if info is None or info["color"] is None:
            err.append(f"religion '{rel}': CK3 faith '{faith}' not found in faith_types")
            continue
        if block_span(text, rel) is None:
            err.append(f"religion '{rel}' (CK3 {faith}) has no block in 00_religion.txt - run tools/faiths.py")
            continue
        have = religion_color(text, rel)
        if have != info["color"]:
            err.append(f"religion '{rel}': colour {have} is not CK3 {faith}'s {info['color']} - run tools/faiths.py")
        if lifted_name(loc, rel) != info["name"]:
            err.append(f"religion '{rel}': name {lifted_name(loc, rel)!r} is not CK3 {faith}'s {info['name']!r} - run tools/faiths.py")
        src = ck3_icon_file(faith)
        if not have_strips:
            continue
        if _icon_matches(text, rel, _placeholder_icon(rel)):
            placeholder.append(rel)  # still the generated stand-in frame
        elif src is None:
            unverified.append(rel)
        elif not _icon_matches(text, rel, src):
            placeholder.append(rel)
    seen = {}
    for rel in used:
        sp = block_span(text, rel)
        m = re.search(r"(?m)^\t\ticon\s*=\s*(\d+)", text[sp[0]:sp[1]]) if sp else None
        if m:
            seen.setdefault(int(m.group(1)), []).append(rel)
    for n, rels in sorted(seen.items()):
        if len(rels) > 1:
            err.append(f"religions {', '.join(rels)} share icon frame {n} - each lifted faith needs its own frame")
    if not have_strips:
        warn.append("religion icon strips are not built here (gfx/interface/icon_religion.dds is missing): icons not checked")
    if placeholder:
        warn.append("religion icons that are placeholders or not CK3's yet (run tools/faiths.py icons locally): " + ", ".join(placeholder))
    if unverified:
        warn.append("religion icons not checked against CK3 (CK3 icon files not on this machine): " + ", ".join(unverified))
    return err, warn


def _icon_matches(text, rel, src):
    import addreligion

    sp = block_span(text, rel)
    icon = re.search(r"(?m)^\t\ticon\s*=\s*(\d+)", text[sp[0]:sp[1]])
    return bool(icon) and addreligion.frame_matches(src, int(icon.group(1)))


if __name__ == "__main__":
    if sys.argv[1:2] == ["icons"]:
        lift_icons()
    else:
        import religions

        religions.write()
