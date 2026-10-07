#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

from ck3 import ck3_block
from enc import encname

HERE = Path(__file__).resolve().parent
PROVDATA = HERE / "cache" / "provdata.json"

T = "\t"


def ruler_block_for(t) -> str:
    if t.ruler_block:
        return t.ruler_block
    if t.ck3_title:
        return ck3_block(t.tag)
    raise SystemExit(
        f"{t.tag}: a country written from scratch needs a ruler - "
        f"give it a ruler_block or a ck3_title"
    )


def country_history(t) -> str:
    technology = getattr(t, "technology_group", None) or "western"
    religion = getattr(t, "religion", None) or "catholic"
    government = getattr(t, "government", None) or "monarchy"
    reforms = getattr(t, "reforms", None) or ("feudalism_reform",)
    lines = [f"government = {government}"]
    lines += [f"add_government_reform = {r}" for r in reforms]
    if t.rank is not None:
        lines.append(f"government_rank = {t.rank}")
    lines += [
        f"technology_group = {technology}",
        f"primary_culture = {t.culture}",
        f"religion = {religion}",
        f"capital = {t.capital}",
        ruler_block_for(t),
    ]
    return "\n".join(lines) + "\n"


def country_definition(t) -> str:
    graphical = (
        "easterngfx"
        if getattr(t, "technology_group", None) == "eastern"
        else "westerngfx"
    )
    r, g, b = t.color
    rc = t.revolutionary_colors
    parts = [
        f"graphical_culture = {graphical}",
        "",
        f"color = {{ {r}  {g}  {b} }}",
        "",
        f"revolutionary_colors = {{ {rc[0]}  {rc[1]}  {rc[2]} }}",
        "",
        f"historical_score = {t.historical_score}",
    ]
    if t.historical_units:
        parts += (
            ["", "historical_units = {"]
            + [f"{T}{u}" for u in t.historical_units]
            + ["}"]
        )
    if t.monarch_names:
        parts += [""] + ["monarch_names = {"]
        parts += [
            f'{T}"{encname(name)}" = {weight}' for name, weight in t.monarch_names
        ]
        parts += ["}"]
    if t.leader_names:
        parts += (
            ["", "leader_names = {"] + [f"{T}{ln}" for ln in t.leader_names] + ["}"]
        )
    if t.ship_names:
        parts += ["", "ship_names = {"] + [f"{T}{sn}" for sn in t.ship_names] + ["}"]
    return "\n".join(parts) + "\n"


def basin_provinces(t) -> list[int]:
    data = json.load(open(str(PROVDATA)))
    return sorted({int(p) for a in t.form_areas for p in data["areas"].get(a, ())})


def suppression(t) -> str:
    return "\n".join(
        f"{T}{key} = {{\n"
        f"{T*2}potential = {{\n"
        f"{T*3}always = no\n"
        f"{T*2}}}\n"
        f"{T*2}allow = {{\n"
        f"{T*2}}}\n"
        f"{T*2}effect = {{\n"
        f"{T*2}}}\n"
        f"{T}}}"
        for key in t.suppress
    )


def formation_decision(t) -> str:
    basin = basin_provinces(t)
    form_rank = t.form_rank or 2
    area_or = "\n".join(f"{T*4}area = {a}" for a in t.form_areas)
    claims = "\n".join(
        f"{T*3}{a} = {{\n"
        f"{T*4}limit = {{\n"
        f"{T*5}NOT = {{ is_core = ROOT }}\n"
        f"{T*5}NOT = {{ is_permanent_claim = ROOT }}\n"
        f"{T*4}}}\n"
        f"{T*4}add_permanent_claim = ROOT\n"
        f"{T*3}}}"
        for a in t.form_areas
    )
    held = "\n".join(
        f"{T*4}NOT = {{ {p} = {{ country_or_non_sovereign_subject_holds = ROOT }} }}"
        for p in basin
    )

    return f"""country_decisions = {{
{suppression(t)}

\t{t.decision} = {{
\t\tmajor = yes

\t\tpotential = {{
\t\t\tNOT = {{ map_setup = map_setup_random }}
\t\t\tNOT = {{ tag = {t.forms} }}
\t\t\tNOT = {{ has_country_flag = {t.decision} }}
\t\t\tNOT = {{ exists = {t.forms} }}
\t\t\tis_free_or_tributary_trigger = yes
\t\t\tis_nomad = no
\t\t\ttag = {t.tag}
\t\t\tOR = {{
\t\t\t\tai = no
\t\t\t\tAND = {{
\t\t\t\t\tai = yes
\t\t\t\t\tnum_of_cities = 40
\t\t\t\t}}
\t\t\t}}
\t\t}}

\t\tprovinces_to_highlight = {{
\t\t\tOR = {{
{area_or}
\t\t\t}}
\t\t\tNOT = {{ country_or_non_sovereign_subject_holds = ROOT }}
\t\t}}

\t\tallow = {{
\t\t\tis_at_war = no
\t\t\tis_free_or_tributary_trigger = yes
{held}
\t\t}}

\t\teffect = {{
\t\t\tchange_tag = {t.forms}
\t\t\ton_change_tag_effect = yes
\t\t\tchange_government_to_monarchy = yes
\t\t\tset_country_flag = {t.decision}
\t\t\thidden_effect = {{
\t\t\t\tset_government_rank = {form_rank}
\t\t\t}}
\t\t\tadd_prestige = 25
\t\t\tadd_legitimacy = 10
{claims}
\t\t}}
\t}}
}}
"""
