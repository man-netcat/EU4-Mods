#!/usr/bin/env python3
"""The early technology levels: sixteen new levels per category before the base game's first, 867 to 1350.

The base game's tables start at 1350 (its "pre-era" techs) and everyone begins at level 3. Our start is 867, so each of the
three tables gets NEW levels in front of the base game's, one about every 30 years. The new administrative levels are where
governing capacity grows (+10 each, on top of the base the all_nations modifier gives), so a realm's reach follows its
administration instead of being flat; the old pre-era levels' unlocks (units, ships, the first governments) are carried by
new level 0 so every start has them.

Putting levels in front moves every base-game level by NEW, so:
  * technology.txt: each group starts at a level suited to 867 (BASE_LEVEL),
  * the base game's own numeric tech checks (`adm_tech = 12` in missions, decisions, events, estate agendas ...) are rewritten by
    +NEW in generated copies (step_shift_checks),
  * the base game's defines that name a level, and its per-level costs, are adjusted (defines_patch),
  * localisation names are shifted along (the names are keyed by level).
Run from build.py; `python3 tools/techs.py` just regenerates the tech files."""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import EU4_GAME  # noqa: E402
from steps.layout import MOD  # noqa: E402
from steps.output import write_loc  # noqa: E402

NEW = 16
FIRST_YEAR, LAST_YEAR = 867, 1350
CATS = ("adm", "dip", "mil")
MARKER = f"# tech levels shifted by {NEW} (tools/techs.py)"
GOVERNING_CAPACITY_BASE = 30  # was 200; with +8 per new adm level it is 150 at the base game's first level
GOVERNING_CAPACITY_MODIFIER = -0.2  # every country's capacity is a fifth lower again

# each group's starting level at 867 (the base game gives nearly every group 3 at 1444; ours begins in 867, so it is a
# level of the new ladder: the caliphate and China ahead, the West and Africa behind)
BASE_LEVEL = {
    "western": 2, "eastern": 4, "ottoman": 4, "muslim": 4, "indian": 4, "east_african": 3, "central_african": 2,
    "chinese": 6, "nomad_group": 3, "sub_saharan": 2, "north_american": 1, "mesoamerican": 1, "south_american": 1,
    "andean": 1, "aboriginal_tech": 1, "polynesian_tech": 2, "high_american": 3,
}

# name, description, modifier lines, flags unlocked here
ADM = [
    ("Hereditary Custom", "Rule passes by blood and oath, and the court keeps no record beyond the ruler's memory.", [], []),
    ("Household Administration", "The royal household doubles as the government: stewards, chamberlains and seneschals.", ["governing_capacity = 8", "production_efficiency = 0.01"], []),
    ("Royal Estates", "Crown lands are surveyed and farmed for the court.", ["governing_capacity = 8", "development_cost_modifier = -0.02"], []),
    ("Missi Dominici", "Itinerant envoys carry the ruler's will into the counties.", ["governing_capacity = 8", "administrative_efficiency = 0.01"], []),
    ("Charters and Writs", "Grants and judgements are set down in sealed documents.", ["governing_capacity = 8", "production_efficiency = 0.01"], []),
    ("Counts and Margraves", "Trusted lords hold whole regions in the ruler's name.", ["governing_capacity = 8", "production_efficiency = 0.01"], []),
    ("Monastic Scribes", "Monks keep the realm's letters, accounts and laws.", ["governing_capacity = 8", "administrative_efficiency = 0.01"], ["temple = yes"]),
    ("Tithes and Tolls", "Regular dues replace the ruler's endless travelling.", ["governing_capacity = 8", "administrative_efficiency = 0.01"], []),
    ("Cathedral Chapters", "Bishops and canons administer the realm's spiritual and temporal estates.", ["governing_capacity = 8", "development_cost_modifier = -0.02"], []),
    ("Manorial Records", "Rolls of tenants and dues allow the lords to reckon what they own.", ["governing_capacity = 8", "administrative_efficiency = 0.01"], []),
    ("Royal Chancery", "A permanent office issues the ruler's letters and keeps copies.", ["governing_capacity = 8", "production_efficiency = 0.01"], []),
    ("Town Charters", "Boroughs are granted their own courts and markets.", ["governing_capacity = 8", "development_cost_modifier = -0.02"], []),
    ("Exchequer", "Revenue is counted at a fixed table and audited.", ["governing_capacity = 8", "administrative_efficiency = 0.01"], ["workshop = yes", "farm_estate = yes"]),
    ("Roman Law Revival", "The old codes are studied again, and judges learn to cite them.", ["governing_capacity = 8", "administrative_efficiency = 0.01"], []),
    ("University Jurists", "Trained lawyers fill the courts and the councils.", ["governing_capacity = 8", "production_efficiency = 0.01"], ["courthouse = yes"]),
    ("Bureaucratic Clerks", "Salaried clerks, not household servants, now run the offices of state.", ["governing_capacity = 8", "development_cost_modifier = -0.02"], []),
]
DIP = [
    ("Coastal Boats", "Open boats carry goods and men along the shore.", [], []),
    ("Fairs and Markets", "Seasonal fairs bring merchants and their coin together.", ["trade_efficiency = 0.01"], []),
    ("Heralds and Envoys", "Messengers with safe-conduct carry the ruler's word abroad.", ["trade_range = 10"], []),
    ("Clinker Hulls", "Overlapping planks make a stronger, seaworthier hull.", ["naval_morale = 0.05"], []),
    ("Royal Marriages", "Brides and dowries bind dynasties in peace.", ["trade_efficiency = 0.01"], []),
    ("Hanseatic Leagues", "Merchant towns league together for safe trade.", ["trade_efficiency = 0.01"], []),
    ("Treaties of Peace", "Truces are written, sworn and witnessed.", ["trade_range = 10", "range = 10"], []),
    ("Caravan Roads", "Roads, wells and inns keep the caravans moving.", ["trade_range = 10"], ["marketplace = yes"]),
    ("Lateen Sails", "Triangular sails let ships work against the wind.", ["naval_morale = 0.05"], []),
    ("Merchant Guilds", "Merchants organise to defend their privileges and bargains.", ["trade_efficiency = 0.01"], []),
    ("Consular Posts", "Resident agents look after their countrymen in foreign ports.", ["trade_efficiency = 0.01"], []),
    ("Letters of Credit", "Bills of exchange spare merchants from carrying coin.", ["trade_range = 10"], []),
    ("Dynastic Diplomacy", "Alliances are planned generations ahead through marriage.", ["trade_range = 10"], []),
    ("Harbour Works", "Quays, breakwaters and cranes serve the port towns.", ["trade_efficiency = 0.01"], ["dock = yes"]),
    ("Portolan Charts", "Coasts and harbours are drawn together in one chart.", ["naval_morale = 0.05"], []),
    ("Compass and Astrolabe", "Pilots keep their course out of sight of land.", ["range = 10"], []),
]
MIL = [
    ("Household Retinues", "The ruler's sworn companions form the core of every army.", [], []),
    ("Heavy Cavalry", "Mounted men in mail ride down the lightly armed.", ["land_morale = 0.05"], []),
    ("Castle Garrisons", "Strongholds are held by small permanent garrisons.", ["military_tactics = 0.05"], []),
    ("Stirrup and Lance", "Couched lances and firm saddles make the charge irresistible.", ["cavalry_shock = 0.1"], []),
    ("Levy Arrays", "Every free man is listed for service by his lord.", ["infantry_shock = 0.1"], []),
    ("Mounted Knighthood", "Landed knights serve for a fief and ride to war on their own horses.", ["cavalry_shock = 0.1", "cavalry_fire = 0.05"], []),
    ("Crossbow Companies", "Hired crossbowmen put the strongest armour at risk.", ["infantry_fire = 0.05"], []),
    ("Stone Keeps", "Square towers of stone replace timber palisades.", ["military_tactics = 0.05"], []),
    ("Mercenary Contracts", "Companies of professional soldiers are hired by the season.", ["land_morale = 0.05"], []),
    ("Chivalric Orders", "Military brotherhoods hold the frontier.", ["military_tactics = 0.05"], []),
    ("Siege Towers", "Engines and belfries are built to the walls' height.", ["maneuver_value = 0.05"], []),
    ("Pike Hedgehogs", "Packed pikemen hold off the heaviest charge.", ["infantry_shock = 0.1"], []),
    ("Longbow Archery", "Volleys from drilled archers thin the enemy ranks.", ["infantry_fire = 0.05"], []),
    ("Heraldic Standards", "Banners let captains rally and command their men.", ["supply_limit = 0.1"], []),
    ("Plate Armour", "Full harness of steel protects knight and man-at-arms.", ["land_morale = 0.05"], []),
    ("Trained Companies", "Paid and drilled companies stand ready all year.", ["military_tactics = 0.05"], []),
]
TABLE = {"adm": ADM, "dip": DIP, "mil": MIL}
assert all(len(t) == NEW for t in TABLE.values())

FLAG = re.compile(r"^\s*((?:enable = \w+)|(?:\w+ = yes))\s*(?:#.*)?$")
NUMERIC_CHECK = re.compile(r"\b((?:adm|dip|mil)_tech\s*[=<>]+\s*)(\d+)\b")


def _read(path):
    return open(path, "rb").read().decode("latin-1")


def _blocks(text):
    """[(start, end)] of each top-level `technology = { ... }` block."""
    out = []
    for m in re.finditer(r"(?m)^technology\s*=\s*\{", text):
        depth, i = 0, m.end() - 1
        while True:
            c = text[i]
            depth += c == "{"
            depth -= c == "}"
            i += 1
            if depth == 0:
                break
        out.append((m.start(), i))
    return out


# the pace of the early levels follows Extended Timeline's: a level every 20 to 55 years, quickest around 1000 and slowest from 1230
EARLY_YEARS = [867, 922, 967, 987, 1005, 1026, 1046, 1064, 1088, 1126, 1149, 1196, 1235, 1259, 1306, 1329]
assert len(EARLY_YEARS) == NEW


def level_year(i):
    return EARLY_YEARS[i]


def tech_file(cat):
    """The mod's table: the base game's header, the new levels, then the base game's levels untouched."""
    text = _read(os.path.join(EU4_GAME, "common", "technologies", cat + ".txt")).replace("\r\n", "\n")
    blocks = _blocks(text)
    carried = []  # the pre-era levels' unlocks (units, ships, the first governments) come with new level 0
    for a, b in blocks[:3]:
        for line in text[a:b].split("\n"):
            m = FLAG.match(line)
            if m and m.group(1) not in carried:
                carried.append(m.group(1))
    out = [text[:blocks[0][0]].rstrip("\n"), "",
           f"# Levels 0-{NEW - 1}: ours, one about every 30 years from {FIRST_YEAR}. The base game's levels follow (its level n is ours {NEW}+n).", ""]
    for i, (name, _desc, mods, flags) in enumerate(TABLE[cat]):
        out.append("technology = { # " + name)
        out.append(f"\t# Tech {i}")
        out.append(f"\tyear = {level_year(i)}")
        for line in mods + flags + (carried if i == 0 else []):
            out.append("\t" + line)
        out += ["}", ""]
    out.append(text[blocks[0][0]:].rstrip("\n"))
    return "\n".join(out) + "\n"


def groups_file():
    text = _read(os.path.join(EU4_GAME, "common", "technology.txt"))
    seen = set()

    def fix(m):
        name = m.group(1)
        seen.add(name)
        if name not in BASE_LEVEL:
            raise SystemExit(f"techs: no 867 start level for the technology group {name!r}")
        return re.sub(r"start_level = \d+", f"start_level = {BASE_LEVEL[name]}", m.group(0), count=1)

    text = re.sub(r"(?m)^\t(\w+) = \{[^\n]*\n\t\tstart_level = \d+", fix, text)
    return text


def tech_names():
    """Localisation for every level: ours, then the base game's shifted by NEW."""
    loc = _read(os.path.join(EU4_GAME, "localisation", "technology_l_english.yml"))
    pairs = []
    for cat in CATS:
        for i, (name, desc, _m, _f) in enumerate(TABLE[cat]):
            pairs += [(f"{cat}_tech_cs_{i}_name", name), (f"{cat}_tech_cs_{i}_desc", desc)]
    for m in re.finditer(r'(?m)^ (adm|dip|mil)_tech_cs_(\d+)_(name|desc):\d* "(.*)"\s*$', loc):
        pairs.append((f"{m.group(1)}_tech_cs_{int(m.group(2)) + NEW}_{m.group(3)}", m.group(4)))
    return pairs


def shift_checks(text):
    return NUMERIC_CHECK.sub(lambda m: m.group(1) + str(int(m.group(2)) + NEW), text)


def defines_patch(text):
    """The base game's defines that name a tech level move with the levels; per-level costs are spread over more levels."""
    text = et_defines_patch(text)
    def level(name, text):
        m = re.search(rf"(\b{name}\s*=\s*)(\d+)", text)
        assert m, name
        return text[:m.start()] + m.group(1) + str(int(m.group(2)) + NEW) + text[m.end():]

    for name in ("MIN_TECH_FOR_CIRCUMNAVIGATE", "REBEL_ARTILLERY_INCREASE_LEVEL_1_TECH", "REBEL_ARTILLERY_INCREASE_LEVEL_2_TECH",
                 "HORDE_RAZE_TECH_BASE_LEVEL", "DEVOTION_RAZE_TECH_BASE_LEVEL", "FORCE_COMPOSITION_CHANGE_TECH_LEVEL"):
        text = level(name, text)
    for name, old, new in (("LAND_TECH_MAINTENANCE_IMPACT", "0.02", "0.0133"), ("NAVAL_TECH_MAINTENANCE_IMPACT", "0.02", "0.0133"),
                           ("LAND_TECH_MERC_MAINTENANCE_IMPACT", "0.08", "0.0533"), ("REVOLT_TECH_IMPACT", "0.03", "0.02"),
                           ("REVOLT_TECH_MORALE", "0.01", "0.0067")):
        assert re.search(rf"\b{name}\s*=\s*{old}\b", text), name
        text = re.sub(rf"(\b{name}\s*=\s*){old}\b", lambda m: m.group(1) + new, text, count=1)
    return text


def governing_capacity_patch(text):
    text = static_patch(text)
    """The flat governing capacity every country has: low, so reach is earned through administration."""
    return re.sub(r"(?ms)^(base_values = \{.*?^\tgoverning_capacity\s*=\s*)200\b",
                  lambda m: m.group(1) + f"{GOVERNING_CAPACITY_BASE}\n\tgoverning_capacity_modifier = {GOVERNING_CAPACITY_MODIFIER}", text, count=1)


# Extended Timeline's base values for every country (the base game's in brackets in the comment): fewer missionaries and advisers,
# a narrower tolerance, a lower pace of prestige and tradition decay, and no free vassal income
BASE_VALUES = {"missionaries": (1, 0), "army_tradition_decay": ("0.05", "0.06"), "navy_tradition_decay": ("0.05", "0.06"),
               "prestige_decay": ("0.05", "0.06"), "tolerance_own": (3, 2), "tolerance_heathen": (-3, -5), "tolerance_heretic": (-2, -3),
               "global_missionary_strength": ("0.02", "0"), "advisor_pool": (3, 2), "colonist_placement_chance": ("0.1", "0.05"),
               "vassal_income": ("0.10", "0"), "num_accepted_cultures": (2, 1), "merc_maintenance_modifier": ("0.1", "0.6")}
CLIMATE_DEVELOPMENT_COST = {"tropical": ("0.05", "0.15"), "arid": ("0.1", "0.15")}  # dearer to develop, as in Extended Timeline


def static_patch(text):
    def base(m):
        block = m.group(0)
        for key, (old, new) in BASE_VALUES.items():
            block, n = re.subn(rf"(?m)^(\t{key}\s*=\s*){old}\b", lambda x: x.group(1) + str(new), block, count=1)
            assert n == 1, key
        return block

    text = re.sub(r"(?ms)^base_values = \{.*?^\}", base, text, count=1)
    for name, (old, new) in CLIMATE_DEVELOPMENT_COST.items():
        text, n = re.subn(rf"(?ms)^({name} = \{{.*?^\tlocal_development_cost\s*=\s*){old}\b", lambda x: x.group(1) + new, text, count=1)
        assert n == 1, name
    return text


# Extended Timeline's development limits and costs: vassalisation is not capped by development, and the AI's development cap
# is a high multiple; reforms cost more to start and less to chain, as the early tiers add many; fewer ages of professionalism each
ET_DEFINES = {"VASSALIZE_BASE_DEVELOPMENT_CAP": ("100", "1000"), "DEVELOPMENT_CAP_BASE": ("10", "500"), "DEVELOPMENT_CAP_MULT": ("2", "5"),
              "GOVERNMENT_REFORM_BASE_COST": ("100.0", "300.0"), "GOVERNMENT_REFORM_COST_INCREASE": ("40.0", "10.0"),
              "ARMY_PROFESSIONALISM_PER_AGE": ("0.2", "0.08")}


def et_defines_patch(text):
    for name, (old, new) in ET_DEFINES.items():
        text, n = re.subn(rf"(\b{name}\s*=\s*){old}\b", lambda x: x.group(1) + new, text, count=1)
        assert n == 1, name
    return text


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(text.encode("latin-1"))


SHIFT_DIRS = ("common", "events", "decisions", "missions")
SKIP_DIRS = ("common/technologies", "common/defines")


def vanilla_files_with_checks():
    for top in SHIFT_DIRS:
        for root, _dirs, files in os.walk(os.path.join(EU4_GAME, top)):
            rel_root = os.path.relpath(root, EU4_GAME).replace(os.sep, "/")
            if rel_root.startswith(SKIP_DIRS):
                continue
            for fn in files:
                if fn.endswith(".txt"):
                    rel = rel_root + "/" + fn
                    if NUMERIC_CHECK.search(_read(os.path.join(EU4_GAME, rel))):
                        yield rel


BOM = "\xef\xbb\xbf"


def _marked(text):
    return text.removeprefix(BOM).startswith(MARKER)


def step_shift_checks():
    """Every base-game file with numeric tech checks gets a copy with them +NEW. A copy another step made this build (the
    filtered events and decisions) is shifted in place; one already carrying our marker is left alone; one carrying an older
    marker, or no copy at all, starts again from the base game's file."""
    n = 0
    for rel in vanilla_files_with_checks():
        dest = os.path.join(MOD, rel)
        text = _read(dest) if os.path.exists(dest) else ""
        body = text.removeprefix(BOM)
        if body.startswith(MARKER):
            n += 1
            continue
        if not text or body.startswith("# tech levels shifted by"):
            text = _read(os.path.join(EU4_GAME, rel))
        bom = BOM if text.startswith(BOM) else ""
        _write(dest, bom + MARKER + "\n" + shift_checks(text.removeprefix(BOM)))
        n += 1
    return n


def step_techs():
    for cat in CATS:
        _write(os.path.join(MOD, "common", "technologies", cat + ".txt"), tech_file(cat))
    _write(os.path.join(MOD, "common", "technology.txt"), groups_file())
    write_loc(os.path.join(MOD, "localisation", "kar_technology_l_english.yml"), tech_names())
    n = step_shift_checks()
    print(f"  {NEW} new levels in each of {len(CATS)} tables; shifted the tech checks of {n} base-game files")
    return 0


if __name__ == "__main__":
    step_techs()
