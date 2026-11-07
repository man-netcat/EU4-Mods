#!/usr/bin/env python3
"""National ideas: the data is sound, every tag gets a set, and only ours (and the kept government groups) are written."""

import os
import re
from checks.report import note
from checks.context import MOD, BY_TAG


def national_ideas_cover_every_tag() -> None:
    """The idea sets parse and respect the base game's ranges; every tag matches one; the files hold nothing else."""
    print("\n== national ideas (tools/steps/ideas.py, tools/data/ideas) ==")
    from steps import ideas as I
    from tagdb import culture_groups

    sets, problems = I.parse()
    problems += I.check_sets(sets)
    note(not problems, f"{len(sets)} idea sets are well formed and within the base game's ranges ({len(problems)} problems)")
    for p in problems[:10]:
        print("        " + p)

    budget = I.vanilla_budget()
    note(len(budget["powers"]) >= 100, f"the base game's idea sets give a power budget ({len(budget['powers'])} sets measured)")
    worst = max(sets.values(), key=lambda s: I.set_power(s) / I.power_cap(s))
    over = [s["slug"] for s in sets.values() if I.set_power(s) > I.power_cap(s) + 1e-9]
    note(not over, f"no idea set is stronger than the base game's (tag sets under its {int(I.TAG_QUANTILE * 100)}th percentile, "
                   f"culture and group sets under its {int(I.OTHER_QUANTILE * 100)}th, no modifier total above any base-game set's); "
                   f"closest {worst['slug']} {I.set_power(worst):.2f} of {I.power_cap(worst):.2f}")

    group_of = {c: g for g, v in culture_groups().items() for c in v}
    ordered = sorted(sets.values(), key=lambda s: (I.KIND_ORDER[I.kind(s)], s["order"]))

    bare = [t for t, row in BY_TAG.items() if not any(I.matches(s, row, group_of) for s in ordered)]
    note(not bare, f"every tag gets a national idea set of ours, none falls to the default ({len(bare)} do)")
    for t in bare[:10]:
        print(f"        {t} ({BY_TAG[t].culture})")

    ours = {f"kar_{s['slug']}_ideas" for s in sets.values()}
    stray = []
    for fn, allowed in (("00_country_ideas.txt", ours), ("zz_group_ideas.txt", ours | set(I.KEEP_GROUPS))):
        text = open(os.path.join(MOD, "common", "ideas", fn), encoding="cp1252").read()
        names = set(re.findall(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{", text))
        stray += [f"{fn}: {n}" for n in sorted(names - allowed)]
        stray += [f"{fn}: {n} is missing" for n in sorted(allowed - names) if (fn.startswith("00") and n in ours and
                  any(f"kar_{s['slug']}_ideas" == n and I.kind(s) == "tag" for s in sets.values()))]
    note(not stray, f"the idea files hold only our sets and the kept base-game groups ({len(stray)} stray)")
    for s in stray[:10]:
        print("        " + s)

    loc = open(os.path.join(MOD, "localisation", "kar_ideas_l_english.yml"), encoding="utf-8-sig").read()
    missing = [k for k, _ in I.loc_pairs(sets) if f" {k}:0 " not in loc]
    note(not missing, f"every idea set has its names and descriptions in localisation ({len(missing)} missing)")


def run() -> None:
    national_ideas_cover_every_tag()
