#!/usr/bin/env python3
"""Tag names and adjectives, lifted from CK3 at build time.

Nothing of CK3's text is stored in the repo: every tag's name and adjective is
read from CK3's localisation on each build and written to
localisation/replace/countries_l_english.yml. How a tag is named is one of

  ck3      the title's name for its 867 holder's culture (culturalnames), else
           the plain title name; steppe counties and duchies take their people
           as a suffix ("Quriltay Oghuz"). Scripted `$key$` references resolve.
  dynasty  the realm is named for its 867 ruler's dynasty ("Samanids" /
           "Samanid"), the dynasty being CK3's own
  custom   our own wording (tag_names.name / adj), for realms CK3 has no name
           for in this sense ("Great Tang", "West Francia"). Own text, no CK3 data.
  vanilla  the base game's loc stays (nothing written)

The mode lives in tags.db (table tag_names; tags without a row are `ck3`).
Everything is folded to what EU4's font renders (enc.fold_loc).

    python3 tools/tagloc.py            # compare the written loc with what CK3 gives
    python3 tools/tagloc.py write      # rewrite the tag lines of the loc file
    python3 tools/tagloc.py seed       # one-off: classify the current loc into modes
"""
import difflib
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

DB = os.path.join(HERE, "tags.db")
SCHEMA = ("create table if not exists tag_names ("
          "tag text primary key references tags(tag), mode text not null, name text, adj text)")


def _db():
    con = sqlite3.connect(DB)
    con.execute(SCHEMA)
    return con


def _resolve(s, depth=0):
    """CK3 scripted loc: `$key$` stands for that key's text; None while one stays unresolved."""
    import ck3

    if s is None:
        return None

    def sub(m):
        v = ck3.loc(m.group(1))
        return _resolve(v, depth + 1) if v and depth < 4 else None

    out = re.sub(r"\$([\w\-]+)\$", lambda m: sub(m) or "\0", s)
    return None if "\0" in out else out


def title_names(title, rank):
    """(name, adjective) of mode `ck3`, folded; None when CK3 has no name."""
    import ck3
    import culturalnames as cn
    from enc import fold_loc

    name, adj = cn.cultural_name(title)
    if not name:
        name = ck3.loc(title)
        adj = ck3.loc(title + "_adj")
    name = _resolve(name)
    if not name:
        return None
    adj = _resolve(adj) or name
    name, adj = fold_loc(name), fold_loc(adj)
    suf = cn.people_suffix(title, rank)
    if suf:
        name, adj = f"{name} {fold_loc(suf)}", f"{adj} {fold_loc(suf)}"
    return name, adj


def dynasty_names(dynasty):
    from enc import fold_loc

    d = fold_loc(dynasty)
    return (d + "s" if d.lower().endswith("id") else d), d


def dynasty_of(tag, _ctx=[]):
    import ck3

    if not _ctx:
        _ctx.append((ck3.load_titles(), ck3.load_chars(), ck3.load_dynasties(), ck3.load_houses()))
    try:
        return ck3.resolve(tag, *_ctx[0]).get("dynasty")
    except Exception:
        return None


def names_of(tag, title, rank, row):
    """(name, adjective) a tag shows, or None when the base game's loc stays."""
    mode = row[0] if row else "ck3"
    if mode == "vanilla":
        return None
    if mode == "custom":
        return row[1], row[2] or row[1]
    if mode == "dynasty":
        d = dynasty_of(tag, )
        return dynasty_names(d) if d else None
    return title_names(title, rank)


def wanted():
    con = _db()
    rows = {t: (m, n, a) for t, m, n, a in con.execute("select tag, mode, name, adj from tag_names")}
    return {tag: names_of(tag, title, rank, rows.get(tag))
            for tag, title, rank in con.execute("select tag, ck3_title, rank from tags order by seq")}


def _loc_path():
    import culturalnames as cn

    return cn.LOC


def write():
    path = _loc_path()
    loc = open(path, encoding="utf-8-sig", newline="").read()
    nl = "\r\n" if "\r\n" in loc else "\n"
    lines = loc.split(nl)
    for tag, got in wanted().items():
        if got is None:
            continue
        for key, val in ((tag, got[0]), (tag + "_ADJ", got[1])):
            for i, ln in enumerate(lines):
                if ln.startswith(f" {key}:"):
                    lines[i] = re.sub(r'"[^"]*"$', lambda m: f'"{val}"', ln)
                    break
            else:
                anchor = lines.index(' HLR:1 "Karolingian Empire"')
                lines.insert(anchor, f' {key}:1 "{val}"')
    new = nl.join(lines)
    if new != loc:
        open(path, "w", encoding="utf-8-sig", newline="").write(new)
    return new != loc


def drift():
    """[(tag, have, wanted)] for tags whose loc is not what CK3 gives."""
    import culturalnames as cn

    loc = open(_loc_path(), encoding="utf-8-sig").read()
    return [(t, cn.shown(t, loc), w) for t, w in wanted().items()
            if w is not None and cn.shown(t, loc) != w]


def step_tagloc():
    """Build step: write every tag's name and adjective from CK3."""
    changed = write()
    print("  tag names lifted from CK3" + (" (loc rewritten)" if changed else " (unchanged)"))
    return 0


def seed():
    """Classify the loc as it stands: ck3 where it is CK3's, dynasty where it names the dynasty,
    else our own wording kept as `custom`. Prints the custom ones for review."""
    import culturalnames as cn
    from enc import _slug

    con = _db()
    loc = open(_loc_path(), encoding="utf-8-sig").read()
    vanilla = _vanilla_tags()
    con.execute("delete from tag_names")
    custom = []
    for tag, title, rank in con.execute("select tag, ck3_title, rank from tags order by seq").fetchall():
        have = cn.shown(tag, loc)
        if have[0] is None:
            if tag in vanilla:
                con.execute("insert into tag_names values (?,?,?,?)", (tag, "vanilla", None, None))
            continue
        want = title_names(title, rank)
        if want and want[0] == have[0]:
            continue
        d = dynasty_of(tag)
        if d:
            dn = dynasty_names(d)
            if difflib.SequenceMatcher(None, _slug(have[0]).lower(), _slug(dn[0]).lower()).ratio() >= 0.8:
                con.execute("insert into tag_names values (?,?,?,?)", (tag, "dynasty", None, None))
                continue
        con.execute("insert into tag_names values (?,?,?,?)", (tag, "custom", have[0], have[1]))
        custom.append((tag, title, have, want))
    con.commit()
    for c in custom:
        print("  custom", *c)
    print(len(custom), "custom")


def _vanilla_tags():
    from paths import EU4_GAME

    p = os.path.join(EU4_GAME, "common", "country_tags", "00_countries.txt")
    return set(re.findall(r"(?m)^([A-Z][A-Z0-9]{2})\s*=", open(p, encoding="cp1252", errors="replace").read()))


if __name__ == "__main__":
    a = sys.argv[1:2]
    if a == ["write"]:
        print("rewritten" if write() else "unchanged")
    elif a == ["seed"]:
        seed()
    else:
        d = drift()
        for t, have, want in d:
            print(f"{t:4} have {have} / CK3 {want}")
        print(len(d), "differ")
