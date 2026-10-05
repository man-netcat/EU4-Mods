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
import json, os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_provinces import empire_core

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

MOD = str(HERE.parent)
GAME = "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV"
d = json.load(open(str(CACHE / "provdata.json")))
area_of = d["area_of"]

# The empire is defined by where it was in 867, not by who holds it. There is no
# list of eligible tags here and no realm that is privileged: the requirement is
# land, and any tag that comes to hold all of it may form the empire. That
# includes Lusatia, Brittany, and anything added later - none of which is named
# as an outsider anywhere in this file, because none of them is one.
#
# empire_core() comes from gen_provinces, where the 60 areas and the 11
# documented non-imperial provinces live, so the decision cannot disagree with
# the rest of the mod about where the empire was.
provs = empire_core()
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
# allow: land, and nothing else. "NOT = { <id> = { ... } }" is true when that
# province is not held by you or your non-sovereign subjects, so requiring every
# one of them to be false means holding all of them.
held = "\n".join(
    f"{T*4}NOT = {{ {p} = {{ country_or_non_sovereign_subject_holds = ROOT }} }}"
    for p in provs)

txt = f"""# The Karolingians - "Unite the Karlings"
#
# The imperial title has no land at all in 867, because the empire is split
# among its heirs. Once one ruler holds the old imperial heartlands in a single
# hand the empire can be made whole again. This mirrors vanilla's own "form
# Germany" / "Restore Roman Empire" decisions and uses change_tag, so the
# country really becomes HLR rather than merely renaming itself.
#
# Any ruler who comes to hold that land may do this. The decision names no
# realm as eligible or ineligible, because the empire is a place, not a set of
# dynasties: whether the five Frankish kingdoms, Lusatia, or anyone else
# reunites it is the game's business, not this file's.

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
\t\t\t# No tag test at all. Whichever ruler ends up holding the old imperial
\t\t\t# land may try, so no realm is excluded for being the realm it is.
\t\t\t# The land requirement in allow is the entire test.
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
\t\t\t# One ruler holding every imperial province. There is deliberately no
\t\t\t# "and not one province more" clause, and no requirement that any
\t\t\t# particular realm have died out: both described the five-kingdom
\t\t\t# partition, and neither is a fact about the empire itself.
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
print(f"  imperial provinces    : {len(provs)}")
print(f"  areas covered         : {len(areas)}")
print(f"  eligible tags         : any - the requirement is land, not a tag list")