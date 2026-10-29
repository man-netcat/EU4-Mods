#!/usr/bin/env python3
"""Formation decisions and the restore-empire decision against the land they require; Reconquista claims."""

import json
import os
import re
from checks.report import note
from checks.context import CACHE, MOD, empire_core, parse, province_files


def formation_decisions_and_claims() -> None:
    """Hre decision matches the empire's land; finland decisions cover finland and bothnia; reconquista claims."""
    files = province_files()

    print("\n== hre decision matches the empire's land ==")

    expected = set(empire_core())
    trig = open(
        os.path.join(MOD, "common", "scripted_triggers", "KarolingianFormations.txt"),
        encoding="utf-8",
        errors="replace",
    ).read()
    blk = re.search(
        r"kar_form_hre_provinces_trigger = \{(.*?)\n\}",
        trig,
        re.S,
    )
    body = blk.group(1) if blk else ""
    cdata = json.load(open(str(CACHE / "provdata.json")))
    required = {int(x) for x in re.findall(r"province_id = (\d+)", body)}
    for a in re.findall(r"^\s*area = (\w+)", body, re.M):
        required |= {int(x) for x in cdata["areas"].get(a, ())}
    note(
        required == expected,
        f"trigger covers exactly the {len(expected)} imperial provinces",
    )
    if required != expected:
        print(f"        only in trigger : {sorted(required - expected)}")
        print(f"        only in the core : {sorted(expected - required)}")
    note(
        not (required - expected),
        "no province outside the 867 empire is required to restore it",
    )
    hredec = open(
        os.path.join(MOD, "decisions", "KarolingianHRE.txt"),
        encoding="utf-8",
        errors="replace",
    ).read()
    val = re.search(r"num_of_owned_provinces_with = \{.*?value = (\d+)", hredec, re.S)
    note(
        bool(val) and int(val.group(1)) == len(expected),
        f"decision demands owning {len(expected)} provinces (value)",
    )
    note(
        "dynasty = " in hredec,
        "potential gates on the Karling dynasty",
    )
    hreloc = open(
        os.path.join(MOD, "localisation", "karolingian_hre_l_english.yml"),
        encoding="utf-8",
        errors="replace",
    ).read()
    note(
        "kar_form_hre_title:0" in hreloc,
        "decision name keyed kar_form_hre_title (EU4 reads <key>_title)",
    )

    print("\n== finland decisions cover finland and bothnia ==")

    finland = {27, 28, 29, 31, 4123, 19, 4113, 4152}
    fblk = re.search(
        r"kar_form_finland_provinces_trigger = \{(.*?)\n\}",
        trig,
        re.S,
    )
    fbody = fblk.group(1) if fblk else ""
    freq = {int(x) for x in re.findall(r"province_id = (\d+)", fbody)}
    for a in re.findall(r"^\s*area = (\w+)", fbody, re.M):
        freq |= {int(x) for x in cdata["areas"].get(a, ())}
    note(freq == finland, f"trigger covers exactly the {len(finland)} finnish provinces")
    cblk = re.search(
        r"kar_form_finland_capital_trigger = \{(.*?)\n\}",
        trig,
        re.S,
    )
    cbody = cblk.group(1) if cblk else ""
    creq = {int(x) for x in re.findall(r"province_id = (\d+)", cbody)}
    for a in re.findall(r"^\s*area = (\w+)", cbody, re.M):
        creq |= {int(x) for x in cdata["areas"].get(a, ())}
    note(creq == finland, "capital trigger covers exactly the finnish provinces")
    findec = open(
        os.path.join(MOD, "decisions", "FinlandKingdom.txt"),
        encoding="utf-8",
        errors="replace",
    ).read()
    note(
        "tag = FIN" in findec and "change_tag = FIN" in findec,
        "crown path stays FIN, form path changes to FIN",
    )
    note(
        "NOT = { government_rank = 3 }" in findec,
        "crown path needs Finland below kingdom rank",
    )
    note(
        "NOT = { exists = FIN }" in findec,
        "form path needs Finland gone",
    )
    note(
        "primary_culture = finnish" in findec,
        "form path is finnish-gated",
    )
    note(
        findec.count("NOT = { government_rank = 3 }") >= 2,
        "both finland paths need a non-kingdom firer",
    )
    note(
        "set_government_rank = 3" in findec,
        "both paths crown rank 3",
    )
    finloc = open(
        os.path.join(MOD, "localisation", "finland_l_english.yml"),
        encoding="utf-8",
        errors="replace",
    ).read()
    note(
        "kar_form_finland_title:0" in finloc
        and "kar_crown_finland_title:0" in finloc,
        "both decisions named in loc",
    )

    print("\n== reconquista claims ==")
    from steps.allocation import IBERIA_AREAS

    area_of = {}
    for a, pids in cdata["areas"].items():
        for pid in pids:
            area_of[int(pid)] = a
    bad_rec = []
    for pid, path in files.items():
        s, _, _ = parse(path)
        if s.get("owner") != "ADU" or area_of.get(pid) not in IBERIA_AREAS:
            continue
        text = open(path, encoding="utf-8", errors="surrogateescape").read()
        m = re.search(r"^867\.1\.1 = \{(.*?)^\}", text, re.M | re.S)
        blk = m.group(1) if m else ""
        if "add_claim = ASU" not in blk or "add_claim = NAV" not in blk:
            bad_rec.append(str(pid))
    note(not bad_rec, f"andalusi iberia carries asu+nav claims ({len(bad_rec)} missing)")
    for b in bad_rec[:10]:
        print("        " + b)

    print()


def run() -> None:
    formation_decisions_and_claims()
