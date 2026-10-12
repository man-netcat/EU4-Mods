#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

from ck3 import ck3_block, load_title_colors
from enc import encname
from tagdb import BY_FORMABLE, rank_of, required_count

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
    lines.append(f"government_rank = {rank_of(t)}")
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


def requirement_provinces(fcode) -> list[int]:
    """Province ids a formable requires: its areas expanded via provdata
    plus its explicit provinces."""
    data = json.load(open(str(PROVDATA)))
    fb = BY_FORMABLE[fcode]
    return sorted(
        {int(p) for a in fb.areas for p in data["areas"].get(a, ())}
        | set(fb.provinces)
    )


def formation_decision(fcode, starters) -> str:
    """One shared decision per formable; every starter that can fire it is
    listed in the potential (a single starter keeps the old single-tag line
    so its file stays byte-identical)."""
    fb = BY_FORMABLE[fcode]
    key = starters[0].decision
    required = requirement_provinces(fcode)
    want = required_count(len(required), fb.percent)
    cap_req = ""
    if fb.own_capital:
        cap_req = "\n\t\t\towns = " + str(fb.capital)
    home_req = ""
    if fb.home_capital:
        home_req = f"\n\t\t\t{key}_capital_trigger = yes"
    rank_req = ""
    if fb.rank_required:
        rank_req = f"\n\t\t\tgovernment_rank = {fb.rank_required}"
    elif fb.rank == 3:
        rank_req = "\n\t\t\tNOT = { government_rank = 3 }"
    claims = "\n".join(
        f"{T*3}{a} = {{\n"
        f"{T*4}limit = {{\n"
        f"{T*5}NOT = {{ is_core = ROOT }}\n"
        f"{T*5}NOT = {{ is_permanent_claim = ROOT }}\n"
        f"{T*4}}}\n"
        f"{T*4}add_permanent_claim = ROOT\n"
        f"{T*3}}}"
        for a in fb.areas
    )
    rename = ""
    if fb.renames:
        ordered = sorted(
            ((t, f"tag = {t}", n) for c, t, n in fb.renames if t)
        ) + sorted(
            ((c, f"primary_culture = {c}", n) for c, t, n in fb.renames if c)
        )
        parts = []
        for _key, trig, name in ordered:
            kw = "if" if not parts else "else_if"
            parts.append(
                f"{T*3}{kw} = {{\n"
                f"{T*4}limit = {{\n"
                f"{T*5}{trig}\n"
                f"{T*4}}}\n"
                f"{T*4}override_country_name = {name}\n"
                f"{T*3}}}"
            )
        rename = "\n" + "\n".join(parts)
    if fb.culture_group:
        if len(fb.culture_group) == 1:
            tag_line = f"\t\t\tculture_group = {fb.culture_group[0]}"
        else:
            inner = "\n".join(
                f"\t\t\t\tculture_group = {g}" for g in fb.culture_group
            )
            tag_line = f"\t\t\tOR = {{\n{inner}\n\t\t\t}}"
    elif fb.culture:
        tag_line = f"\t\t\tprimary_culture = {fb.culture}"
    elif len(starters) == 1:
        tag_line = f"\t\t\ttag = {starters[0].tag}"
    else:
        inner = "\n".join(f"\t\t\t\ttag = {s.tag}" for s in starters)
        tag_line = f"\t\t\tOR = {{\n{inner}\n\t\t\t}}"
    return f"""country_decisions = {{
\t{key} = {{
\t\tmajor = yes

\t\tpotential = {{
\t\t\tnormal_or_historical_nations = yes
\t\t\tNOT = {{ has_country_flag = {key} }}
\t\t\tNOT = {{ tag = {fcode} }}
\t\t\tNOT = {{ exists = {fcode} }}
{tag_line}{home_req}{rank_req}
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
\t\t\t{key}_provinces_trigger = yes
\t\t\tNOT = {{ country_or_non_sovereign_subject_holds = ROOT }}
\t\t}}

\t\tallow = {{
\t\t\tnum_of_owned_provinces_with = {{
\t\t\t\tvalue = {want}
\t\t\t\t{key}_provinces_trigger = yes
\t\t\t}}{cap_req}
\t\t\tis_at_war = no
\t\t\tis_free_or_tributary_trigger = yes
\t\t}}

\t\teffect = {{
\t\t\tchange_tag = {fcode}
\t\t\ton_change_tag_effect = yes
\t\t\tchange_government_to_monarchy = yes
\t\t\tset_country_flag = {key}
\t\t\thidden_effect = {{
\t\t\t\tset_government_rank = {fb.rank}
\t\t\t}}
\t\t\tadd_prestige = 25
\t\t\tadd_legitimacy = 10
{claims}{rename}
\t\t}}
\t}}
}}
"""


def formation_trigger_block(name, pids) -> str:
    return (
        f"{name} = {{\n{T}OR = {{\n"
        + "\n".join(_trigger_land_lines(pids))
        + f"\n{T}}}\n}}"
    )


def formation_capital_trigger_block(name, pids) -> str:
    """Homeland-capital check for home_capital formables: the firing tag's
    capital must sit inside the requirement land."""
    return (
        f"{name} = {{\n{T}capital_scope = {{\n{T}OR = {{\n"
        + "\n".join(_trigger_land_lines(pids))
        + f"\n{T}}}\n{T}}}\n}}"
    )


def _trigger_land_lines(pids) -> list[str]:
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
    return lines
