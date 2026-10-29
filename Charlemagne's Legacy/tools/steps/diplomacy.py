#!/usr/bin/env python3
"""Start-date relations between tags: subjects, alliances, marriages, guarantees, and the preset wars."""

import os
from tagdb import CTRY_DATE, PEER_RELATIONS, WARS
from steps.layout import MOD
from steps.output import write_out


def step_diplomacy() -> None:
    lines = [
        "# Starting subjects and guarantees of the Carolingian world.",
        f"# Every subject relation is created at the start date ({CTRY_DATE}): a vassal can be integrated 50 years after",
        "# that (defines INTEGRATE_VASSAL_MIN_YEARS), not at once as a relation without a start_date can.",
    ]
    from marriages import all_relations  # lifted from CK3 (alliances and marriages between rulers' families)

    relations = all_relations()
    for rel in relations:
        if rel.relation == "vassal":
            lines += [
                "vassal = {",
                "\tfirst = " + rel.liege,
                "\tsecond = " + rel.subject,
                f"\tstart_date = {CTRY_DATE}",
                "}",
            ]
        elif rel.relation == "guarantee":
            lines += [
                "guarantee = {",
                "\tfirst = " + rel.liege,
                "\tsecond = " + rel.subject,
                "}",
            ]
        elif rel.relation in PEER_RELATIONS:
            lines += [
                rel.relation + " = {",
                "\tfirst = " + rel.liege,
                "\tsecond = " + rel.subject,
                "}",
            ]
        elif rel.relation == "union":
            lines += [
                "union = {",
                "\tfirst = " + rel.liege,
                "\tsecond = " + rel.subject,
                f"\tstart_date = {CTRY_DATE}",
                "}",
            ]
        else:
            lines += [
                "dependency = {",
                "\tsubject_type = " + rel.relation,
                "\tfirst = " + rel.liege,
                "\tsecond = " + rel.subject,
                f"\tstart_date = {CTRY_DATE}",
                "}",
            ]
    path = os.path.join(MOD, "history", "diplomacy", "karolingian_vassals.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines += [
        "867.1.1 = { celestial_emperor = TNG }",
    ]
    write_out(path, "\n".join(lines) + "\n")
    pairs = ", ".join(f"{d.subject} {d.relation} {d.liege}" for d in relations)
    print(f"wrote {path}  ({pairs})")


def step_wars() -> None:
    wdir = os.path.join(MOD, "history", "wars")
    os.makedirs(wdir, exist_ok=True)
    live = set()
    for w in WARS:
        sides = "\n".join(
            [f"\tadd_attacker = {t}" for t in w.attackers]
            + [f"\tadd_defender = {t}" for t in w.defenders]
        )
        objective = (
            f"\tprovince = {w.goal_province}"
            if w.goal_province
            else f"\ttag = {w.goal_tag}"
        )
        txt = (
            f'name = "{w.title}"\n'
            f"war_goal = {{\n"
            f"\ttype = {w.goal}\n"
            f"\tcasus_belli = {w.cb}\n"
            f"{objective}\n"
            f"}}\n\n"
            f"{w.date} = {{\n{sides}\n}}\n"
        )
        p = os.path.join(wdir, f"{w.slug}.txt")
        write_out(p, txt)
        live.add(f"{w.slug}.txt")
        print(f"wrote {p}  ({w.title})")
    for fn in sorted(os.listdir(wdir)):
        if fn.endswith(".txt") and fn not in live:
            os.remove(os.path.join(wdir, fn))
            print(f"removed stale {fn}")
