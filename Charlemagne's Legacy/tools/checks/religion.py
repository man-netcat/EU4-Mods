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


def run() -> None:
    religion_key_exists_in_vanilla_or_our_additions()
    christian_rite_schools()
    religion_groups_follow_ck3_s_religions()
    cultures_and_religions_are_ck3_s()
    province_religions_track_ck3_s_counties()
