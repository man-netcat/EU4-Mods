#!/usr/bin/env python3
"""Which provinces sit with a tag other than the one CK3's 867 chain says.

For every owned province: the county's 867 holder, then his liege chain up to the nearest lord who rules a tag of the mod
(a governor folded into a tag counts as that tag); the owner should be that tag. Read-only; nothing here moves land.

    python3 tools/audit_provinces.py            # summary and the largest groups
    python3 tools/audit_provinces.py --all      # every province: pid county owner holder -> expected tags
    python3 tools/audit_provinces.py --json     # the same as JSON on stdout
    python3 tools/audit_provinces.py --classify # every hit with its evidence (own-county, area, holder-rules, ...)
    python3 tools/audit_provinces.py --apply [PID,PID,..]  # move the trusted ones (or the listed PIDs) in tags.db, then build + validate

A province whose holder's chain reaches no tag has no expected tag (printed as "-"). Several EU4 provinces may share one CK3
county (`provfaiths.PROVINCE_COUNTY` pairs by place), so a hit can be a wrong pairing as well as a wrong owner: judge each
before moving land (`cl-assign-provinces`). Tags a union shares a ruler with are all accepted."""
import collections
import difflib
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lieges  # noqa: E402
import provfaiths as pf  # noqa: E402
import state867 as S  # noqa: E402


def audit():
    ruler, _ = lieges.lieges()
    rules = collections.defaultdict(list)
    for tag, r in ruler.items():
        rules[str(r)].append(tag)
    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    dormant = {r[0] for r in con.execute("select tag from releasables")}
    owner = dict(con.execute("select pid, tag from tag_provinces"))

    def name(x):
        m = re.search(r'name\\s*=\\s*"?([^\\s"#]+)', S._CH.get(str(x), ""))
        return m.group(1) if m else str(x)

    def expected(h):
        cur, seen = h, set()
        while cur and cur not in seen:
            seen.add(cur)
            tags = [t for t in rules.get(str(cur), []) if t not in dormant]
            if tags:
                return tags, cur
            prim = S.primary(cur)
            if prim is None:
                return [], None
            cur = S.liege_holder(prim)
        return [], None

    out = []
    for pid, tag in sorted(owner.items()):
        county = pf.PROVINCE_COUNTY.get(pid)
        holder = S.holder(county) if county else None
        if not holder:
            continue
        tags, lord = expected(holder)
        if tag not in tags:
            out.append({"pid": pid, "county": county, "owner": tag, "holder": name(holder), "expected": tags,
                        "lord": name(lord) if lord else None})
    return out


def _norm(s):
    return re.sub(r"[^a-z]", "", s[2:].lower() if s.startswith("c_") else s.lower())


def classify(rows):
    """Add `evidence` to each row: `name` (the EU4 province name matches its county's name, ratio >= 0.8: the one pairing
    that is not an approximation, though homonyms exist - EU4's Karelian Viborg is not Jutland's), `own-county` (the paired county is the title of the expected tag, whose own county it
    must own), `area` (more of the province's EU4-area neighbours belong to the expected tag than to the owner),
    `holder-rules` (the county's holder rules the expected tag himself; true of every direct holding, so it does not
    discriminate between a wrong owner and a wrong pairing), or `weak`/`ambiguous`/`none`."""
    from steps.provdata import load_areas

    areas = load_areas()
    area_of = {int(p): a for a, ps in areas.items() for p in ps}
    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    title = dict(con.execute("select tag, ck3_title from tags"))
    owner = dict(con.execute("select pid, tag from tag_provinces"))
    pname = dict(con.execute("select pid, name from provinces"))
    ruler, _ = lieges.lieges()
    ruled = collections.defaultdict(list)
    for tag, r in ruler.items():
        ruled[str(r)].append(tag)
    for r in rows:
        exp = r["expected"]
        if len(exp) != 1:
            r["evidence"] = "ambiguous" if exp else "none"
            continue
        e = exp[0]
        ev = []
        if difflib.SequenceMatcher(None, _norm(pname.get(r["pid"], "")), _norm(r["county"])).ratio() >= 0.8:
            ev.append("name")
        if title.get(e) == r["county"]:
            ev.append("own-county")
        mates = collections.Counter(owner.get(int(p)) for p in areas.get(area_of.get(r["pid"]), []) if int(p) != r["pid"])
        if mates[e] > mates[r["owner"]]:
            ev.append("area")
        if e in ruled.get(str(S.holder(r["county"])), []):
            ev.append("holder-rules")
        r["evidence"] = "+".join(ev) if ev else "weak"
    return rows


STRONG = ("own-county", "area")


def trusted(row):
    """A name-matched pairing with geographic backing (the county is the expected tag's own, or the province's EU4-area
    neighbours belong to the expected tag): the owner is wrong, not the pairing."""
    ev = row["evidence"].split("+")
    return "name" in ev and bool(set(ev) & set(STRONG))


def apply(rows, only=None):
    """Move the trusted provinces (`trusted`) - or exactly the PIDs in `only` - to their expected tag in tags.db, keeping
    every tag alive and giving a tag that loses its capital a new one (a province paired to its own title, else its lowest
    pid). Check the list against geography before using `only`."""
    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    owner = dict(con.execute("select pid, tag from tag_provinces"))
    capital = dict(con.execute("select tag, capital from tags"))
    title = dict(con.execute("select tag, ck3_title from tags"))
    moves = {r["pid"]: r["expected"][0] for r in rows
             if len(r["expected"]) == 1 and ((only is None and trusted(r)) or (only is not None and r["pid"] in only))}
    after = dict(owner)
    after.update(moves)
    left = collections.Counter(after.values())
    skipped = [(p, owner[p], t) for p, t in moves.items() if left[owner[p]] == 0]
    for p, _o, _t in skipped:
        moves.pop(p)
        after[p] = owner[p]
    for pid, tag in moves.items():
        con.execute("update tag_provinces set tag=? where pid=?", (tag, pid))
        print(f"{pid} {owner[pid]} -> {tag}")
    for tag, cap in capital.items():
        if after.get(cap) != tag and any(t == tag for t in after.values()):
            mine = sorted(p for p, t in after.items() if t == tag)
            own = [p for p in mine if pf.PROVINCE_COUNTY.get(p) == title.get(tag)]
            con.execute("update tags set capital=? where tag=?", ((own or mine)[0], tag))
            print(f"capital of {tag}: {cap} -> {(own or mine)[0]}")
    con.commit()
    print(f"moved {len(moves)} provinces; skipped {len(skipped)} that would leave their owner with no land: {skipped}")


def main(argv):
    rows = audit()
    if "--classify" in argv or "--apply" in argv:
        classify(rows)
    if "--apply" in argv:
        nxt = argv[argv.index("--apply") + 1:]
        apply(rows, {int(x) for x in nxt[0].split(",")} if nxt and nxt[0][0].isdigit() else None)
        return
    if "--classify" in argv:
        for r in rows:
            print(f"{r['pid']:>5} {r['county']:<22} {r['owner']} -> {','.join(r['expected']) or '-':<8} {r['evidence']}")
        print(collections.Counter(r["evidence"] for r in rows))
        return
    if "--json" in argv:
        json.dump(rows, sys.stdout, indent=1)
        return
    with_target = [r for r in rows if r["expected"]]
    print(f"{len(rows)} provinces sit with a tag other than their CK3 chain's: {len(with_target)} have an expected tag, "
          f"{len(rows) - len(with_target)} reach no tag")
    if "--all" in argv:
        for r in rows:
            print(f"{r['pid']:>5} {r['county']:<22} {r['owner']} holder {r['holder']} -> {','.join(r['expected']) or '-'}")
        return
    groups = collections.Counter((r["owner"], tuple(r["expected"])) for r in with_target)
    for (owner, exp), n in groups.most_common(20):
        print(f"  {owner} -> {'/'.join(exp)}: {n}")


if __name__ == "__main__":
    main(sys.argv[1:])
