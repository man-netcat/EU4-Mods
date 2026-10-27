#!/usr/bin/env python3
"""Tag names as CK3 names the title for its 867 holder's culture.

CK3 titles carry per-culture names (`name_list_<list> = cn_x` in landed_titles,
localised as cn_x / cn_x_adj): Kiev is Könugarðr under a Norse holder, Dublin
is Dyflinn, Lena is Eülkhe for the Buryat. A tag takes the name of its title in
the holder's culture (the holder's culture's `name_list`), falling back to the
plain title name when CK3 has no cultural one. CK3 leaves the adjective out of
some cn_ names; the adjective then equals the name, as CK3's own `$cn_x$` does.

    python3 tools/culturalnames.py              # list tags that do not show it
    python3 tools/culturalnames.py apply TAG..  # write the cultural name and adjective
    python3 tools/culturalnames.py peoples      # list / write the "<place> <people>" names

Steppe peoples: a county or duchy held by a ruler of one of the Turkic steppe
cultures below is "<place> <people>" (Quriltay Oghuz, Akmola Kimeks, Targyl
Kipchaks, Tumar Cumans), the people's name being CK3's own culture name in the
plural (Oghuz and Kirghiz are invariant); the adjective keeps the singular. The
people's realm itself (Oghuz il, the Kirghiz Khanate) keeps its title name.
"""
import glob
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import CK3_GAME  # noqa: E402

MOD = os.path.join(HERE, "..")
LOC = os.path.join(MOD, "localisation", "replace", "countries_l_english.yml")
_blocks = {}

# CK3 holder cultures whose counties and duchies carry the people's name
PEOPLES = ("turkish", "pecheneg", "cuman", "kipchak", "kimek", "karluk", "kirghiz", "bashkir", "bolghar")


def _title_blocks():
    if _blocks:
        return _blocks
    for f in sorted(glob.glob(os.path.join(CK3_GAME, "common", "landed_titles", "*.txt"))):
        t = open(f, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"(?m)^(\t*)([ckde]_[\w\-]+)\s*=\s*\{", t):
            if m.group(2) in _blocks:
                continue
            i = j = m.end()
            d = 1
            while j < len(t) and d > 0:
                d += (t[j] == "{") - (t[j] == "}")
                j += 1
            body = t[i:j - 1]
            child = re.search(r"(?m)^\t*[bcdke]_[\w\-]+\s*=\s*\{", body)
            _blocks[m.group(2)] = body[:child.start()] if child else body
    return _blocks


def cultural_name(title):
    """(name, adjective) CK3 shows for the title under its 867 holder's culture, else (None, None)."""
    import ck3
    import culturelift as cl
    import culturetitles as ct

    _h, cc = cl.holder_culture(title)
    if not cc:
        return None, None
    nl = ct.culture_info(cc)[1]
    if not nl:
        return None, None
    nl = nl[len("name_list_"):] if nl.startswith("name_list_") else nl
    m = re.search(rf"name_list_{re.escape(nl)}\s*=\s*([\w\-]+)", _title_blocks().get(title, ""))
    if not m:
        return None, None
    name = ck3.loc(m.group(1))
    return name, (ck3.loc(m.group(1) + "_adj") or name) if name else None


def shown(tag, loc=None):
    loc = loc if loc is not None else open(LOC, encoding="utf-8-sig").read()

    def lk(k):
        m = re.search(rf'(?m)^ {re.escape(k)}:\d* "([^"]*)"', loc)
        return m.group(1) if m else None

    return lk(tag), lk(tag + "_ADJ")


def drifting(rows):
    """[(tag, title, cultural name, shown name)] for (tag, title) rows whose name is not the cultural one."""
    from enc import encname

    loc = open(LOC, encoding="utf-8-sig").read()
    out = []
    for tag, title in rows:
        name, _adj = cultural_name(title)
        have = shown(tag, loc)[0]
        if name and have is not None and encname(name) != have:
            out.append((tag, title, name, have))
    return out


def apply(tags):
    from enc import encname

    loc = open(LOC, encoding="utf-8-sig").read()
    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    for tag in tags:
        row = con.execute("select ck3_title from tags where tag=?", (tag,)).fetchone()
        if not row:
            sys.exit(f"{tag}: not in tags.db")
        name, adj = cultural_name(row[0])
        if not name:
            print(f"  {tag}: CK3 has no cultural name for {row[0]} under its holder's culture - skipped")
            continue
        for key, val in ((tag, name), (tag + "_ADJ", adj)):
            loc, k = re.subn(rf'(?m)^( {re.escape(key)}:\d* )"[^"]*"', lambda m: f'{m.group(1)}"{encname(val)}"', loc, count=1)
            if not k:
                sys.exit(f"{key}: no loc line to update")
        print(f"  {tag}: {shown(tag)[0]} -> {encname(name)} / {encname(adj)}")
    open(LOC, "w", encoding="utf-8-sig", newline="").write(loc)


INVARIANT_PEOPLES = ("Oghuz", "Kirghiz")


def plural_people(suf):
    """The people in the plural for the realm's name (Tumar Cumans); the adjective stays singular."""
    return suf if suf in INVARIANT_PEOPLES or suf.endswith("s") else suf + "s"


def people_suffix(title, rank):
    """The people a county/duchy tag is named after ("Oghuz" for CK3's turkish culture), else None."""
    import ck3
    import culturelift as cl

    if rank is None or rank > 2:
        return None
    _h, cc = cl.holder_culture(title)
    return ck3.loc(cc) if cc in PEOPLES else None


def people_drift(rows):
    """[(tag, shown name, wanted name)] for (tag, title, rank) rows missing their people suffix."""
    from enc import encname

    loc = open(LOC, encoding="utf-8-sig").read()
    out = []
    for tag, title, rank in rows:
        suf = people_suffix(title, rank)
        have = shown(tag, loc)[0]
        if suf and have is not None and not have.endswith(" " + encname(plural_people(suf))):
            out.append((tag, have, f"{have} {encname(plural_people(suf))}"))
    return out


def apply_peoples(tags=None):
    from enc import encname

    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    loc = open(LOC, encoding="utf-8-sig").read()
    for tag, title, rank in con.execute("select tag, ck3_title, rank from tags"):
        if tags and tag not in tags:
            continue
        suf = people_suffix(title, rank)
        if not suf:
            continue
        suf, pl = encname(suf), encname(plural_people(suf))
        name, adj = shown(tag, loc)
        if name is None or name.endswith(" " + pl):
            continue
        for key, val in ((tag, f"{name} {pl}"), (tag + "_ADJ", f"{adj} {suf}")):
            loc = re.sub(rf'(?m)^( {re.escape(key)}:\d* )"[^"]*"', lambda m: f'{m.group(1)}"{val}"', loc, count=1)
        print(f"  {tag}: {name} -> {name} {pl} / {adj} {suf}")
    open(LOC, "w", encoding="utf-8-sig", newline="").write(loc)


if __name__ == "__main__":
    if sys.argv[1:2] == ["peoples"]:
        apply_peoples()
    elif sys.argv[1:2] == ["apply"]:
        apply(sys.argv[2:])
    else:
        con = sqlite3.connect(os.path.join(HERE, "tags.db"))
        for t, title, want, have in drifting(con.execute("select tag, ck3_title from tags").fetchall()):
            print(f"{t:4} {title:20} CK3 cultural name {want!r}, shown {have!r}")
