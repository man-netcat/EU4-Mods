#!/usr/bin/env python3
"""National ideas: the data is sound, every tag gets a set, and only ours (and the kept government groups) are written."""

import collections
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

    winners = collections.Counter()
    for t_, row in BY_TAG.items():
        first = next((s for s in ordered if I.matches(s, row, group_of)), None)
        if first:
            winners[first["slug"]] += 1
    fallback = sorted(s["slug"] for s in ordered if I.kind(s) != "tag" and not winners[s["slug"]])
    note(True, f"{len(fallback)} culture, group and factor sets win no realm at the start date (they wait for a realm "
               f"that changes religion or government): {', '.join(fallback[:6])}{' ...' if len(fallback) > 6 else ''}")
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


def national_ideas_traps() -> None:
    """What could silently go wrong with the generated idea files, the scripts that name ideas, or the data."""
    print("\n== national ideas: traps ==")
    from steps import ideas as I
    from tagdb import culture_groups

    sets, _ = I.parse()

    left = I.dangling_idea_refs()
    note(not left, f"no script that loads names an idea group or idea that no longer exists ({len(left)} do)")
    for rel, how, name in left[:8]:
        print(f"        {rel}: {how} = {name}")

    groups, twice = I.written_groups()
    shape = []
    for s in sets.values():
        key = f"kar_{s['slug']}_ideas"
        if key not in groups:
            if I.kind(s) != "tag" or any(not neg and what == "tag" and any(v in BY_TAG for v in vs) for neg, what, vs in s["trigger"]):
                shape.append(f"{key} is not written")
            continue
        _f, body, closed = groups[key]
        if not closed:
            shape.append(f"{key}: braces do not balance")
        blocks = I.top_keys(body, 1)
        want = ["start", "bonus", "trigger"] + [f"kar_{s['slug']}_{i}" for i in range(1, 8)]
        if blocks != want:
            shape.append(f"{key}: blocks are {blocks}, expected {want}")
        if not re.search(r"(?m)^\s*free\s*=\s*yes\s*$", body):
            shape.append(f"{key}: no `free = yes`, the game would never offer it")
    note(not shape and not twice, f"every written idea group is complete (start, bonus, trigger, free, seven ideas) and defined once "
                                  f"({len(shape)} malformed, {len(twice)} defined twice)")
    for line in (shape + [f"{n} defined twice" for n in twice])[:8]:
        print("        " + line)

    clash = sorted({n for n in I.known_idea_names() if n.startswith("kar_")} - {f"kar_{s['slug']}_ideas" for s in sets.values()}
                   - {f"kar_{s['slug']}_{i}" for s in sets.values() for i in range(1, 8)})
    note(not clash, f"no idea key with our prefix is left over from an earlier build ({len(clash)} are)")
    for n in clash[:8]:
        print("        " + n)

    names = I.engine_names()
    unknown = []
    for s in sets.values():
        for neg, what, values in s["trigger"]:
            if what in names:
                unknown += [f"{s['slug']}: {what} {v}" for v in values if v not in names[what] and what != "rank"]
    note(not unknown, f"every religion, government, reform and technology group a trigger names exists in the game files ({len(unknown)} do not)")
    for u in unknown[:8]:
        print("        " + u)

    claimed = collections.defaultdict(list)
    for s in sets.values():
        if I.kind(s) == "tag":
            for neg, what, values in s["trigger"]:
                if not neg and what == "tag":
                    for v in values:
                        claimed[v].append(s["slug"])
    both = {t: v for t, v in claimed.items() if len(v) > 1}
    note(not both, f"no tag is listed by two tag sets, the second would never be used ({len(both)} are)")
    for t, v in list(both.items())[:8]:
        print(f"        {t}: {', '.join(v)}")

    wrong = I.wrong_way(sets)
    note(not wrong, f"no modifier points the opposite way from the base game's use of it, which would make a bonus a malus ({len(wrong)} do)")
    for slug, where, key, val in wrong[:8]:
        print(f"        {slug} {where}: {key} {val:g}")


def run() -> None:
    national_ideas_cover_every_tag()
    national_ideas_traps()
