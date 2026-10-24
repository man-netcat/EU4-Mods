#!/usr/bin/env python3
"""Insert a new realm tag: DB rows + loc pair. Then run build + validate.

Usage: python3 tools/addtag.py TAG ck3_title PID [PID ...]
       python3 tools/addtag.py --to TAG PID [PID ...]   (append to a tag)
       [--rank N] [--capital PID] [--tech GROUP] [--gov GOV]
       [--name STR] [--adj STR] [--file NAME] [--take]

Defaults: rank from title tier (c1/d2/k3/e4), capital = first PID, gov
monarchy, name/adj from CK3 loc, culture and religion lifted from the
title's 867 ruler (capital's vanilla values take over only when the
ruler's own data is unscripted; --culture/--religion are a documented
EXCEPTION on top, never the norm), country file = ASCII-ised name. Tech group is mandatory:
`--tech` must be passed and named correctly (for reuse codes the base
game's own tech is expected unless the 867 reality says otherwise -
then say it explicitly).
Aborts if the code is taken or a province is owned (use --take to
reassign provinces from their current owner).
"""
import argparse
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import db  # noqa: E402
from eu4 import GAME, vanilla_prov_file  # noqa: E402
from models import (  # noqa: E402
    Culture as CultureRow,
    Province as ProvinceRow,
    Religion as ReligionRow,
    Tag as TagRow,
    TagProvince as TagProvinceRow,
    TagReform as TagReformRow,
)
from sqlalchemy import func  # noqa: E402

import ck3  # noqa: E402

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
    return name, cul.group(1) if cul else None, rel.group(1) if rel else None


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("tag", nargs="?")
    ap.add_argument("title", nargs="?")
    ap.add_argument("pids", nargs="+", type=int)
    ap.add_argument("--to",
                    help="append the provinces to an existing tag (no title)")
    ap.add_argument("--culture", help="override the vanilla province culture")
    ap.add_argument("--religion", help="override the vanilla province religion")
    ap.add_argument("--rank", type=int)
    ap.add_argument("--capital", type=int)
    ap.add_argument("--tech", default=None)
    ap.add_argument("--gov", default="monarchy")
    ap.add_argument("--name")
    ap.add_argument("--adj")
    ap.add_argument("--file")
    ap.add_argument("--take", action="store_true")
    ap.add_argument("--reuse", action="store_true",
                    help="code is a vanilla tag taken over deliberately")
    a = ap.parse_args(argv)

    if a.to and (a.tag is not None or a.title is not None):
        # --to takes only pids: argparse files leading pids as tag/title,
        # so fold any numeric ones back into pids.
        try:
            extra = [int(x) for x in ([a.tag] if a.tag else []) + ([a.title] if a.title else [])]
        except ValueError:
            sys.exit("--to takes only pids, no tag/title")
        a.pids = extra + (a.pids or [])
        a.tag = a.title = None

    s = db.session()
    if a.to:
        if a.tag or a.title:
            sys.exit("--to takes only pids, no tag/title")
        if s.get(TagRow, a.to) is None:
            sys.exit(f"{a.to} is no tag in tags.db")
        taken = s.query(TagProvinceRow.tag, TagProvinceRow.pid).filter(
            TagProvinceRow.pid.in_(a.pids)).all()
        if taken and not a.take:
            sys.exit(f"provinces owned already ({taken}); pass --take to reassign")
        for tag, pid in taken:
            s.delete(s.get(TagProvinceRow, (tag, pid)))
            print(f"  took {pid} from {tag}")
    if a.to:
        datas = {pid: prov_data(pid) for pid in a.pids}
        for pid, (nm, cul, rel) in datas.items():
            if s.get(ProvinceRow, pid) is not None:
                continue  # existing rows keep the culture/religion in the DB
            if (cul is None and not a.culture) or (rel is None and not a.religion):
                sys.exit(f"vanilla province {pid} has no culture/religion head "
                         "(uncolonized in 1444) - pass --culture/--religion")
            for key, val, model in (("culture", a.culture or cul, CultureRow),
                                    ("religion", a.religion or rel, ReligionRow)):
                if s.get(model, val) is None:
                    sys.exit(f"{val} is no {key} in tags.db - seed it first")
        for pid in a.pids:
            name, cul, rel = datas[pid]
            if s.get(ProvinceRow, pid) is None:
                s.add(ProvinceRow(pid=pid, name=name, culture=a.culture or cul,
                                  religion=a.religion or rel, fort=False))
            s.add(TagProvinceRow(tag=a.to, pid=pid))
        s.commit()
        s.close()
        print(f"{a.to} gains {len(a.pids)} provinces")
        return 0

    datas = {pid: prov_data(pid) for pid in a.pids}
    for pid, (_nm, cul, rel) in datas.items():
        if (cul is None and not a.culture) or (rel is None and not a.religion):
            sys.exit(f"vanilla province {pid} has no culture/religion head "
                     "(uncolonized in 1444) - pass --culture/--religion")
        for key, val, model in (("culture", a.culture or cul, CultureRow),
                                ("religion", a.religion or rel, ReligionRow)):
            # session still empty - safe to look up (and seed if missing)
            if s.get(model, val) is None:
                sys.exit(f"{val} is no {key} in tags.db - seed it first")
    have = set()
    import glob as _glob
    for fn in _glob.glob(os.path.join(HERE, "..", "localisation", "..",
                                      "common", "cultures", "*.txt")):
        for ln in open(fn, encoding="cp1252", errors="replace"):
            # tolerate trailing comments (most cultures carry #Name)
            m = re.match(r"^\t([a-z_0-9]+)\s*=\s*\{", ln)
            if m:
                have.add(m.group(1))
    for pid, (_nm, cul, _rel) in datas.items():
        # an existing province keeps the culture already in the DB; only a
        # fresh one would be written with the vanilla (possibly dead) key.
        if s.get(ProvinceRow, pid) is None and cul not in have and not a.culture:
            sys.exit(f"province {pid} is vanilla {cul}, undefined here - "
                     "pass --culture to pick the 867 key")

    if not re.fullmatch(r"[A-Z]{3}", a.tag):
        sys.exit("tag must be 3 uppercase letters")
    if a.tag in vanilla_tags() and not a.reuse:
        sys.exit(f"{a.tag} is a vanilla tag (pass --reuse to take it over deliberately)")
    if s.get(TagRow, a.tag) is not None:
        sys.exit(f"{a.tag} already in tags.db")
    taken = s.query(TagProvinceRow.tag, TagProvinceRow.pid).filter(
        TagProvinceRow.pid.in_(a.pids)).all()
    if taken and not a.take:
        sys.exit(f"provinces owned already ({taken}); pass --take to reassign")
    for tag, pid in taken:
        s.delete(s.get(TagProvinceRow, (tag, pid)))
        print(f"  took {pid} from {tag}")

    if a.tech is None:
        hint = "pass --tech"
        if a.reuse:
            import glob as _glob
            hits = _glob.glob(os.path.join(
                GAME, "history", "countries", f"{a.tag} - *.txt"))
            if hits:
                m = re.search(r"(?m)^\s*technology_group\s*=\s*([a-z_]+)",
                              open(hits[0], encoding="cp1252",
                                   errors="replace").read())
                if m and m.group(1) != "western":
                    hint = (f"pass --tech (careful: reuse of vanilla "
                            f"{m.group(1)} tech - an 867 realm may want it "
                            f"kept, so say --tech {m.group(1)} explicitly)")
                else:
                    hint = f"pass --tech (vanilla tech is {m.group(1)})" if m else "pass --tech"
        sys.exit(f"{a.tag}: no tech group given - {hint}")
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
    from culturelift import ruler_default, ruler_religion  # noqa: E402

    if a.culture:
        # documented exception: manual culture overriding the ruler lift
        culture = a.culture
    else:
        culture = ruler_default(a.title, s) or datas[capital][1]
    if a.religion:
        # documented exception: manual faith overriding the ruler lift
        religion = a.religion
    else:
        ruler_rel = ruler_religion(a.title)
        if ruler_rel is None:
            print(f"  no ruler faith for {a.title}, keeping land religion")
        religion = ruler_rel or datas[capital][2]
    for key, model, val in (("culture", CultureRow, culture),
                            ("religion", ReligionRow, religion)):
        if s.get(model, val) is None:
            sys.exit(f"{val} is no {key} in tags.db - lift it first")
    seq = s.query(func.max(TagRow.seq)).scalar() + 1
    country_file = (a.file or ascii_name(name)) + ".txt"
    from eu4 import load_vanilla_countries

    vanilla_countries = load_vanilla_countries()
    taken_files = {fn for fn, _text in vanilla_countries.values()}
    if country_file in taken_files and not (
            a.reuse and vanilla_countries.get(a.tag, ("",))[0] == country_file
    ):
        sys.exit(
            f"{country_file} is a vanilla country file for another tag - "
            "pass --file to pick a free name"
        )

    r, g, bl = colors[a.title]
    s.add(TagRow(tag=a.tag, seq=seq, rank=rank, name=name, capital=capital,
                 culture=culture, religion=religion, ck3_title=a.title,
                 government=a.gov, technology_group=a.tech, color_r=r,
                 color_g=g, color_b=bl, country_file=country_file))
    for pid in a.pids:
        # no_autoflush: the lookups must not flush the pending Tag row,
        # whose capital FK points at a province this loop only then adds
        with s.no_autoflush:
            fresh = s.get(ProvinceRow, pid) is None
        if fresh:
            pname, pcul, prel = datas[pid]
            s.add(ProvinceRow(pid=pid, name=pname, culture=a.culture or pcul,
                              religion=a.religion or prel, fort=False))
        s.add(TagProvinceRow(tag=a.tag, pid=pid))
    s.add(TagReformRow(tag=a.tag, pos=seq, reform="feudalism_reform"))
    s.commit()
    s.close()

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
