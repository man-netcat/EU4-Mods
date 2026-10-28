"""EU5 country facts: names, colours, culture/religion definition, government heuristics, capital, ruler."""
import colorsys, glob, re
from functools import lru_cache
from pdx import parse, get, getall
from paths import EU5_GAME
from loc2prov import yml
from eu5setup import countries

L5 = EU5_GAME / "main_menu/localization/english"


@lru_cache(None)
def loc():
    out = {}
    for f in ("country_names", "area", "province_names", "region_names", "scripted_geography_names", "name_structs"):
        p = L5 / f"{f}_l_english.yml"
        if p.exists():
            out.update(yml(p))
    for f in (L5 / "location_names").glob("location_names_l_english.yml"):
        out.update(yml(f))
    return out


def display(key, fallback=None):
    v = loc().get(key)
    seen = 0
    while v and v.startswith("$") and v.endswith("$") and seen < 4:
        v = loc().get(v.strip("$"), v.strip("$"))
        seen += 1
    if v and "[" in v:
        v = None
    return v or fallback or key.replace("_", " ").title()


@lru_cache(None)
def named_colors():
    out = {}
    for f in sorted(glob.glob(str(EU5_GAME / "main_menu/common/named_colors/*.txt"))):
        r = parse(open(f, encoding="utf-8-sig").read())
        for k, b in get(r, "colors") or []:
            out[k] = b
    return out


def rgb_of(c):
    """colour value: str name or [(None,'rgb')...]; returns (r,g,b) or None"""
    if isinstance(c, str):
        return rgb_of(named_colors().get(c)) if c in named_colors() else None
    return None


def parse_color(text_tokens):
    return None


@lru_cache(None)
def country_defs():
    """tag -> dict(color=(r,g,b), culture, religion)"""
    out = {}
    pat_rgb = re.compile(r"color\s*=\s*(rgb|hsv360|hsv)\s*\{([^}]*)\}")
    for f in sorted(glob.glob(str(EU5_GAME / "in_game/setup/countries/*.txt"))):
        text = open(f, encoding="utf-8-sig").read()
        for m in re.finditer(r"^([A-Za-z0-9_]+)\s*=\s*\{(.*?)^\}", text, re.M | re.S):
            body = m[2]
            col = None
            mm = pat_rgb.search(re.sub(r"#.*", "", body).replace("color2", "xx"))
            if mm:
                col = to_rgb(mm[1], mm[2].split())
            else:
                mn = re.search(r"^\s*color\s*=\s*(\w+)", body, re.M)
                if mn and mn[1] in named_colors():
                    v = named_colors()[mn[1]]
                    col = v
            cul = re.search(r"culture_definition\s*=\s*(\w+)", body)
            rel = re.search(r"religion_definition\s*=\s*(\w+)", body)
            out[m[1]] = dict(color=col, culture=cul and cul[1], religion=rel and rel[1])
    # resolve named colour entries parsed by pdx as lists
    return out


NAMED_RGB = {}


def to_rgb(kind, v):
    v = [float(x) for x in v]
    if kind == "rgb":
        return tuple(int(x) for x in v)
    h, s, val = v[0] / 360.0, v[1] / 100.0, v[2] / 100.0
    r, g, b = colorsys.hsv_to_rgb(h, s, val)
    return (round(r * 255), round(g * 255), round(b * 255))


@lru_cache(None)
def named_rgb():
    out = {}
    text = ""
    for f in sorted(glob.glob(str(EU5_GAME / "main_menu/common/named_colors/*.txt"))):
        text += open(f, encoding="utf-8-sig").read() + "\n"
    for m in re.finditer(r"^\s*(\w+)\s*=\s*(rgb|hsv360|hsv)\s*\{([^}]*)\}", text, re.M):
        try:
            out[m[1]] = to_rgb(m[2], m[3].split())
        except ValueError:
            pass
    return out


def color_of(tag):
    d = country_defs().get(tag)
    c = d and d["color"]
    if isinstance(c, tuple):
        return tuple(max(0, min(255, int(v))) for v in c)
    # named colour: re-read raw
    for f in sorted(glob.glob(str(EU5_GAME / "in_game/setup/countries/*.txt"))):
        text = open(f, encoding="utf-8-sig").read()
        m = re.search(r"^%s\s*=\s*\{(.*?)^\}" % re.escape(tag), text, re.M | re.S)
        if m:
            mn = re.search(r"^\s*color\s*=\s*(\w+)\s*$", m[1], re.M)
            if mn and mn[1] in named_rgb():
                return tuple(max(0, min(255, int(v))) for v in named_rgb()[mn[1]])
    return None


def gov_type(b):
    g = get(b, "government") or []
    t = get(g, "type") if isinstance(g, list) else None
    if t:
        return {"tribe": "tribe", "steppe_horde": "horde"}.get(t, t)
    inc = " ".join(getall(b, "include"))
    if re.search(r"horde", inc):
        return "horde"
    if re.search(r"tribe|clan", inc):
        return "tribe"
    if re.search(r"republic|free_city|hansa", inc):
        return "republic"
    if re.search(r"bishopric|abbey|theocracy|military_order", inc):
        return "theocracy"
    return "monarchy"


@lru_cache(None)
def info():
    out = {}
    for tag, b in countries():
        g = get(b, "government") or []
        out[tag] = dict(
            gov=gov_type(b), rank=get(b, "country_rank"), capital=get(b, "capital"),
            ruler=get(g, "ruler") if isinstance(g, list) else None,
            dynasty=get(b, "dynasty"), tech=get(b, "starting_technology_level"),
        )
    return out
