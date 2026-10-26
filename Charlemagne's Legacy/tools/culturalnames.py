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


if __name__ == "__main__":
    if sys.argv[1:2] == ["apply"]:
        apply(sys.argv[2:])
    else:
        con = sqlite3.connect(os.path.join(HERE, "tags.db"))
        for t, title, want, have in drifting(con.execute("select tag, ck3_title from tags").fetchall()):
            print(f"{t:4} {title:20} CK3 cultural name {want!r}, shown {have!r}")
