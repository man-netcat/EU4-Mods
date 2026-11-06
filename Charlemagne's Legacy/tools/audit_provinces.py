#!/usr/bin/env python3
"""Which provinces sit with a tag other than the one CK3's 867 chain says.

For every owned province: the county's 867 holder, then his liege chain up to the nearest lord who rules a tag of the mod
(a governor folded into a tag counts as that tag); the owner should be that tag. Read-only; nothing here moves land.

    python3 tools/audit_provinces.py            # summary and the largest groups
    python3 tools/audit_provinces.py --all      # every province: pid county owner holder -> expected tags
    python3 tools/audit_provinces.py --json     # the same as JSON on stdout

A province whose holder's chain reaches no tag has no expected tag (printed as "-"). Several EU4 provinces may share one CK3
county (`provfaiths.PROVINCE_COUNTY` pairs by place), so a hit can be a wrong pairing as well as a wrong owner: judge each
before moving land (`cl-assign-provinces`). Tags a union shares a ruler with are all accepted."""
import collections
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


def main(argv):
    rows = audit()
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
