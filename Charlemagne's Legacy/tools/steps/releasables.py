#!/usr/bin/env python3
"""The releasables: dormant county tags that wake by event.

Each tag in the `releasables` table holds nothing at the start; its county (and any others it lists) keeps the owner,
with the tag's core seeded on it (`seed_cores`). Two wake-ups are generated here, both choices for the province's owner:

* at the CK3 independence year of the county (the first year of the first ten-year run in which its 867-chain holder is
  an independent ruler whose top title is that county; lifted from CK3 at each build), `kar_releasables.N`;
* for the `hre` ones, when a Karolingian ruler forms the empire (the decision schedules `kar_releasables.100` a year later):
  the emperor may free every one of them that sits on his land.
"""

import re

import ck3
import state867 as S
from steps.layout import MOD
from steps.output import write_loc, write_out
from tagdb import BY_TAG, RELEASABLES, SEED_CORES, TAGS

FIRST, LAST, RUN = 868, 1100, 10
HRE_EVENT = 100


def independence_years(titles):
    """{title: first year of a RUN-year stretch in which CK3's holder of the title rules independently with the county
    as top title, or None}; one pass over the years for all titles (each year re-indexes every title's holder)."""
    saved = ck3.DATE, S._DATE
    held = {t: set() for t in titles}
    try:
        for y in range(FIRST, LAST + 1):
            ck3.DATE = f"{y}.1.1"
            S._DATE = ck3._date_key(ck3.DATE)
            S._held.clear()
            for t in titles:
                h = S.holder(t)
                if h:
                    prim = S.primary(h)
                    if prim and prim[0] == "c" and S.sovereign(h)[0] == h:
                        held[t].add(y)
    finally:
        ck3.DATE, S._DATE = saved
        S._held.clear()
    out = {}
    for t, ys in held.items():
        out[t] = next((y for y in sorted(ys) if all(y + i in ys for i in range(RUN))), None)
    return out


def _provinces(tag):
    return sorted(p for p, ts in SEED_CORES.items() if tag in ts)


def _owns(provs, indent):
    return "\n".join(f"{indent}owns = {p}" for p in provs)


def step_releasables():
    order = {t.tag: i for i, t in enumerate(TAGS)}
    tags = sorted(RELEASABLES, key=order.get)
    ev, loc, years = [], [], {}
    by_title = independence_years([BY_TAG[t].ck3_title for t in tags])
    for n, tag in enumerate(tags, 1):
        provs = _provinces(tag)
        year = by_title[BY_TAG[tag].ck3_title]
        if year is None:
            raise SystemExit(f"{tag} ({BY_TAG[tag].ck3_title}) is never independent in CK3 between {FIRST} and {LAST}")
        years[tag] = year
        eid = f"kar_releasables.{n}"
        cores = "\n".join(f"\t\t\t{p} = {{ limit = {{ owned_by = ROOT }} add_unrest = 5 }}" for p in provs)
        ev.append(f"""# {BY_TAG[tag].ck3_title}: independent in CK3 from {year}
country_event = {{
	id = {eid}
	title = {eid}.t
	desc = {eid}.d
	picture = CIVIL_WAR_eventPicture

	fire_only_once = yes

	trigger = {{
		NOT = {{ exists = {tag} }}
		is_year = {year}
		NOT = {{ tag = {tag} }}
		OR = {{
{_owns(provs, chr(9) * 3)}
		}}
	}}

	mean_time_to_happen = {{
		months = 24
	}}

	option = {{
		name = {eid}.a
		ai_chance = {{ factor = 20 }}
		release = {tag}
	}}

	option = {{
		name = {eid}.b
		ai_chance = {{ factor = 80 }}
{cores}
	}}
}}
""")
        loc += [(f"{eid}.t", f"[{tag}.GetName] Wants Its Freedom"),
                (f"{eid}.d", f"The lords and townsmen of [{tag}.GetName] have long chafed under their overlord and now have a ruler of their own who will not kneel. We can let them go or hold them by force."),
                (f"{eid}.a", "Let them go."),
                (f"{eid}.b", "They will learn their place.")]
    hre = [t for t in tags if RELEASABLES[t]]
    releases = "\n".join(
        f"\t\t\tif = {{\n\t\t\t\tlimit = {{\n\t\t\t\t\tNOT = {{ exists = {t} }}\n\t\t\t\t\tOR = {{\n{_owns(_provinces(t), chr(9) * 6)}\n\t\t\t\t\t}}\n\t\t\t\t}}\n\t\t\t\trelease = {t}\n\t\t\t}}"
        for t in hre)
    ev.append(f"""# The Karolingian Empire is formed: the emperor may grant immediacy to the free counties and bishoprics of the Empire's heartland
country_event = {{
	id = kar_releasables.{HRE_EVENT}
	title = kar_releasables.{HRE_EVENT}.t
	desc = kar_releasables.{HRE_EVENT}.d
	picture = DIPLOMACY_eventPicture

	major = yes
	is_triggered_only = yes
	fire_only_once = yes

	trigger = {{
		tag = HLR
	}}

	option = {{
		name = kar_releasables.{HRE_EVENT}.a
		ai_chance = {{ factor = 50 }}
		add_prestige = 10
		hidden_effect = {{
{releases}
		}}
	}}

	option = {{
		name = kar_releasables.{HRE_EVENT}.b
		ai_chance = {{ factor = 50 }}
		add_legitimacy = 5
	}}
}}
""")
    loc += [(f"kar_releasables.{HRE_EVENT}.t", "Imperial Immediacy"),
            (f"kar_releasables.{HRE_EVENT}.d", "Now that the Empire is whole again, the cities and bishoprics along the Rhine, the Danube and the Elbe ask for the charters their forefathers held from Charlemagne: to answer to the emperor alone. Granting them frees them of their present lords; refusing keeps the land in our hands."),
            (f"kar_releasables.{HRE_EVENT}.a", "Grant them immediacy."),
            (f"kar_releasables.{HRE_EVENT}.b", "The Empire's land is ours.")]
    head = ("# Generated by tools/steps/releasables.py from the `releasables` table and CK3's county history.\n"
            "namespace = kar_releasables\n\n")
    write_out(f"{MOD}/events/KarReleasables.txt", head + "\n".join(ev))
    write_loc(f"{MOD}/localisation/kar_releasables_l_english.yml", loc)
    print(f"wrote events/KarReleasables.txt: {len(tags)} releasables ({len(hre)} imperial), years "
          + ", ".join(f"{t} {y}" for t, y in years.items()))
