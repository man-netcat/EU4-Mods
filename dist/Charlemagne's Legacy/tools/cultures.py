#!/usr/bin/env python3
"""common/cultures/00_cultures.txt: the CK3 cultures the mod uses, and nothing else.

A culture here IS a CK3 culture, under CK3's own key: `norse`, `anglo_saxon`, `han`. There is no
table between the two games. The file holds one entry per culture a province, tag or formable of
tags.db names, with the dynasty, male and female names of the name list CK3 gives that culture, and
the cultures sit in a group per CK3 heritage (`heritage_west_germanic` -> `west_germanic`). The
localisation is CK3's text: the culture's name, and the heritage's for the group. Nothing of either
game is stored here; the file is written whenever it differs, before anything reads it (tagdb reads
it on import).

    python3 tools/cultures.py          # rewrite the file and its localisation
    python3 tools/cultures.py --check  # exit 1 if either is stale
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import CK3_GAME  # noqa: E402

MOD = os.path.join(HERE, "..")
OUT = os.path.join(MOD, "common", "cultures", "00_cultures.txt")
LOC = os.path.join(MOD, "localisation", "karolingian_cultures_l_english.yml")
CK3_LISTS = os.path.join(str(CK3_GAME), "common", "culture", "name_lists")
CK3_CULTURES = os.path.join(str(CK3_GAME), "common", "culture", "cultures")

# EU4 draws a group's flags, units and portraits from a graphical set; this picks one per heritage
# (ours: CK3 has no such thing). The second set is EU4's fallback where it uses one.
GFX = {}
for _gfx, _heritages in (
    ("westerngfx", "west_germanic central_germanic north_germanic frankish latin iberian brythonic "
                   "goidelic balto_finnic volga_finnic ugro_permian magyar west_slavic gothic"),
    ("easterngfx", "south_slavic east_slavic baltic vlach albanian byzantine caucasian"),
    ("muslimgfx", "arabic berber iranian turkic israelite syriac tocharian"),
    ("asiangfx", "chinese buyeo korean japonic tibetan qiangic hmongic burman mongolic tungusic"),
    ("indiangfx", "indo_aryan dravidian"),
    ("africangfx", "akan bantu central_african east_african sahelian senegambian somalian west_african "
                   "yoruba"),
):
    for _h in _heritages.split():
        GFX["heritage_" + _h] = (_gfx, None)
for _h in "austronesian tai mon_khmer viet".split():
    GFX["heritage_" + _h] = ("southeastasiangfx", "asiangfx")
for _h in "ainuic nivkh".split():
    GFX["heritage_" + _h] = ("inuitgfx", "asiangfx")

_ck3_name_list = {}

def _read(path):
    return open(path, encoding="cp1252", errors="replace").read().replace("\r\n", "\n")


def ck3_culture_name_list(ck3cult):
    if not _ck3_name_list:
        for fn in sorted(os.listdir(CK3_CULTURES)):
            text = open(os.path.join(CK3_CULTURES, fn), encoding="utf-8-sig",
                        errors="replace").read()
            for m in re.finditer(r"(?m)^(\w+)\s*=\s*\{(.*?)^\}", text, re.S):
                nl = re.search(r"name_list\s*=\s*(\w+)", m.group(2))
                if nl:
                    _ck3_name_list[m.group(1)] = nl.group(1)
    return _ck3_name_list.get(ck3cult)


def _ck3_list_block(list_key):
    for fn in sorted(os.listdir(CK3_LISTS)):
        text = open(os.path.join(CK3_LISTS, fn), encoding="utf-8-sig", errors="replace").read()
        m = re.search(r"(?m)^%s\s*=\s*\{" % re.escape(list_key), text)
        if m:
            j, depth, k = text.index("{", m.start()), 0, text.index("{", m.start())
            while True:
                if text[k] == "{":
                    depth += 1
                elif text[k] == "}":
                    depth -= 1
                    if depth == 0:
                        return text[j + 1:k]
                k += 1
    return None


def _section(block, *names):
    for nm in names:
        i = block.find(nm)
        if i < 0:
            continue
        j = block.find("{", i)
        depth, k = 0, j
        while True:
            if block[k] == "{":
                depth += 1
            elif block[k] == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        return block[j + 1:k]
    return ""


def _tokens(text):
    return re.findall(r'"([^"]+)"|(\S+)', text)


def _clean(tok):
    tok = re.sub(r"\s+", " ", tok.replace("_", " ")).strip()
    try:
        tok.encode("cp1252")
    except UnicodeEncodeError:
        return None
    return tok or None


def ck3_names(ck3cult):
    """(dynasties, males, females) of the name list a CK3 culture names."""
    key = ck3_culture_name_list(ck3cult)
    block = _ck3_list_block(key) if key else None
    if not block:
        raise SystemExit(f"cultures: CK3 culture {ck3cult} has no name list")

    def names(*sections, strip=""):
        out = []
        for t in _tokens(_section(block, *sections)):
            tok = t[0] or t[1]
            if strip:
                if not tok.startswith(strip):
                    continue
                tok = tok[len(strip):]
            c = _clean(tok)
            if c:
                out.append(c)
        return list(dict.fromkeys(out))

    dyns = names("cadet_dynasty_names", "dynasty_names", strip="dynn_")
    males, females = names("male_names"), names("female_names")
    if dyns and not (males and females) and not _fallback:
        # a CK3 list may name only dynasties (Yemeni): its heritage's first culture with names lends its own
        h = ck3_heritage(ck3cult)
        for other in sorted(k for k in _heritage_all() if _heritage_all()[k] == h and k != ck3cult):
            _fallback.append(other)
            try:
                _d, m2, f2 = ck3_names(other)
            except SystemExit:
                _fallback.clear()
                continue
            _fallback.clear()
            males, females = males or m2, females or f2
            break
    if not (dyns and males and females):
        raise SystemExit(f"cultures: short name list for {ck3cult}: "
                         f"{len(dyns)}/{len(males)}/{len(females)}")
    return dyns, males, females


def _q(tok):
    return f'"{tok}"' if re.search(r"[^A-Za-z0-9_'-]", tok) else tok


def _wrap(items):
    lines, cur = [], "\t\t\t"
    for tok in items:
        tok = _q(tok)
        if len(cur) + len(tok) + 1 > 110:
            lines.append(cur.rstrip())
            cur = "\t\t\t"
        cur += tok + " "
    lines.append(cur.rstrip())
    return lines


def _list_lines(key, items):
    return [f"\t\t{key} = {{"] + _wrap(items) + ["\t\t}"]


_fallback = []
_heritage = {}


def _heritage_all():
    ck3_heritage("norse")
    return _heritage


def ck3_heritage(culture):
    """The CK3 heritage key of a CK3 culture (`heritage_west_germanic`), or None."""
    if not _heritage:
        for fn in sorted(os.listdir(CK3_CULTURES)):
            t = open(os.path.join(CK3_CULTURES, fn), encoding="utf-8-sig", errors="replace").read()
            for m in re.finditer(r"(?m)^(\w+)\s*=\s*\{(.*?)^\}", t, re.S):
                h = re.search(r"heritage\s*=\s*(\w+)", m.group(2))
                if h:
                    _heritage[m.group(1)] = h.group(1)
    return _heritage.get(culture)


def group_of(culture):
    h = ck3_heritage(culture)
    return h[len("heritage_"):] if h else None


def culture_lines(key):
    dyns, males, females = ck3_names(key)
    out = [f"\t{key} = {{"]
    out += _list_lines("dynasty_names", dyns) + _list_lines("male_names", males)
    out += _list_lines("female_names", females)
    out.append("\t}")
    return out


def used_in_db():
    """Cultures the tag database names: provinces, tags, formables and formable renames."""
    import sqlite3

    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    used = set()
    for q in ("select culture from provinces", "select culture from tags",
              "select culture from formables", "select culture from formable_renames"):
        for (c,) in con.execute(q):
            used |= set((c or "").split())
    con.close()
    return used


def needed():
    return used_in_db()


def build_text():
    by_group = {}
    for c in sorted(needed()):
        g = group_of(c)
        if g is None:
            raise SystemExit(f"cultures: {c} is not a CK3 culture (tags.db names it)")
        by_group.setdefault(g, []).append(c)
    out = ["# Written by tools/cultures.py from CK3's cultures, name lists and heritages. Do not edit.", ""]
    for g in sorted(by_group):
        gfx, second = GFX.get("heritage_" + g, ("westerngfx", None))
        out.append(f"{g} = {{")
        out.append(f"\tgraphical_culture = {gfx}")
        if second:
            out.append(f"\tsecond_graphical_culture = {second}")
        for c in by_group[g]:
            out += [""] + culture_lines(c)
        out += ["}", ""]
    return "\n".join(out).rstrip("\n") + "\n"


_loc_cache = {}


def ck3_loc(keys):
    """CK3's English text for each wanted key (own reader: tagdb imports this
    module while ck3.py is still loading, so ck3.loc is not available here)."""
    want = set(keys) - set(_loc_cache)
    if want:
        rx = re.compile(r'^\s*(%s):\d*\s+"(.*)"' % "|".join(re.escape(k) for k in want))
        root = os.path.join(str(CK3_GAME), "localization", "english")
        for dp, _dn, fns in os.walk(root):
            for fn in sorted(fns):
                if not fn.endswith(".yml"):
                    continue
                for ln in open(os.path.join(dp, fn), encoding="utf-8-sig", errors="replace"):
                    m = rx.match(ln)
                    if m and m.group(1) not in _loc_cache:
                        _loc_cache[m.group(1)] = m.group(2)
        for k in want:
            _loc_cache.setdefault(k, None)
    return {k: _loc_cache[k] for k in keys}


def _loc_text(pairs):
    seen, lines = set(), ["l_english:"]
    for k, v in pairs:
        if k not in seen:
            seen.add(k)
            lines.append(f' {k}:0 "{v}"')
    return "\n".join(lines) + "\n"


def loc_text():
    cults = sorted(needed())
    groups = sorted({group_of(c) for c in cults})
    got = ck3_loc(cults + ["heritage_" + g for g in groups])
    pairs = [(g, got["heritage_" + g]) for g in groups if got.get("heritage_" + g)]
    pairs += [(c, got[c]) for c in cults if got.get(c)]
    return _loc_text(pairs)


def targets():
    return [(OUT, build_text(), "cp1252"), (LOC, loc_text(), "utf-8-sig")]


def write(check=False):
    stale = []
    for path, text, enc in targets():
        old = None
        if os.path.exists(path):
            old = open(path, encoding=enc, errors="replace", newline="").read()
        if old != text:
            stale.append(path)
            if not check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding=enc, errors="replace", newline="") as f:
                    f.write(text)
    return stale


_done = False


def ensure():
    """Write the file once per process, before anything reads it."""
    global _done
    if not _done:
        _done = True
        if not os.environ.get("KAR_NO_ENSURE"):  # set while tags.db is being migrated
            write()


def known():
    ensure()
    return set(re.findall(r"(?m)^\t([A-Za-z0-9_]+) = \{", _read(OUT))) - {"dynasty_names", "male_names", "female_names"}


if __name__ == "__main__":
    check = "--check" in sys.argv
    stale = write(check)
    for p in stale:
        print(("stale: " if check else "wrote ") + os.path.relpath(p, MOD))
    sys.exit(1 if (check and stale) else 0)
