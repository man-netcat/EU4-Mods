"""EU5 1337 characters -> EU4 monarch/heir blocks."""
import re
from functools import lru_cache
from pdx import parse, get, getall
from paths import EU5_SETUP, EU5_GAME
from loc2prov import yml

L5 = EU5_GAME / "main_menu/localization/english"
START = (1337, 4, 1)
ROMAN = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def roman(n):
    out = ""
    for v, s in ROMAN:
        while n >= v:
            out += s
            n -= v
    return out


@lru_cache(None)
def names():
    out = {}
    for f in ("character_names_dynamic", "character_names", "dynasty_names"):
        out.update(yml(L5 / f"{f}_l_english.yml"))
    return out


@lru_cache(None)
def characters():
    r = parse((EU5_SETUP / "05_characters.txt").read_text(encoding="utf-8-sig"))
    db = get(r, "character_db") or []
    return {k: v for k, v in db if isinstance(v, list)}


def date(s):
    try:
        y, m, d = (int(x) for x in s.split("."))
        return (y, m, d)
    except (ValueError, AttributeError):
        return None


def alive(c):
    b, d = date(get(c, "birth_date")), date(get(c, "death_date"))
    return b is not None and b <= START and (d is None or d > START)


def stat(c, k):
    m = re.search(rf"\b{k}\s*=\s*(\d+)", "")
    v = get(c, k)
    try:
        return max(0, min(6, round(int(v) * 6 / 100)))
    except (TypeError, ValueError):
        return 3


def first_name(c):
    fn = get(c, "first_name")
    key = get(fn, "name") if isinstance(fn, list) else None
    return names().get(key) or (key or "Unknown").replace("name_", "").title()


def dynasty_name(c):
    d = get(c, "dynasty")
    return names().get(d) if d else None


def ascii_name(s):
    import unicodedata
    return unicodedata.normalize("NFKC", s)


def block(cid, c, regnal=None, heir=False, indent="\t"):
    """EU4 monarch/heir body text."""
    name = first_name(c)
    if regnal:
        name += " " + roman(regnal)
    b = date(get(c, "birth_date"))
    if b is None:
        return None
    lines = [f'name = "{name}"']
    if get(c, "female") == "yes":
        lines.append("female = yes")
    dyn = dynasty_name(c)
    if dyn:
        lines.append(f'dynasty = "{dyn}"')
    lines.append("birth_date = %d.%d.%d" % b)
    if heir:
        lines.append("death_date = %d.%d.%d" % (b[0] + 60, b[1], b[2]))
        lines.append("claim = 95")
    lines += [f"adm = {stat(c, 'adm')}", f"dip = {stat(c, 'dip')}", f"mil = {stat(c, 'mil')}"]
    return "\n".join(indent + l for l in lines)


def ruler_regnal(cid, tag_block):
    g = get(tag_block, "government") or []
    for rt in reversed(getall(g, "ruler_term")):
        if isinstance(rt, list) and get(rt, "character") == cid and get(rt, "end_date") is None:
            try:
                return int(get(rt, "regnal_number"))
            except (TypeError, ValueError):
                return None
    return None


def find_heir(cid):
    """eldest living son (fallback: eldest living child) of ruler as of 1337.4.1"""
    kids = [(date(get(c, "birth_date")), k, c) for k, c in characters().items()
            if get(c, "father") == cid and alive(c)]
    sons = [x for x in kids if get(x[2], "female") != "yes"]
    pick = sorted(sons or kids, key=lambda x: x[0])
    return (pick[0][1], pick[0][2]) if pick else (None, None)
