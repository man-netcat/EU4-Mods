#!/usr/bin/env python3
"""Religions: keys, rite schools, groups, and province faiths against CK3."""

import os
import re
from checks.report import note, warn
from checks.context import GAME, MOD, PDIR


def religion_key_exists_in_vanilla_or_our_additions() -> None:
    """Every religion key exists in vanilla or our additions."""
    print("\n== every religion key exists in vanilla or our additions ==")
    vrel = set(
        re.findall(
            r"(?m)^\s*([a-z_]+)\s*=\s*\{",
            open(
                os.path.join(GAME, "common", "religions", "00_religion.txt"),
                encoding="utf-8",
                errors="replace",
            ).read(),
        )
    )
    own_rel = os.path.join(MOD, "common", "religions", "00_religion.txt")
    if os.path.exists(own_rel):
        vrel |= set(
            re.findall(
                r"(?m)^\s*([a-z_]+)\s*=\s*\{",
                open(own_rel, encoding="utf-8", errors="replace").read(),
            )
        )
    bad_rel = []
    for fn in sorted(os.listdir(PDIR)):
        if not fn.endswith(".txt"):
            continue
        m = re.match(r"^(\d+)", fn)
        if not m:
            continue
        text = open(
            os.path.join(PDIR, fn), encoding="utf-8", errors="surrogateescape"
        ).read()
        for rel in set(re.findall(r"^\s*religion\s*=\s*(\w+)", text, re.M)):
            if rel not in vrel:
                bad_rel.append(f"{m.group(1)} {rel}")
    note(not bad_rel, f"all province religions are real keys ({len(bad_rel)} bad)")
    for b in bad_rel[:8]:
        print("        " + b)


def christian_rite_schools() -> None:
    """Christian rite schools (tools/rites.py)."""
    print("\n== Christian rite schools (tools/rites.py) ==")
    import rites

    rite_err, rite_warn = rites.verify()
    note(not rite_err, f"rite schools verified against CK3, vanilla and history ({len(rite_err)} problems)")
    for e in rite_err:
        print("        " + e)
    for w in rite_warn:
        warn(w)


def religion_groups_follow_ck3_s_religions() -> None:
    """Religion groups follow CK3's religions (tools/faiths.py)."""
    print("\n== religion groups follow CK3's religions (tools/faiths.py) ==")
    import faiths as _faiths

    gm = _faiths.group_misfits()
    note(not gm, f"every lifted religion sits in the group of its CK3 religion ({len(gm)} off)")
    for k, have, want in gm[:12]:
        print(f"        {k} is in {have} but CK3 files it under {want}")


def cultures_and_religions_are_ck3_s() -> None:
    """Cultures and religions are CK3's (tools/cultures.py, tools/religions.py)."""
    print("\n== cultures and religions are CK3's (tools/cultures.py, tools/religions.py) ==")
    import cultures as _cultures
    import religions as _religions

    not_ck3 = sorted(c for c in _cultures.used_in_db() if _cultures.group_of(c) is None)
    note(not not_ck3, f"every culture in use is a CK3 culture ({len(not_ck3)} are not)")
    for c in not_ck3[:12]:
        print(f"        {c}")
    no_block = sorted(f for f in _religions.used_faiths() if f not in _religions.TEMPLATE)
    note(not no_block, f"every religion in use is a CK3 faith the file has a block for ({len(no_block)} lack one)")
    for f in no_block[:12]:
        print(f"        {f}")


def province_religions_track_ck3_s_counties() -> None:
    """Province religions track CK3's counties (tools/provfaiths.py)."""
    print("\n== province religions track CK3's counties (tools/provfaiths.py) ==")
    import provfaiths

    pf_err, pf_warn = provfaiths.verify()
    note(not pf_err, f"audited province religions match CK3 ({len(pf_err)} off, {len(provfaiths.PROVINCE_COUNTY)} audited)")
    for e in pf_err[:20]:
        print("        " + e)
    for w in pf_warn:
        warn(w)


def province_religions_fit_their_surroundings() -> None:
    """Warn when a province's religion does not fit the provinces around it. Two signs of a province paired with the wrong
    CK3 county (Brest-Litovsk with Brittany's Brest, the Crimean Kaffa with Ethiopia's): its religion is found almost only in
    other regions of the world (Waaqism in the Crimea), or it stands alone against an area that is nearly all of one other religion
    (a Chalcedonian Brest among Slavic pagans)."""
    print("\n== province religions fit their surroundings ==")
    import collections
    import sqlite3

    import development as dev
    from paths import EU4_GAME

    areas = {}
    areafile = os.path.join(str(EU4_GAME), "map", "area.txt")
    for name, body in dev._blocks(dev._strip(open(areafile, encoding="latin-1").read())):
        areas[name] = [int(x) for x in re.findall(r"\b\d+\b", re.sub(r"color\s*=\s*\{[^}]*\}", "", body))]
    area_of, region_of = {}, {}
    for name, body in dev._blocks(dev._strip(open(os.path.join(str(EU4_GAME), "map", "region.txt"), encoding="latin-1").read())):
        m = re.search(r"areas = \{(.*?)\}", body, re.S)
        for a in (m.group(1).split() if m else []):
            for p in areas.get(a, []):
                area_of[p], region_of[p] = a, name
    con = sqlite3.connect(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tags.db"))
    prov = {p: (n, r) for p, n, r in con.execute("select pid, name, religion from provinces")}
    owned = {r[0] for r in con.execute("select distinct pid from tag_provinces")} & set(region_of)
    con.close()

    by_rel = collections.defaultdict(collections.Counter)
    for p in owned:
        by_rel[prov[p][1]][region_of[p]] += 1
    warnings = []
    for rel, counts in by_rel.items():  # the regions that between them hold 90% of a religion are its home
        total = sum(counts.values())
        if total < 8:
            continue
        home, run = set(), 0
        for region, n in counts.most_common():
            if run >= 0.9 * total:
                break
            home.add(region)
            run += n
        for p in sorted(owned):
            if prov[p][1] == rel and region_of[p] not in home and counts[region_of[p]] <= 2:
                warnings.append(f"{p} {prov[p][0]} is {rel}, which is found almost only in {', '.join(sorted(home)[:3])}... not in {region_of[p]}")
    in_area = collections.defaultdict(list)
    for p in owned:
        in_area[area_of[p]].append(p)
    for area, ps in in_area.items():
        if len(ps) < 4:
            continue
        (main, n), = collections.Counter(prov[p][1] for p in ps).most_common(1)
        if n < 0.75 * len(ps):
            continue
        for p in ps:
            rel = prov[p][1]
            if rel != main and sum(1 for q in owned if region_of[q] == region_of[p] and prov[q][1] == rel and q != p) <= 1:
                warnings.append(f"{p} {prov[p][0]} is {rel}, alone in {region_of[p]} among {main} in {area}")
    per_province = {}
    for w in sorted(set(warnings)):
        per_province.setdefault(w.split()[0], []).append(w.split(" ", 1)[1])
    for pid in sorted(per_province, key=int):
        warn(f"{pid} " + "; ".join(per_province[pid]))
    note(True, f"{len(per_province)} provinces whose religion does not fit their surroundings (warnings above)")


def run() -> None:
    province_religions_fit_their_surroundings()
    religion_key_exists_in_vanilla_or_our_additions()
    christian_rite_schools()
    religion_groups_follow_ck3_s_religions()
    cultures_and_religions_are_ck3_s()
    province_religions_track_ck3_s_counties()
