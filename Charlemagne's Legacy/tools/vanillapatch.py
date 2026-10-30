#!/usr/bin/env python3
"""The few base-game files the mod changes, written from the base game's own copy.

Each entry is a file path and the edits made to it: the lines to find (context
first), the lines they were and the lines they become. The base game's text is
read at build time, so the repository holds only the edits (ours), never the
file. An edit whose context no longer matches (after a game patch) stops the
build, so an update is noticed rather than silently dropped.

    PATCHES[path] = [(context lines, old lines, new lines), ...]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import EU4_GAME  # noqa: E402

MOD = os.path.join(HERE, "..")

PATCHES = {
 "common/defines.lua": [
  [
   [
    "NGame = {"
   ],
   [
    "\tSTART_DATE = \"1444.11.11\","
   ],
   [
    "\tSTART_DATE = \"867.1.1\","
   ]
  ],
  [
   [
    "\tCULTURAL_UNION_MIN_DEV = 1000,\t\t\t\t-- Minimum development to get cultural union effect without Common Sense, or if CULTURAL_UNION_MIN_RANK is set to negative value."
   ],
   [
    "\tCULTURAL_UNION_MIN_RANK = 3,\t\t\t\t-- Minimum rank to get cultural union effect with Common Sense."
   ],
   [
    "\tCULTURAL_UNION_MIN_RANK = 4,\t\t\t\t-- Minimum rank to get cultural union effect with Common Sense."
   ]
  ],
  [
   [
    "\tADDITIONAL_MIN_DEVELOPMENT_FOR_GOV_RANK_X = 500,\t-- ADDITIONAL development needed to upgrade to government rank above 3"
   ],
   [
    "\tMAX_GOV_RANK = 3,\t\t\t\t\t\t\t\t\t-- Max possible is 10"
   ],
   [
    "\tMAX_GOV_RANK = 5,\t\t\t\t\t\t\t\t\t-- Max possible is 10"
   ]
  ],
  [
   [
    "\tFORT_MOTHBALL_SAFETY_DISTANCE = 5, -- How far from the border AI will mothball forts"
   ],
   [
    "\tFORT_CAPITAL_DESIRE = 0.5, -- How much does the AI want a fort in its capital? (adds to regular reasons)"
   ],
   [
    "\tFORT_CAPITAL_DESIRE = 0, -- the Karolingians: capitals stay unfortified unless scripted (see provinces.fort); the AI must not rebuild what the start date removed"
   ]
  ]
 ],
 "common/government_reforms/01_government_reforms_monarchies.txt": [
  [
   [
    "\t\tvassal_income = 0.25",
    "\t\tnobles_influence_modifier = 0.05",
    "\t\tmaratha_exclusive_influence_modifier = 0.05",
    "\t\trajput_exclusive_influence_modifier = 0.05",
    "\t}",
    "\tcustom_attributes = {",
    "\t\tbuffed_strong_duchies = yes #+5% Loyalty"
   ],
   [],
   [
    "\t}",
    "\tai = {",
    "\t\tfactor = 0.5 #generic",
    "\t}",
    "}",
    "",
    "# The Magyar horse-lords fight from the saddle: a tier-1 pick for MGY",
    "# (replacing feudalism, which is dead weight without vassals) inherited by",
    "# no one - formation strips it for feudalism. The flat force limit aims",
    "# MGY at roughly 20 total; the maintenance line keeps the host affordable",
    "# on steppe income. Numbers are first-pass for the balance pass.",
    "magyar_horse_lords_reform = {",
    "\ticon = \"cavalry\"",
    "\tallow_normal_conversion = yes",
    "\tvalid_for_nation_designer = no",
    "\tpotential = {",
    "\t\ttag = MGY",
    "\t}",
    "\tmodifiers = {",
    "\t\tcavalry_power = 0.2",
    "\t\tcavalry_cost = -0.15",
    "\t\tland_forcelimit = 12",
    "\t\tland_maintenance_modifier = -0.25"
   ]
  ],
  [
   [
    "\tallow_normal_conversion = yes",
    "\tpotential = {",
    "\t\tNOT = { has_country_flag = formed_japan_flag }",
    "\t\tOR = {"
   ],
   [],
   [
    "\t\t\ttag = JAP # the Kampaku regency of our Japan (Charlemagne's Legacy)"
   ]
  ],
  [
   [
    "\tlegacy_equivalent = shogunate_legacy"
   ],
   [
    "\tfixed_rank = 2"
   ],
   [
    "\t# fixed_rank dropped: JAP's rank follows its CK3 title (Kampaku at the empire)"
   ]
  ],
  [
   [
    "\tlegacy_equivalent = daimyo_legacy"
   ],
   [
    "\tfixed_rank = 1"
   ],
   [
    "\t# fixed_rank dropped: Kuni sit at their held title's rank"
   ]
  ],
  [
   [
    ""
   ],
   [
    "\tfixed_rank = 3"
   ],
   []
  ],
  [
   [
    "\t\tburghers_influence_modifier = -0.1"
   ],
   [
    "\t\tgoverning_capacity = 500"
   ],
   []
  ]
 ],
 "common/subject_types/00_subject_types.txt": [
  [
   [],
   [],
   [
    "",
    "# Karolingian: vanilla copy, three edits - vassal max_government_rank 1 -> 0, vassal forcelimit_to_overlord 0.1 -> 0.0, march 0.2 -> 0.1.",
    "# Engine (CCountry::CalcGovernmentRank) clamps a subject's rank down to its",
    "# subject type's max_government_rank; CK3-true vassals (TRA/VSG/GTH/DAL/",
    "# SIC/CST/ARG/PRT) hold duchy titles and must read as Duchy (user 18 Oct 2026).",
    "# personal_union and tributary_state inherit the default (no limit) already.",
    "# Re-sync against the base game on patches; keep the vassal line flipped."
   ]
  ],
  [
   [
    ""
   ],
   [
    "\tmax_government_rank = 1"
   ],
   [
    "\tmax_government_rank = 0\t\t\t\t\t\t# CK3 ranks: vassalage shows at the held title's rank"
   ]
  ],
  [
   [
    "\tpays_overlord = 1.0"
   ],
   [
    "\tforcelimit_to_overlord = 0.1"
   ],
   [
    "\tforcelimit_to_overlord = 0.0\t\t\t\t\t# vassals add nothing to the overlord's force limit (slots come with rank instead)"
   ]
  ],
  [
   [],
   [
    "march = {"
   ],
   [
    "# BEGIN kar theme",
    "# The Byzantine themes: governors the emperor appointed, not rivals of the throne. A vassal in every respect the",
    "# scripts see (count = vassal) but no relation slot, no relative-power liberty pull (a tiny capital against twenty",
    "# governors would put them all in revolt), loyal by default, and half of their force limit and manpower go to the",
    "# emperor, whose own few counties carry no army (user request, 29 Oct 2026).",
    "theme_subject_type = {",
    "\tcopy_from = vassal",
    "\tcount = vassal",
    "\ttakes_diplo_slot = no",
    "\trelative_power_class = 0",
    "\tliberty_desire_development_ratio = 0.0",
    "\tbase_liberty_desire = -25.0",
    "\tforcelimit_to_overlord = 0.25",
    "\tmanpower_to_overlord = 0.25",
    "}",
    "# END kar theme",
    "",
    "march = {"
   ]
  ],
  [
   [
    "\tbase_liberty_desire = -15.0",
    "\tcan_be_annexed = no"
   ],
   [
    "\tforcelimit_to_overlord = 0.2"
   ],
   [
    "\tforcelimit_to_overlord = 0.1"
   ]
  ]
 ],
 "common/static_modifiers/00_static_modifiers.txt": [
  [
   [
    "vassal_subject = {"
   ],
   [
    "\tland_forcelimit = 1"
   ],
   [
    "\t# no flat force limit per vassal"
   ]
  ],
  [
   [
    "\ttolerance_own = 3"
   ],
   [
    "\tdiplomatic_upkeep = 4"
   ],
   [
    "\tdiplomatic_upkeep = 5\t\t\t\t\t\t# +1 for every country (a county's vassal slot); each government rank above adds one more"
   ]
  ]
 ]
}

def patched(path):
    raw = open(os.path.join(str(EU4_GAME), path), "rb").read().decode("latin-1")
    lines = raw.replace("\r\n", "\n").split("\n")
    for ctx, old, new in PATCHES[path]:
        seq = ctx + old
        if not seq:
            lines[0:0] = new
            continue
        hits = [i for i in range(len(lines) - len(seq) + 1) if lines[i:i + len(seq)] == seq]
        if len(hits) != 1:
            raise SystemExit(f"vanillapatch: {path}: edit after {ctx[-1:]!r} matches {len(hits)} places "
                             "in the base game's file (changed by a patch?)")
        at = hits[0] + len(ctx)
        lines[at:at + len(old)] = new
    return "\n".join(lines)


def write(check=False):
    stale = []
    for path in PATCHES:
        text = patched(path)
        dest = os.path.join(MOD, path)
        old = open(dest, "rb").read().decode("latin-1") if os.path.exists(dest) else None
        if old != text:
            stale.append(path)
            if not check:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                open(dest, "wb").write(text.encode("latin-1"))
    return stale


def step_vanilla_patches():
    stale = write()
    print(f"  {len(PATCHES)} patched base-game files" + (f" (rewrote {', '.join(stale)})" if stale else " (unchanged)"))
    return 0


if __name__ == "__main__":
    check = "--check" in sys.argv
    stale = write(check)
    for p in stale:
        print(("stale: " if check else "wrote ") + p)
    sys.exit(1 if (check and stale) else 0)
