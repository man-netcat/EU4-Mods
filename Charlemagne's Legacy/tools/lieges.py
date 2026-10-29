#!/usr/bin/env python3
"""Who is whose liege in CK3's 867, seen from the mod's tags.

A tag's ruler is the 867 holder of its title; the ruler's liege is the liege of his highest-tier title (`liege =` in
that title's history; none means independent). When that liege is a character no tag is ruled by (a governor whose
lands are folded into his own sovereign's tag), the chain is followed up until a ruler who has a tag.

    python3 tools/lieges.py       # list every tag whose CK3 liege differs from the mod's diplomacy table
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ck3  # noqa: E402
import state867 as S  # noqa: E402
from tagdb import BY_TAG, DIPLOMACY, DORMANT, PEER_RELATIONS  # noqa: E402

_cache = None


def lieges():
    """({tag: ruler id}, {tag: sorted tags of its CK3 liege's realm, or None when CK3 gives it no liege})."""
    global _cache
    if _cache is not None:
        return _cache
    titles, chars = ck3.load_titles(), ck3.load_chars()
    dyns, houses = ck3.load_dynasties(), ck3.load_houses()
    ruler, by_ruler = {}, collections.defaultdict(list)
    for tag in sorted(BY_TAG):
        if tag in DORMANT:
            continue
        r = ck3.resolve(tag, titles, chars, dyns, houses)
        if "char" in r:
            ruler[tag] = str(r["char"])
            by_ruler[str(r["char"])].append(tag)
    out = {}
    for tag, cid in ruler.items():
        prim, lg, seen = S.primary(cid), None, {cid}
        while prim is not None:
            lg = S.liege_holder(prim)
            if lg is None or lg in seen or by_ruler.get(str(lg)):
                break
            seen.add(lg)
            prim = S.primary(lg)
            lg = None
        out[tag] = sorted(by_ruler[str(lg)]) if lg and by_ruler.get(str(lg)) else None
    _cache = (ruler, out)
    return _cache


def mismatches():
    """[(tag, what the mod says, what CK3 says)] over every tag with a ruler."""
    ruler, ck3_liege = lieges()
    subj = collections.defaultdict(list)
    for d in DIPLOMACY:
        if d.relation not in PEER_RELATIONS:
            subj[d.subject].append((d.liege, d.relation))
    bad = []
    for tag in sorted(ruler):
        liege = ck3_liege[tag]
        rel = subj.get(tag, [])
        held = [(l, t) for l, t in rel if t != "tributary_state"]  # a tributary has no liege in CK3
        if not held:
            if liege:
                says = f"tributary of {rel[0][0]}" if rel else "independent"
                bad.append((tag, says, f"liege in {'/'.join(liege)}"))
            continue
        for overlord, typ in held:
            if typ == "union" and ruler.get(overlord) == ruler[tag]:
                continue  # one ruler holding both crowns
            if not liege:
                bad.append((tag, f"{typ} of {overlord}", "independent"))
            elif overlord not in liege:
                bad.append((tag, f"{typ} of {overlord}", f"liege in {'/'.join(liege)}"))
    return bad


if __name__ == "__main__":
    for tag, mod, ck in mismatches():
        print(f"{tag}: mod says {mod}, CK3 says {ck}")
