#!/usr/bin/env python3
"""Tag names and adjectives, derived from CK3 at build time.

Nothing of CK3's text is stored in the repo and nothing is hand-chosen: the
name a tag shows is the name CK3 shows for its title at 867.1.1, derived by:

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


def title_names(title, rank):
    """(name, adjective) CK3 shows for the title at the start, folded; None when CK3 has no name."""
    import ck3
    import culturalnames as cn
    from enc import fold_loc

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


def wanted():
    con = sqlite3.connect(DB)
    return {tag: title_names(title, rank)
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


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["write"]:
        print("rewritten" if write() else "unchanged")
    elif a:
        con = sqlite3.connect(DB)
        for tag in a:
            title, rank = con.execute("select ck3_title, rank from tags where tag=?", (tag,)).fetchone()
            print(tag, title, "history key:", history_name(title), "->", title_names(title, rank))
    else:
        d = drift()
        for t, have, want in d:
            print(f"{t:4} have {have} / CK3 {want}")
        print(len(d), "differ")
