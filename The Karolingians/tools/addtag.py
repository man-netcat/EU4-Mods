#!/usr/bin/env python3
"""Insert a new realm tag: DB rows + loc pair. Then run build + validate.

Usage: python3 tools/addtag.py TAG ck3_title PID [PID ...]
       [--rank N] [--capital PID] [--tech GROUP] [--gov GOV]
       [--name STR] [--adj STR] [--file NAME] [--take]

Defaults: rank from title tier (c1/d2/k3/e4), capital = first PID,
tech western, gov monarchy, name/adj from CK3 loc, culture/religion =
vanilla values of the capital, country file = ASCII-ised name.
Aborts if the code is taken or a province is owned (use --take to
reassign provinces from their current owner).
"""
import argparse
import os
import re
import sqlite3
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eu4 import GAME, vanilla_prov_file  # noqa: E402

import ck3  # noqa: E402

DB = os.path.join(HERE, "tags.db")
LOC = os.path.join(HERE, "..", "localisation", "replace", "countries_l_english.yml")
RANK_OF = {"c": 1, "d": 2, "k": 3, "e": 4}
_ASCII_MAP = {"æ": "ae", "Æ": "Ae", "œ": "oe", "Œ": "Oe", "ø": "o", "Ø": "O",
              "ß": "ss", "ẞ": "SS", "ł": "l", "Ł": "L", "ð": "d", "Ð": "D",
              "þ": "th", "Þ": "TH"}


def ascii_name(s):
    out = []
    for ch in s:
        if ch in _ASCII_MAP:
            out.append(_ASCII_MAP[ch])
        else:
            for c in unicodedata.normalize("NFKD", ch):
                if not unicodedata.combining(c) and ord(c) < 128:
                    out.append(c)
    return "".join(out)


def vanilla_tags():
    found = set()
    vd = os.path.join(GAME, "common", "country_tags")
    for fn in os.listdir(vd):
        if fn.endswith(".txt"):
            found.update(
                re.findall(r"^([A-Z]{3})\s*=\s*\"countries/",
                           open(os.path.join(vd, fn), encoding="cp1252",
                                errors="replace").read(), re.M))
    return found


def prov_data(pid):
    src = vanilla_prov_file(pid)
    if not src:
        sys.exit(f"no vanilla province file for {pid}")
    fn = os.path.basename(src)[:-4]
    name = re.sub(r"^\d+\s*-\s*", "", fn)
    txt = open(src, encoding="cp1252", errors="replace").read()
    cul = re.search(r"^culture\s*=\s*(\w+)", txt, re.M)
    rel = re.search(r"^religion\s*=\s*([\w_]+)", txt, re.M)
    if not cul or not rel:
        sys.exit(f"no culture/religion in {src}")
    return name, cul.group(1), rel.group(1)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("title")
    ap.add_argument("pids", nargs="+", type=int)
    ap.add_argument("--rank", type=int)
    ap.add_argument("--capital", type=int)
    ap.add_argument("--tech", default="western")
    ap.add_argument("--gov", default="monarchy")
    ap.add_argument("--name")
    ap.add_argument("--adj")
    ap.add_argument("--file")
    ap.add_argument("--take", action="store_true")
    ap.add_argument("--reuse", action="store_true",
                    help="code is a vanilla tag taken over deliberately")
    a = ap.parse_args(argv)

    if not re.fullmatch(r"[A-Z]{3}", a.tag):
        sys.exit("tag must be 3 uppercase letters")
    if a.tag in vanilla_tags() and not a.reuse:
        sys.exit(f"{a.tag} is a vanilla tag (pass --reuse to take it over deliberately)")
    c = sqlite3.connect(DB)
    if c.execute("select tag from tags where tag=?", (a.tag,)).fetchone():
        sys.exit(f"{a.tag} already in tags.db")
    taken = c.execute(
        f"select tag,pid from tag_provinces where pid in ({','.join('?' * len(a.pids))})",
        a.pids).fetchall()
    if taken and not a.take:
        sys.exit(f"provinces owned already ({taken}); pass --take to reassign")
    for tag, pid in taken:
        c.execute("delete from tag_provinces where tag=? and pid=?", (tag, pid))
        print(f"  took {pid} from {tag}")

    rank = a.rank or RANK_OF.get(a.title.split("_")[0])
    if not rank:
        sys.exit("cannot derive rank from title; pass --rank")
    name = a.name or ck3.loc(a.title)
    if not name:
        sys.exit(f"no CK3 loc for {a.title}; pass --name")
    adj = a.adj or ck3.loc(a.title + "_adj") or name
    colors = ck3.load_title_colors()
    if a.title not in colors:
        sys.exit(f"no CK3 color for {a.title}")
    capital = a.capital or a.pids[0]
    if capital not in a.pids:
        sys.exit("capital must be one of the provinces")
    datas = {pid: prov_data(pid) for pid in a.pids}
    culture, religion = datas[capital][1], datas[capital][2]
    seq = c.execute("select max(seq) from tags").fetchone()[0] + 1
    country_file = (a.file or ascii_name(name)) + ".txt"

    values = ((a.tag, seq, rank, name, capital, culture, religion, a.title, None,
               a.gov, a.tech, "", 0) + tuple(colors[a.title])
              + (country_file, 250, 5, 0, 10,
                 "[]", "[]", "[]", "[]", None, None, None, None, None))
    c.execute(f"INSERT INTO tags VALUES ({','.join('?' * len(values))})", values)
    for pid in a.pids:
        if not c.execute("select pid from provinces where pid=?", (pid,)).fetchone():
            c.execute("INSERT INTO provinces VALUES (?,?,?,?)", (pid,) + datas[pid])
        c.execute("INSERT INTO tag_provinces VALUES (?,?)", (a.tag, pid))
    c.execute("INSERT INTO tag_reforms VALUES (?,?,?)",
              (a.tag, seq, "feudalism_reform"))
    c.commit()

    with open(LOC, encoding="utf-8-sig") as f:
        lines = f.read().split("\n")
    try:
        i = next(n for n, ln in enumerate(lines) if ln == " HLR:1 \"Karolingian Empire\"")
    except StopIteration:
        sys.exit("HLR anchor not found in loc file")
    lines[i:i] = [f' {a.tag}:1 "{name}"', f' {a.tag}_ADJ:1 "{adj}"']
    with open(LOC, "w", encoding="utf-8-sig", newline="") as f:
        f.write("\n".join(lines))
    print(f"{a.tag} {name} ({a.title}): seq {seq}, rank {rank}, "
          f"capital {capital}, {culture}/{religion}, {a.tech}, "
          f"{len(a.pids)} provinces, {country_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
