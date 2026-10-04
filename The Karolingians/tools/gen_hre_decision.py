#!/usr/bin/env python3
"""Emit the 'Restore the Holy Roman Empire' decision for The Karolingians.

Follows the same shape as vanilla's own nation-forming decisions
(decisions/GermanNation.txt, decisions/RestoreRomanEmpire.txt):

    potential  -> who is even allowed to try (nation type, flags, tag)
    allow      -> the actual requirement, so the UI shows it with a red X
    effect     -> change_tag = HLR + on_change_tag_effect

change_tag is a real tag switch, exactly how vanilla forms GER or ROM, so this
genuinely becomes the HLR rather than just renaming the country.
"""
import json, os, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

MOD = str(HERE.parent)
GAME = "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV"
d = json.load(open(str(CACHE / "provdata.json")))
alloc = json.load(open(str(CACHE / "alloc.json")))
area_of = d["area_of"]

# The Karolingian sphere is exactly the land the five kingdoms start with.
# Every other realm - Lusatia, Brittany, or anything added later - sits outside
# it: neither required to restore the empire, nor able to restore it. Areas are
# therefore derived from the five alone, which drops lusatia_area and
# south_saxony_area. The allow block is built per province rather than per area
# so that an outsider holding a province inside a covered area does not drag
# that province into the requirement - thuringia_area, for instance, holds
# Lusatia's Vogtland alongside East Francia's Thuringian core.
FIVE = ["FRA", "LOT", "GER", "BAV", "ITA"]
provs = sorted({int(p) for t in FIVE for p in alloc[t]})
areas = sorted({area_of[str(p)] for p in provs})

all_areas = set(re.findall(r"^\t*([a-z_]+) = \{",
    open(f"{GAME}/map/area.txt", encoding="utf-8", errors="replace").read(), re.M))
missing = [a for a in areas if a not in all_areas]
assert not missing, f"unknown areas: {missing}"

T = "\t"
area_or = "\n".join(f"{T*4}area = {a}" for a in areas)
claims = "\n".join(
    f"{T*3}{a} = {{\n"
    f"{T*4}limit = {{\n"
    f"{T*5}NOT = {{ is_core = ROOT }}\n"
    f"{T*5}NOT = {{ is_permanent_claim = ROOT }}\n"
    f"{T*4}}}\n"
    f"{T*4}add_permanent_claim = ROOT\n"
    f"{T*3}}}" for a in areas)
# potential: mere eligibility. Being one of the five Carolingian tags is the
# whole test - Lusatia, Brittany or any other realm is excluded here and can
# never see the decision, however much land it holds. An earlier version also
# demanded the other four be extinct, but a tag always exists while you are
# playing it, so that condition belongs in allow, not here.
is_carolingian = "\n".join(f"{T*4}tag = {t}" for t in FIVE)
# allow, part one: you must be the last of the five standing. One branch per
# tag, because "the other four" depends on which one you are.
per_tag = "\n".join(
    f"{T*4}AND = {{\n"
    + f"{T*5}tag = {me}\n"
    + "\n".join(f"{T*5}NOT = {{ exists = {o} }}" for o in FIVE if o != me)
    + f"\n{T*4}}}"
    for me in FIVE)
# allow, part two: exact land. You must hold every province the five kingdoms
# start with, and not one province more. "NOT = { <id> = { ... } }" is true when
# that province is not held by you or your non-sovereign subjects.
held = "\n".join(
    f"{T*4}NOT = {{ {p} = {{ country_or_non_sovereign_subject_holds = ROOT }} }}"
    for p in provs)

txt = f"""# The Karolingians - "Unite the Karlings"
#
# The 867 partition is split across five kingdoms and the imperial title has no
# land at all. Once a ruler holds the old Carolingian heartlands in one hand
# the empire can be made whole again. This mirrors vanilla's own "form Germany"
# / "Restore Roman Empire" decisions and uses change_tag, so the country really
# becomes HLR - displayed as the Karolingian Empire - rather than merely
# renaming itself.

country_decisions = {{

\tkar_form_hre = {{
\t\tmajor = yes

\t\tpotential = {{
\t\t\tNOT = {{ map_setup = map_setup_random }}
\t\t\tNOT = {{ tag = HLR }}
\t\t\tNOT = {{ has_country_flag = kar_formed_hre }}
\t\t\tNOT = {{ exists = ROM }}
\t\t\tNOT = {{ exists = ARH }}
\t\t\tis_free_or_tributary_trigger = yes
\t\t\tis_nomad = no
\t\t\tOR = {{
\t\t\t\tai = no
\t\t\t\tAND = {{
\t\t\t\t\tai = yes
\t\t\t\t\tnum_of_cities = 40
\t\t\t\t}}
\t\t\t}}
\t\t\t# Eligibility only: any of the five Carolingian tags may try. Lusatia
\t\t\t# and every other realm fail this test, so they never see the decision.
\t\t\tOR = {{
{is_carolingian}
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
\t\t\t# The empire can only be made whole by the last of the five standing,
\t\t\t# once it also holds every province the five started with. Lusatia's
\t\t\t# land is deliberately absent from that list.
\t\t\tOR = {{
{per_tag}
\t\t\t}}
{held}
\t\t}}

\t\teffect = {{
\t\t\tchange_tag = HLR
\t\t\ton_change_tag_effect = yes
\t\t\tchange_government_to_monarchy = yes
\t\t\tset_country_flag = kar_formed_hre
\t\t\thidden_effect = {{
\t\t\t\tset_government_rank = 3
\t\t\t}}
\t\t\tif = {{
\t\t\t\tlimit = {{ has_dlc = "Domination" }}
\t\t\t\tadd_government_reform = holy_imperial_monarchy_reform
\t\t\t}}
\t\t\tadd_prestige = 25
\t\t\tadd_legitimacy = 10

\t\t\t# claim the rest of the former empire for good
{claims}
\t\t}}
\t}}
}}
"""

os.makedirs(os.path.join(MOD, "decisions"), exist_ok=True)
p = os.path.join(MOD, "decisions", "KarolingianHRE.txt")
open(p, "w", encoding="utf-8").write(txt)
print(f"wrote {p}")
print(f"  karolingian provinces : {len(provs)}")
print(f"  areas covered         : {len(areas)}")
print(f"  allow requires         : all {len(provs)} provinces of the five kingdoms (exact)")
print(f"  outside the sphere     : Lusatia and any other tag, both land and title")