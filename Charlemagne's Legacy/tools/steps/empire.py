#!/usr/bin/env python3
"""The empire: the Karling realms, the imperial land, and the decision to restore the empire."""

import os
import re
from ck3 import load_chars, load_dynasties, load_houses, load_titles, resolve
from histgen import area_claim_lines
from tagdb import DIPLOMACY, PEER_RELATIONS, TITLES
from steps.allocation import build
from steps.layout import GAME, MOD, T
from steps.output import write_out
from steps.provdata import _pd


def karling_realms():
    """(start dynasty, karling tags) lifted from CK3: the dynasty that the
    CK3-synced start holders share, and every CK3-synced tag whose start
    holder carries it."""
    titles, chars = load_titles(), load_chars()
    dyns, houses = load_dynasties(), load_houses()
    dyn_of = {
        tag: resolve(tag, titles, chars, dyns, houses).get("dynasty")
        for tag in sorted(TITLES)
    }
    counts = {}
    for d in dyn_of.values():
        if d:
            counts[d] = counts.get(d, 0) + 1
    dynasty = max(counts, key=counts.get)
    ktags = sorted(t for t, d in dyn_of.items() if d == dynasty)
    return dynasty, ktags


def empire_core():
    alloc = build()
    _, ktags = karling_realms()
    tags = set(ktags)
    tags |= {d.subject for d in DIPLOMACY if d.liege in tags and d.relation not in PEER_RELATIONS}
    return sorted({p for t in tags for p in alloc.get(t, ())})


def step_hre() -> None:
    data = _pd()
    area_of = data["area_of"]

    dynasty, ktags = karling_realms()
    empire_provs = empire_core()
    areas = sorted({area_of[str(p)] for p in empire_provs})

    all_areas = set(
        re.findall(
            r"^\t*([a-z_]+) = \{",
            open(f"{GAME}/map/area.txt", encoding="utf-8", errors="replace").read(),
            re.M,
        )
    )
    missing = [a for a in areas if a not in all_areas]
    assert not missing, f"unknown areas: {missing}"

    claims = "\n".join(area_claim_lines(areas))
    dynasty_line = f'{T*3}dynasty = "{dynasty}"'

    txt = f"""country_decisions = {{

\tkar_form_hre = {{
\t\tmajor = yes

\t\tpotential = {{
\t\t\tNOT = {{ tag = HLR }}
{dynasty_line}
\t\t}}

\t\tprovinces_to_highlight = {{
\t\t\tkar_form_hre_provinces_trigger = yes
\t\t\tNOT = {{ owned_by = ROOT }}
\t\t}}

\t\tallow = {{
\t\t\tnum_of_owned_provinces_with = {{
\t\t\t\tcustom_trigger_tooltip = {{
\t\t\t\t\ttooltip = kar_form_hre_provinces_tooltip
\t\t\t\t\tkar_form_hre_provinces_trigger = yes
\t\t\t\t}}
\t\t\t\tvalue = {len(empire_provs)}
\t\t\t}}
\t\t}}

\t\teffect = {{
\t\t\tchange_tag = HLR
\t\t\ton_change_tag_effect = yes
\t\t\tchange_government_to_monarchy = yes
\t\t\tset_in_empire = no
\t\t\tset_country_flag = kar_formed_hre
\t\t\thidden_effect = {{
\t\t\t\tset_government_rank = 4
\t\t\t}}
\t\t\tif = {{
\t\t\t\tlimit = {{ has_dlc = "Domination" }}
\t\t\t\tadd_government_reform = holy_imperial_monarchy_reform
\t\t\t}}
\t\t\tadd_prestige = 25
\t\t\tadd_legitimacy = 10
{claims}
\t\t}}
\t}}
}}
"""

    os.makedirs(os.path.join(MOD, "decisions"), exist_ok=True)
    p = os.path.join(MOD, "decisions", "KarolingianHRE.txt")
    write_out(p, txt)
    print(f"wrote {p}")
    print(f"  imperial provinces    : {len(empire_provs)}")
    print(f"  areas covered         : {len(areas)}")
    print(
        f"  karling dynasty (ck3): {dynasty} (tags: {', '.join(ktags)}), then the land"
    )
