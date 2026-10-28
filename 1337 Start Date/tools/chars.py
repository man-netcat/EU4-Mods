"""EU5 1337 characters -> EU4 monarch/heir blocks."""
import re
from functools import lru_cache

from textfold import latin1
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


@lru_cache(None)
def dialect_languages():
    """{dialect: language} from EU5's languages files (a culture speaks a dialect or a language)."""
    out = {}
    for f in sorted((EU5_GAME / "in_game/common/languages").glob("*.txt")):
        for lang, body in parse(f.read_text(encoding="utf-8-sig")):
            if not isinstance(body, list):
                continue
            stack = [body]
            while stack:
                for k, v in stack.pop():
                    if isinstance(v, list):
                        if k and k.endswith("_dialect"):
                            out[k] = lang
                        stack.append(v)
    return out


@lru_cache(None)
def culture_languages():
    """{culture: (dialect or None, language)} from EU5's culture files."""
    out = {}
    dl = dialect_languages()
    for f in sorted((EU5_GAME / "in_game/common/cultures").glob("*.txt")):
        for cul, body in parse(f.read_text(encoding="utf-8-sig")):
            lang = get(body, "language") if isinstance(body, list) else None
            if lang:
                out[cul] = (lang, dl[lang]) if lang in dl else (None, lang)
    return out


def loc_name(key, culture):
    """EU5 name key -> text, in the form the character's culture uses (`name_john` is Johan, Ivan, Jean ...):
    key.<dialect>, key.<language>, then the plain key."""
    n = names()
    dialect, lang = culture_languages().get(culture, (None, None))
    for suffix in (dialect, lang):
        if suffix and f"{key}.{suffix}" in n:
            return n[f"{key}.{suffix}"]
    return n.get(key) or key.replace("name_", "").replace("_", " ").title()


def _name_piece(piece, culture=None):
    key = piece if piece.startswith("name_") else "name_" + piece
    return loc_name(key, culture)


def first_name(c, key=None):
    """The character's name (or the given regnal name key), or None when EU5 leaves it to the game (`random`)."""
    if key is None:
        fn = get(c, "first_name")
        key = get(fn, "name") if isinstance(fn, list) else fn
    if not key or key == "random":
        return None
    cul = get(c, "culture")
    return " ".join(_name_piece(p, cul) for p in key.split("."))


@lru_cache(None)
def dynasties():
    """{dynasty: (name key, type)} from EU5's 04_dynasties."""
    out = {}
    r = parse((EU5_SETUP / "04_dynasties.txt").read_text(encoding="utf-8-sig"))
    for top, body in r:
        if isinstance(body, list):
            for k, b in body:
                if isinstance(b, list):
                    nm = get(b, "name")
                    key = get(nm, "name") if isinstance(nm, list) else nm
                    out[k] = (key, get(b, "dynasty_name_type"))
    return out


def dynasty_name(c):
    """The dynasty's name: its own loc when EU5 has one (valois_dynasty), a patronymic from the key
    (rurikovich_dynasty), else the name key in the character's language."""
    d = get(c, "dynasty")
    if not d:
        return None
    if d in names():
        return names()[d]
    key, kind = dynasties().get(d, (None, None))
    if kind == "patronym" and d.endswith("_dynasty"):
        return d[:-len("_dynasty")].replace("_", " ").title()
    if key:
        return loc_name(key if key.startswith("name_") else "name_" + key, get(c, "culture"))
    return None


def ascii_name(s):
    import unicodedata
    return unicodedata.normalize("NFKC", s)


def block(cid, c, regnal=None, regnal_name=None, heir=False, indent="\t"):
    """EU4 monarch/heir body text."""
    # a throne name (Benedict XII) is the conventional English form, not the form of the ruler's own culture
    name = names().get(regnal_name) if regnal_name and names().get(regnal_name) else first_name(c, regnal_name)
    if name is None:
        return None
    if regnal:
        name += " " + roman(regnal)
    b = date(get(c, "birth_date"))
    if b is None:
        return None
    lines = [f'name = "{latin1(name)}"']
    if get(c, "female") == "yes":
        lines.append("female = yes")
    dyn = dynasty_name(c)
    if dyn:
        lines.append(f'dynasty = "{latin1(dyn)}"')
    lines.append("birth_date = %d.%d.%d" % b)
    if heir:
        lines.append("claim = 95")
    lines += [f"adm = {stat(c, 'adm')}", f"dip = {stat(c, 'dip')}", f"mil = {stat(c, 'mil')}"]
    return "\n".join(indent + l for l in lines)


def ruler_regnal(cid, tag_block):
    """(regnal number, regnal name key) of the ruler's open term; either may be None."""
    g = get(tag_block, "government") or []
    for rt in reversed(getall(g, "ruler_term")):
        if isinstance(rt, list) and get(rt, "character") == cid and get(rt, "end_date") is None:
            try:
                num = int(get(rt, "regnal_number"))
            except (TypeError, ValueError):
                num = None
            return num, get(rt, "regnal_name")
    return None, None


def country_rulers(b):
    """(ruler id, heir id or None) of an EU5 country block at the start date. The ruler is `ruler`; failing that the
    open-ended ruler_term; failing that, in a regency, the heir who reigns under it. `ruler = random` is the
    game's own to generate and gives None. The heir is the block's `heir`, else the eldest son."""
    g = get(b, "government")
    g = g if isinstance(g, list) else []
    rid = get(g, "ruler")
    chs = characters()
    if rid == "random":
        return None, None
    heir = get(g, "heir")
    if not rid:
        open_terms = [get(t, "character") for t in getall(g, "ruler_term") if isinstance(t, list) and get(t, "end_date") is None]
        rid = open_terms[-1] if open_terms else (heir if get(g, "active_regent") else None)
        if rid == heir:
            heir = None
    if rid not in chs or not alive(chs[rid]):
        return None, None
    if heir not in chs or not alive(chs[heir]):
        heir = find_heir(rid)[0]
    return rid, heir


def queen_block(cid, own_tag, tag_of=lambda t: None, indent="\t"):
    """EU4 queen body from the ruler's living spouse (None when there is none or no usable name)."""
    c = characters().get(cid)
    sp = get(c, "spouse") if c else None
    sc = characters().get(sp) if sp else None
    if not sc or not alive(sc) or get(sc, "female") == get(c, "female"):
        return None
    name = first_name(sc)
    b = date(get(sc, "birth_date"))
    if name is None or b is None:
        return None
    lines = [f"country = {tag_of(get(sc, 'tag')) or own_tag}", f'name = "{latin1(name)}"']
    dyn = dynasty_name(sc)
    if dyn:
        lines.append(f'dynasty = "{latin1(dyn)}"')
    lines.append("birth_date = %d.%d.%d" % b)
    if get(sc, "female") == "yes":
        lines.append("female = yes")
    lines += [f"adm = {stat(sc, 'adm')}", f"dip = {stat(sc, 'dip')}", f"mil = {stat(sc, 'mil')}"]
    return "\n".join(indent + l for l in lines)


def find_heir(cid):
    """eldest living son (fallback: eldest living child) of ruler as of 1337.4.1"""
    kids = [(date(get(c, "birth_date")), k, c) for k, c in characters().items()
            if get(c, "father") == cid and alive(c)]
    sons = [x for x in kids if get(x[2], "female") != "yes"]
    pick = sorted(sons or kids, key=lambda x: x[0])
    return (pick[0][1], pick[0][2]) if pick else (None, None)
