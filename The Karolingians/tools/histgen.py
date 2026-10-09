#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

from ck3 import ck3_block, load_title_colors
from enc import encname

HERE = Path(__file__).resolve().parent
PROVDATA = HERE / "cache" / "provdata.json"

T = "\t"


def ruler_block_for(t) -> str:
    if t.ck3_title:
        return ck3_block(t.tag)
    raise SystemExit(
        f"{t.tag}: no ck3_title - give it one, " f"so its 867 ruler is lifted from CK3"
    )


def country_history(t) -> str:
    lines = [f"government = {t.government}"]
    lines += [f"add_government_reform = {r}" for r in t.reforms]
    lines.append(f"government_rank = {t.rank}")
    lines += [
        f"technology_group = {t.technology_group}",
        f"primary_culture = {t.culture}",
        f"religion = {t.religion}",
        f"capital = {t.capital}",
    ]
    if t.extra:
        lines.append(t.extra.rstrip("\n"))
    lines.append(ruler_block_for(t))
    return "\n".join(lines) + "\n"


def lifted_color(t):
    """The CK3 map colour of the title behind the tag; falls back to the
    tag's own declared colour when CK3 has no colour for that title."""
    if t.ck3_title:
        got = load_title_colors().get(t.ck3_title)
        if got:
            return got
    return t.color


def country_definition(t) -> str:
    graphical = "easterngfx" if t.technology_group == "eastern" else "westerngfx"
    r, g, b = lifted_color(t)
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

    return f"""country_decisions = {{
{suppression(t)}

\t{t.decision} = {{
\t\tmajor = yes

\t\tpotential = {{
\t\t\tnormal_or_historical_nations = yes
\t\t\tNOT = {{ has_country_flag = {t.decision} }}
\t\t\tNOT = {{ tag = {t.forms} }}
\t\t\tNOT = {{ exists = {t.forms} }}
\t\t\ttag = {t.tag}
\t\t\tOR = {{
\t\t\t\tai = no
\t\t\t\tis_playing_custom_nation = no
\t\t\t}}
\t\t\tOR = {{
\t\t\t\tis_free_or_tributary_trigger = yes
\t\t\t\tai = no
\t\t\t}}
\t\t}}

\t\tprovinces_to_highlight = {{
\t\t\tOR = {{
{area_or}
\t\t\t}}
\t\t\tNOT = {{ country_or_non_sovereign_subject_holds = ROOT }}
\t\t}}

\t\tallow = {{
\t\t\tnum_of_owned_provinces_with = {{
\t\t\t\tcustom_trigger_tooltip = {{
\t\t\t\t\ttooltip = {t.decision}_provinces_tooltip
\t\t\t\t\t{t.decision}_provinces_trigger = yes
\t\t\t\t}}
\t\t\t\tvalue = {len(basin)}
\t\t\t}}
\t\t\tis_at_war = no
\t\t\tis_free_or_tributary_trigger = yes
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


def formation_trigger_block(name, pids) -> str:
    data = json.load(open(str(PROVDATA)))
    want = set(pids)
    used: set = set()
    lines = []
    for a in sorted(data["areas"]):
        aps = {int(x) for x in data["areas"][a]}
        if aps and aps <= want:
            lines.append(f"{T*2}area = {a}")
            used |= aps
    for p in sorted(want - used):
        nm = data["provs"].get(str(p), {}).get("name")
        lines.append(f"{T*2}province_id = {p}" + (f" #{nm.lower()}" if nm else ""))
    return f"{name} = {{\n{T}OR = {{\n" + "\n".join(lines) + f"\n{T}}}\n}}"
