#!/usr/bin/env python3
"""Start-date alliances and royal marriages, lifted from CK3's 867 marriages between realms.

CK3 carries no alliance data for 867, but its characters do carry marriages. Two tags are bound when one's ruler is
married to a close relative of the other's ruler: the spouse's own parents or siblings, or a child's spouse and that
spouse's parents. Each bound pair starts both allied and married (CK3 marriages normally carry an alliance). Pairs
already tied by a subject relation, or listed in the diplomacy table, are left alone.

    python3 tools/marriages.py       # list the lifted pairs
"""
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ck3  # noqa: E402
from tagdb import BY_TAG, DIPLOMACY, DORMANT, PEER_RELATIONS, Diplomacy  # noqa: E402

_pairs = None


def _field(chars, cid, key):
    m = re.search(rf"^\s*{key}\s*=\s*(\d+)", chars.get(cid, ""), re.M)
    return m.group(1) if m else None


def _spouses(chars, cid):
    out = set()
    for m in re.finditer(r"(\d+)\.\d+\.\d+\s*=\s*\{(.*?)\n\t\}", chars.get(cid, ""), re.S):
        if int(m.group(1)) <= 867:
            out |= set(re.findall(r"add_spouse\s*=\s*(\d+)", m.group(2)))
    return out


def marriage_pairs():
    """Sorted [(tag, tag)] of realms whose 867 rulers' families are joined by a marriage, first tag alphabetical."""
    global _pairs
    if _pairs is not None:
        return _pairs
    chars, titles = ck3.load_chars(), ck3.load_titles()
    dyns, houses = ck3.load_dynasties(), ck3.load_houses()
    ruler = {}
    for tag in sorted(BY_TAG):
        if tag in DORMANT:
            continue
        r = ck3.resolve(tag, titles, chars, dyns, houses)
        if "char" in r:
            ruler[tag] = str(r["char"])
    # one ruler holding several tags (a king and his union subject) binds through the highest-ranked realm only
    subjects = {d.subject for d in DIPLOMACY if d.relation not in PEER_RELATIONS}
    by_ruler = {}
    for tag, cid in sorted(ruler.items()):
        best = by_ruler.get(cid)
        if best is None or (tag in subjects, -BY_TAG[tag].rank) < (best in subjects, -BY_TAG[best].rank):
            by_ruler[cid] = tag
    ruler = {tag: cid for cid, tag in by_ruler.items()}
    kids = collections.defaultdict(set)
    for cid in chars:
        for k in ("father", "mother"):
            p = _field(chars, cid, k)
            if p:
                kids[p].add(cid)
    found = set()
    for tag, cid in sorted(ruler.items()):
        kin = set()
        for s in _spouses(chars, cid):
            kin.add(s)
            for k in ("father", "mother"):
                p = _field(chars, s, k)
                if p:
                    kin.add(p)
                    kin |= kids[p]
        for c in kids[cid]:
            for s in _spouses(chars, c):
                kin.add(s)
                for k in ("father", "mother"):
                    p = _field(chars, s, k)
                    if p:
                        kin.add(p)
        for r in kin:
            other = by_ruler.get(r)
            if other and other != tag:
                found.add(tuple(sorted((tag, other))))
    _pairs = sorted(found)
    return _pairs


def derived_relations():
    """Diplomacy rows for the lifted pairs: an alliance and a royal marriage each, minus pairs the table covers."""
    tied = {frozenset((d.liege, d.subject)) for d in DIPLOMACY if d.relation not in PEER_RELATIONS}
    have = {(frozenset((d.liege, d.subject)), d.relation) for d in DIPLOMACY if d.relation in PEER_RELATIONS}
    out = []
    for a, b in marriage_pairs():
        if frozenset((a, b)) in tied:
            continue
        for rel in PEER_RELATIONS:
            if (frozenset((a, b)), rel) not in have:
                out.append(Diplomacy(a, b, rel))
    return out


def all_relations():
    return list(DIPLOMACY) + derived_relations()


if __name__ == "__main__":
    for a, b in marriage_pairs():
        print(a, b)
    print(len(marriage_pairs()), "pairs;", len(derived_relations()), "relations added")
