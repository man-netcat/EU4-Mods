#!/usr/bin/env python3
"""Tag names and adjectives, derived from CK3 at build time.

Nothing of CK3's text is stored in the repo and nothing is hand-chosen: the
name a tag shows is the name CK3 shows for its title at 867.1.1, derived by:

  0. dynasty-named realms (CK3's `dynasty_named_realms`: "Abbasid", "Samanid"):
     a duchy or higher whose 867 ruler is of Arabic, Berber or Iranian heritage
     is named for his dynasty, unless the title opts out
     (`can_be_named_after_dynasty = no`) or its government does not name realms
     after dynasties (`dynasty_named_realms`: feudal, clan and mandala do,
     tribal does not; a title whose history pins no government takes the default). CK3's own form is the dynasty's name
     ("Abbasid"); we show the plural "Abbasids" for a dynasty ending in -id;
  1. the title's history: the latest dated `name = KEY` / `set_title_name = KEY`
     at or before the start (k_france is WEST_FRANCIA, d_normandy NEUSTRIA,
     h_china dynn_title_tang), the name being CK3's loc for KEY and its
     adjective KEY_adj;
  2. else the title's cultural name for its 867 holder's culture (landed_titles
     `name_list_<list> = cn_x`, see culturalnames);
  3. else the title's own loc (`<title>`, `<title>_adj`).

The adjective falls back to the name when CK3 gives none; scripted `$key$`
references are resolved; counties and duchies of the steppe peoples take the
people as a suffix ("Quriltay Oghuz"); the result is folded to what EU4's
font renders (enc.fold_loc).

    python3 tools/tagloc.py            # compare the written loc with what CK3 gives
    python3 tools/tagloc.py write      # rewrite the tag lines of the loc file
Style preferences (STYLE below) are the only per-tag choices: Great Tang, The
Papacy, Balhae. Everything else follows from CK3.

    python3 tools/tagloc.py TAG...     # explain how these tags are named
"""
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

DB = os.path.join(HERE, "tags.db")
_hist = {}


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


def _blocks(text, start=0):
    """[(index of '{' + 1, index of matching '}')] of the top-level blocks at brace depth 0 from `start`."""
    out, d, i = [], 0, start
    while i < len(text):
        c = text[i]
        if c == "{":
            if d == 0:
                b = i + 1
            d += 1
        elif c == "}":
            d -= 1
            if d == 0:
                out.append((b, i))
        i += 1
    return out


def history_name(title):
    """The loc key a title's history names it by at the start date, or None."""
    import rites

    if not _hist:
        import glob
        from paths import CK3_GAME

        for f in sorted(glob.glob(os.path.join(CK3_GAME, "history", "titles", "*.txt"))):
            text = open(f, encoding="utf-8-sig", errors="replace").read()
            text = re.sub(r"#[^\n]*", "", text)
            for m in re.finditer(r"(?m)^([ckdeh]_[\w\-]+)\s*=\s*\{", text):
                # the title's block: from its brace to the matching one
                d, j = 1, m.end()
                while j < len(text) and d:
                    d += (text[j] == "{") - (text[j] == "}")
                    j += 1
                body = text[m.end():j - 1]
                best = None
                for dm in re.finditer(r"(?m)^\t(\d+\.\d+\.\d+)\s*=\s*\{", body):
                    key = rites._date_key(dm.group(1))
                    if key > rites.START:
                        continue
                    k = dm.end()
                    d2 = 1
                    while k < len(body) and d2:
                        d2 += (body[k] == "{") - (body[k] == "}")
                        k += 1
                    blk = body[dm.end():k - 1]
                    names = re.findall(r'(?m)^\t\t(?:name|set_title_name)\s*=\s*"?([\w\-]+)"?', blk)
                    names += re.findall(r'(?m)^\t\t\t(?:set_title_name)\s*=\s*"?([\w\-]+)"?', blk)
                    if names and (best is None or key >= best[0]):
                        best = (key, names[-1])
                if best:
                    _hist[m.group(1)] = best[1]
    return _hist.get(title)


# our wording where we prefer it to CK3's: tag -> ("prefix", text) or ("key", CK3 loc key)
STYLE = {"TNG": ("prefix", "Great "), "JIN": ("prefix", "Great "), "KOR": ("key", "cn_goryeo"), "PAP": ("prefix", "The "), "BHE": ("key", "cn_balhae")}
DYNASTY_HERITAGES = ("heritage_arabic", "heritage_berber", "heritage_iranian")


def named_realm_governments():
    """The governments with `dynasty_named_realms = yes`."""
    import glob
    from paths import CK3_GAME

    out = set()
    for f in glob.glob(os.path.join(CK3_GAME, "common", "governments", "*.txt")):
        text = open(f, encoding="utf-8-sig", errors="replace").read()
        for m in re.finditer(r"(?m)^(\w+)\s*=\s*\{(.*?)^\}", text, re.S):
            if re.search(r"dynasty_named_realms\s*=\s*yes", m.group(2)):
                out.add(m.group(1))
    return out


def dynasty_realm(tag, title, rank):
    """(name, adjective) when the realm is named for its 867 ruler's dynasty, else None."""
    import ck3
    import culturalnames as cn
    import culturelift as cl
    import culturetitles as ct
    from enc import fold_loc

    if rank is None or rank < 2 or rank > 4:
        return None
    if re.search(r"can_be_named_after_dynasty\s*=\s*no", cn._title_blocks().get(title, "")):
        return None
    gov = ck3.title_government(title)
    if gov and gov not in named_realm_governments():
        return None
    _h, cc = cl.holder_culture(title)
    if not cc or ct.culture_info(cc)[0] not in DYNASTY_HERITAGES:
        return None
    if not _ctx:
        _ctx.append((ck3.load_titles(), ck3.load_chars(), ck3.load_dynasties(), ck3.load_houses()))
    try:
        dyn = ck3.resolve(tag, *_ctx[0]).get("dynasty")
    except Exception:
        dyn = None
    if not dyn:
        return None
    d = fold_loc(dyn)
    return (d + "s" if d.lower().endswith("id") else d), d


_ctx = []


def title_names(title, rank, tag=None):
    """(name, adjective) the tag shows at the start, folded; None when CK3 has no name."""
    got = _title_names(title, rank, tag)
    st = STYLE.get(tag)
    if got and st and st[0] == "prefix":
        got = (st[1] + got[0], got[1])
    return got


def _title_names(title, rank, tag):
    import ck3
    import culturalnames as cn
    from enc import fold_loc

    st = STYLE.get(tag)
    if st and st[0] == "key":
        name = _resolve(ck3.loc(st[1]))
        adj = _resolve(ck3.loc(st[1] + "_adj")) or name
        return (fold_loc(name), fold_loc(adj)) if name else None
    dn = dynasty_realm(tag, title, rank) if tag else None
    if dn:
        return dn
    key = history_name(title)
    if key and ck3.loc(key):
        name, adj = ck3.loc(key), ck3.loc(key + "_adj")
    else:
        name, adj = cn.cultural_name(title)
        if not name:
            name, adj = ck3.loc(title), ck3.loc(title + "_adj")
    name = _resolve(name)
    if not name:
        return None
    adj = _resolve(adj) or name
    name, adj = fold_loc(name), fold_loc(adj)
    suf = cn.people_suffix(title, rank)
    if suf:
        name, adj = f"{name} {fold_loc(suf)}", f"{adj} {fold_loc(suf)}"
    return name, adj


# formables named from CK3 as well (the base game's own loc covers the rest)
LIFT_FORMABLES = ("TIB", "UTS", "KAM", "AMD", "BHU", "LDK", "GRO", "KIN", "LIO", "JIN", "KOR")


def wanted():
    con = sqlite3.connect(DB)
    out = {tag: title_names(title, rank, tag)
           for tag, title, rank in con.execute("select tag, ck3_title, rank from tags order by seq")}
    for tag, title, rank in con.execute("select tag, ck3_title, rank from formables"):
        if tag in LIFT_FORMABLES:
            out[tag] = title_names(title, rank, tag)
    return out


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


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["write"]:
        print("rewritten" if write() else "unchanged")
    elif a:
        con = sqlite3.connect(DB)
        for tag in a:
            title, rank = con.execute("select ck3_title, rank from tags where tag=?", (tag,)).fetchone()
            print(tag, title, "history key:", history_name(title), "->", title_names(title, rank, tag))
    else:
        d = drift()
        for t, have, want in d:
            print(f"{t:4} have {have} / CK3 {want}")
        print(len(d), "differ")
