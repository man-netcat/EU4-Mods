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
from tagdb import BY_TAG, DIPLOMACY, DORMANT, PEER_RELATIONS, PROVINCE_OWNERS  # noqa: E402

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


def governor_province_mismatches():
    """[(pid, county, owner, expected)] for the provinces of every realm that has governor vassals (`theme_subject_type`).

    A province whose 867 holder sits under the realm's ruler belongs to the governor tag whose title is the holder's
    direct-vassal duchy, else to the realm itself (or to one of the realm's other subjects, which keep their own
    lands). Conversely a province owned by the realm or a governor must be held under the realm's ruler in CK3."""
    import provfaiths as pf
    bad = []
    themes = {d.subject for d in DIPLOMACY if d.relation == "theme_subject_type"}
    # (a theme that holds themes of its own, Strymon, is no realm here: its themes sit under the emperor's check)
    for realm in sorted({d.liege for d in DIPLOMACY if d.relation == "theme_subject_type"} - themes):
        subs = {d.subject for d in DIPLOMACY if d.liege == realm}
        govs = {d.subject: BY_TAG[d.subject].ck3_title for d in DIPLOMACY
                if d.liege == realm and d.relation == "theme_subject_type"}
        for d in DIPLOMACY:  # a theme's own themes (Strymon's Thessalonika and Thessaly) are governors too
            if d.relation == "theme_subject_type" and d.liege in govs:
                govs[d.subject] = BY_TAG[d.subject].ck3_title
        top = S.holder(BY_TAG[realm].ck3_title)
        for pid, county in sorted(pf.PROVINCE_COUNTY.items()):
            h = S.holder(county)
            sov = S.sovereign(h)[0] if h else None
            owner = PROVINCE_OWNERS.get(pid)
            if sov != top:
                if owner in govs or owner == realm:
                    bad.append((pid, county, owner, f"held under {sov} in CK3, outside {realm}"))
                continue
            cur, direct, vassal_of_top = h, None, None
            while cur != top:
                prim = S.primary(cur)
                lg = S.liege_holder(prim) if prim else None
                if lg == top:
                    direct = S.primary(cur)
                    vassal_of_top = cur
                    break
                if lg is None or lg == cur:
                    break
                cur = lg
            # the governor tag is the one the direct vassal rules (by holder: his primary title may be a landless family duchy)
            want = next((t for t, ti in govs.items() if ti == direct or (vassal_of_top and S.holder(ti) == vassal_of_top)), realm)
            # a theme's own themes hold the other duchies of the same holder (Strymon, Thessalonika, Thessaly)
            ok = {want} | {t for t, ti in govs.items() if want != realm and S.holder(ti) == S.holder(govs[want])}
            if owner not in ok and not (want == realm and owner in subs):
                bad.append((pid, county, owner, want))
    return bad


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
            # a republic cannot be a vassal: it pays tribute to the realm CK3 gives it as its liege (Venice to Byzantium)
            if liege and rel and BY_TAG[tag].government == "republic" and rel[0][0] in liege:
                continue
            if liege:
                says = f"tributary of {rel[0][0]}" if rel else "independent"
                bad.append((tag, says, f"liege in {'/'.join(liege)}"))
            continue
        for overlord, typ in held:
            if typ in ("union", "theme_subject_type") and ruler.get(overlord) == ruler[tag]:
                continue  # one ruler holding both crowns / the same governor's several duchies
            if not liege:
                bad.append((tag, f"{typ} of {overlord}", "independent"))
            elif overlord not in liege:
                bad.append((tag, f"{typ} of {overlord}", f"liege in {'/'.join(liege)}"))
    return bad


if __name__ == "__main__":
    for tag, mod, ck in mismatches():
        print(f"{tag}: mod says {mod}, CK3 says {ck}")
