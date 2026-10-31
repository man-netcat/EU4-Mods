#!/usr/bin/env python3
"""New government reforms for the early game, unlocked by the new technology levels (techs.py).

Each is one more choice in an existing reform tier of its government (the base game's tiers are only extended: the interface
has a fixed number of tier rows), most of them lifting governing capacity at a cost elsewhere. They are written to
common/government_reforms/zz_kar_government_reforms.txt and listed in the tiers by vanillapatch.py (governments file)."""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import EU4_GAME  # noqa: E402
from steps.layout import MOD  # noqa: E402
from steps.output import write_loc, write_out  # noqa: E402

# government, tier, key, icon, name, description, modifiers, administrative technology level (techs.py's numbering) that unlocks it
REFORMS = [
    ("monarchy", "feudalism_vs_autocracy", "kar_household_court_reform", "crown", "Household Government",
     "The court and the government are one household: stewards, marshals and chamberlains rule in the king's name.",
     ["governing_capacity = 20", "advisor_cost = -0.1", "stability_cost_modifier = -0.1"], 1),
    ("monarchy", "feudalism_vs_autocracy", "kar_oath_bound_reform", "nobleman", "Oath-Bound Realm",
     "Every lord holds by oath, and the oath is renewed at each new reign.",
     ["governing_capacity = 20", "vassal_income = 0.15", "land_forcelimit_modifier = 0.05"], 2),
    ("monarchy", "feudalism_vs_autocracy", "kar_missi_reform", "king", "Missi Dominici",
     "Pairs of envoys, one lay and one clerical, ride the counties to hear complaints and enforce the king's will.",
     ["governing_capacity = 30", "vassal_income = -0.1", "legitimacy = 0.5"], 3),
    ("monarchy", "hereditary_vs_nobility", "kar_palatine_counties_reform", "nobleman", "Palatine Counties",
     "Border counties are held by powerful counts with the rights of the crown within their lands.",
     ["governing_capacity = 30", "nobles_influence_modifier = 0.1", "core_creation = -0.1"], 5),
    ("monarchy", "hereditary_vs_nobility", "kar_ministeriales_reform", "judge", "Ministeriales",
     "Unfree household servants are raised to administer the royal lands, and owe everything to the crown.",
     ["governing_capacity = 25", "global_tax_modifier = 0.05", "nobles_influence_modifier = -0.05"], 8),
    ("monarchy", "bureaucracy", "kar_cathedral_chapters_reform", "pope", "Cathedral Chapters",
     "Bishops and their canons are the realm's clerks, judges and tax-reckoners.",
     ["governing_capacity = 30", "church_influence_modifier = 0.1", "tolerance_own = 1"], 8),
    ("monarchy", "bureaucracy", "kar_royal_chancery_reform", "paper_with_seal", "Royal Chancery",
     "A standing office issues the king's writs and keeps copies of every grant.",
     ["governing_capacity_modifier = 0.1", "advisor_cost = -0.1"], 10),
    ("monarchy", "bureaucracy", "kar_borough_charters_reform", "merchant", "Borough Charters",
     "Towns hold their own courts and councils and answer to the crown for the dues they owe.",
     ["governing_capacity = 20", "burghers_influence_modifier = 0.1", "production_efficiency = 0.05"], 11),
    ("monarchy", "bureaucracy", "kar_exchequer_reform", "paper_with_seal_3", "The Exchequer",
     "Sheriffs account twice a year at a table of squares; every debt is written down.",
     ["governing_capacity = 25", "global_tax_modifier = 0.1", "stability_cost_modifier = 0.1"], 12),
    ("monarchy", "economical_matters", "kar_manorial_economy_reform", "peasants", "Manorial Economy",
     "The land is worked by tenants of the manor, and the manor feeds the realm.",
     ["governing_capacity = 20", "global_tax_modifier = 0.1", "nobles_influence_modifier = 0.05"], 4),
    ("monarchy", "economical_matters", "kar_market_rights_reform", "trading_city", "Market Rights",
     "The crown sells the right to hold markets and takes its share of every sale.",
     ["governing_capacity = 20", "trade_efficiency = 0.1", "burghers_influence_modifier = 0.05"], 7),
    ("monarchy", "state_and_religion", "kar_royal_church_reform", "religious_leader", "Royal Church",
     "Bishops are named by the king and serve him as lords and counsellors.",
     ["governing_capacity = 25", "tolerance_own = 2", "legitimacy = 0.5"], 6),
    ("monarchy", "military_doctrines", "kar_retinue_host_reform", "soldiers_2", "Retinue Host",
     "Every lord keeps a retinue, and the king's host is the sum of them.",
     ["governing_capacity = 15", "land_forcelimit_modifier = 0.1", "land_maintenance_modifier = -0.05"], 3),
    ("monarchy", "military_doctrines", "kar_castle_guard_reform", "castle", "Castle Guard",
     "Knights serve for a term in the castles that hold the land.",
     ["governing_capacity = 15", "defensiveness = 0.1"], 5),
    ("republic", "oligarchy_merchant_class_noble_elite", "kar_guild_assembly_reform", "assembly_hall", "Guild Assembly",
     "The guilds sit as the city's council, each for its own trade.",
     ["governing_capacity = 20", "production_efficiency = 0.05", "burghers_influence_modifier = 0.1"], 3),
    ("republic", "oligarchy_merchant_class_noble_elite", "kar_patrician_council_reform", "politician", "Patrician Council",
     "A few old families hold every office, and keep the city's trade in their hands.",
     ["governing_capacity = 30", "republican_tradition = 0.5", "trade_efficiency = 0.05"], 5),
    ("republic", "republican_virtues", "kar_civic_militia_reform", "soldiers_2", "Civic Militia",
     "Every citizen drills with his ward, and the wards march together.",
     ["governing_capacity = 15", "land_forcelimit_modifier = 0.1"], 4),
    ("republic", "economical_matters_republic", "kar_staple_rights_reform", "merchant", "Staple Rights",
     "Foreign merchants must offer their goods in the city's market before they sail on.",
     ["governing_capacity = 20", "trade_efficiency = 0.1", "global_tax_modifier = 0.05"], 6),
    ("theocracy", "theocratic_leadership", "kar_abbot_lord_reform", "pope", "Abbot-Lord",
     "The head of the order is lord of its lands as well as its souls.",
     ["governing_capacity = 25", "tolerance_own = 2"], 3),
    ("theocracy", "clergy_in_administration", "kar_clerical_scribes_reform", "paper_with_seal", "Clerical Scribes",
     "The clergy keep the accounts, the rolls and the letters of the order.",
     ["governing_capacity = 30", "advisor_cost = -0.1", "stability_cost_modifier = -0.1"], 6),
    ("theocracy", "economical_matters", "kar_monastic_estates_reform", "peasants", "Monastic Estates",
     "Lay brothers and tenants work the order's farms, and the order's farms feed it.",
     ["governing_capacity = 20", "global_tax_modifier = 0.1"], 4),
    ("tribal", "tribal_administration", "kar_clan_moots_reform", "tribal_council", "Clan Moots",
     "Free men meet at the assembly to judge disputes and choose war.",
     ["governing_capacity = 20", "stability_cost_modifier = -0.1"], 2),
    ("tribal", "tribal_administration", "kar_war_band_reform", "chieftain", "War Band",
     "The chief's sworn companions ride with him and are fed at his table.",
     ["governing_capacity = 15", "land_forcelimit_modifier = 0.1"], 3),
    ("tribal", "tribal_cultural_values", "kar_oath_circles_reform", "shaman", "Oath Circles",
     "Kin swear oaths of blood and of the land, and the oaths bind more tightly than law.",
     ["governing_capacity = 15", "tolerance_own = 1"], 4),
]


def modifier_names():
    """Every modifier key the base game's reforms use: ours must come from this set."""
    names = set()
    d = os.path.join(EU4_GAME, "common", "government_reforms")
    for fn in os.listdir(d):
        text = open(os.path.join(d, fn), "rb").read().decode("latin-1")
        for block in re.findall(r"(?ms)^\tmodifiers = \{(.*?)^\t\}", text):
            names.update(re.findall(r"(?m)^\s*(\w+)\s*=", block))
    return names


def tiers():
    """{government: {tier: [reform keys]}} for the governments file."""
    out = {}
    for gov, tier, key, *_ in REFORMS:
        out.setdefault(gov, {}).setdefault(tier, []).append(key)
    return out


def add_to_tiers(text):
    """The governments file with our reforms listed at the top of their tiers."""
    for gov, by_tier in tiers().items():
        m = re.search(rf"(?ms)^{gov} = \{{.*?^\}}", text)
        assert m, gov
        block = m.group(0)
        for tier, keys in by_tier.items():
            pat = re.compile(rf"(\t\t{tier} = \{{\n\t\t\treforms = \{{\n)")
            assert pat.search(block), (gov, tier)
            block = pat.sub(lambda x: x.group(1) + "".join(f"\t\t\t\t{k}\n" for k in keys), block, count=1)
        text = text[:m.start()] + block + text[m.end():]
    return add_early_tiers(text)


def step_reforms():
    known = modifier_names()
    lines = ["# Written by tools/reforms.py. Do not edit.", ""]
    pairs = []
    for gov, tier, key, icon, name, desc, mods, tech in REFORMS:
        for mod in mods:
            assert mod.split("=")[0].strip() in known, (key, mod)
        lines += [f"{key} = {{", f'\ticon = "{icon}"', "\ttrigger = {", f"\t\tadm_tech = {tech}", "\t}", "\tmodifiers = {"]
        lines += ["\t\t" + m for m in mods]
        lines += ["\t}", "\tai = {", "\t\tfactor = 0.5", "\t}", "}", ""]
        pairs += [(key, name), (key + "_desc", desc)]
    elines, epairs = early_text()
    lines.append(elines)
    pairs += epairs
    write_out(os.path.join(MOD, "common", "government_reforms", "zz_kar_government_reforms.txt"), "\n".join(lines))
    write_loc(os.path.join(MOD, "localisation", "kar_government_reforms_l_english.yml"), pairs)
    print(f"  {len(REFORMS) + len(early_reforms())} new government reforms")
    return 0




# ---------------------------------------------------------------------------------------------------------------------------------
# Early reform tiers, after Extended Timeline's design: a run of extra tiers right after each government's first, two reforms in
# each, every one gated by the administrative technology (the new early levels) instead of an institution. The content is ours.

# per tier: (theme, title, a-side modifiers, b-side modifiers, description of the tier's first / second reform)
EARLY_THEMES = [
    ("household", "Kin and Household", ["governing_capacity = 10", "num_accepted_cultures = 1"], ["culture_conversion_cost = -0.1", "global_unrest = -0.5"],
     "keeps the realm together through the ruler's own kin and household", "binds the subject peoples to the ruler's household and customs"),
    ("custom", "Law and Custom", ["governing_capacity = 10", "stability_cost_modifier = -0.05"], ["global_unrest = -1", "tolerance_own = 1"],
     "sets down the customs of the realm so that officers can apply them alike everywhere", "keeps the peace by custom, oath and the fixed price of every wrong"),
    ("office", "Court and Office", ["governing_capacity = 10", "advisor_cost = -0.05"], ["diplomatic_reputation = 1", "improve_relation_modifier = 0.1"],
     "gives each task of government to a named officer of the court", "lets the ruler's court travel the realm and receive foreign envoys"),
    ("levy", "Land and Levy", ["governing_capacity = 10", "land_forcelimit_modifier = 0.05"], ["land_morale = 0.05", "defensiveness = 0.1"],
     "ties every holding of land to a fixed share of the army", "keeps the land's defenders trained and their strongholds manned"),
    ("faith", "Faith and Rule", ["governing_capacity = 10", "tolerance_own = 1"], ["culture_conversion_cost = -0.1", "tolerance_heretic = 1"],
     "lets the clergy carry the ruler's orders to every parish", "puts the faith's holy days and rites at the centre of public life"),
    ("trade", "Town and Trade", ["governing_capacity = 10", "trade_efficiency = 0.05"], ["global_tax_modifier = 0.05", "build_cost = -0.05"],
     "grants towns their own councils in return for steady dues", "licenses markets and mints so that coin moves through the realm"),
    ("records", "Scribes and Records", ["governing_capacity = 10", "development_cost = -0.05"], ["production_efficiency = 0.05", "core_creation = -0.1"],
     "keeps rolls of every holding, tenant and due", "surveys the realm so that new lands are quickly put in order"),
    ("council", "Crown and Council", ["governing_capacity = 15", "stability_cost_modifier = -0.05"], ["global_manpower_modifier = 0.1", "land_forcelimit_modifier = 0.05"],
     "gathers the realm's great men into a council that shares the ruler's burdens", "calls the whole realm to arms through its standing council"),
]
EARLY_NAMES = {
    "monarchy": [("Royal Household", "Kindred Council"), ("Law of the Land", "Royal Peace"), ("Great Officers", "Itinerant Court"),
                 ("Fiefs and Service", "Free Levy"), ("Bishop-Counsellors", "Royal Chapel"), ("Royal Boroughs", "Mint and Market"),
                 ("Charter Rolls", "Domesday Survey"), ("Great Council", "Standing Council")],
    "republic": [("City Compact", "Sworn Commune"), ("Statutes of the City", "Civic Peace"), ("Elected Magistrates", "Rotating Consuls"),
                 ("Citizen Levy", "Hired Condottieri"), ("Parish Councils", "Civic Church"), ("Guild Charters", "Free Port"),
                 ("Notaries and Archives", "City Ledgers"), ("Council of Elders", "Senate of the Realm")],
    "theocracy": [("Rule of the Order", "Chapter House"), ("Canon Law", "Truce of God"), ("Prior and Bursar", "Visiting Abbots"),
                  ("Lay Brothers", "Warrior Brethren"), ("Daily Office", "Pilgrim Hospices"), ("Monastic Markets", "Tithe Barns"),
                  ("Scriptorium", "Cartulary"), ("General Chapter", "Council of Bishops")],
    "tribal": [("Kin Bonds", "Hearth Oaths"), ("Customary Law", "Blood Price"), ("The Chief's Table", "Gift Giving"),
               ("Warband Levy", "Hill Forts"), ("Sacred Groves", "Bardic Order"), ("Trading Halls", "Market Peace"),
               ("Rune Keepers", "Memory Keepers"), ("Great Moot", "Council of Chiefs")],
}
EARLY_ICONS = {"monarchy": ["king", "judge", "nobleman", "soldiers_2", "religious_leader", "merchant", "paper_with_seal", "parliament_hall"],
               "republic": ["politician", "judge", "assembly_hall", "soldiers_2", "religious_leader", "trading_city", "paper_with_seal", "assembly_hall"],
               "theocracy": ["pope", "judge", "religious_leader", "soldiers_2", "pope", "peasants", "paper_with_seal", "religious_leader"],
               "tribal": ["chieftain", "tribal_council", "chieftain", "soldiers_2", "shaman", "trading_city", "shaman", "tribal_council"]}


def early_tier_key(gov, n):
    return f"kar_early_{gov}_tier_{n}"


def early_reforms():
    """[(gov, tier key, reform key, icon, name, description, modifiers, level)] for every early reform."""
    out = []
    for gov, names in EARLY_NAMES.items():
        for i, ((na, nb), (_slug, title, ma, mb, da, db)) in enumerate(zip(names, EARLY_THEMES), start=1):
            level = 2 * i - 1
            tier = early_tier_key(gov, i)
            for side, name, mods, d in (("a", na, ma, da), ("b", nb, mb, db)):
                key = f"kar_early_{gov}_{i}{side}_reform"
                out.append((gov, tier, key, EARLY_ICONS[gov][i - 1], name, f"The {name.lower()} {d}.".replace("The the", "The"), mods, level))
    return out


def add_early_tiers(text):
    """Each government's early tiers are listed right after its first tier."""
    for gov in EARLY_NAMES:
        m = re.search(rf"(?ms)^{gov} = \{{.*?^\}}", text)
        assert m, gov
        block = m.group(0)
        rl = re.search(r"\treform_levels = \{\n", block)
        first = re.compile(r"\t\t\w+ = \{\n\t\t\treforms = \{\n.*?\n\t\t\t\}\n\t\t\}\n", re.S).search(block, rl.end())
        assert first and first.start() == rl.end(), gov
        tiers_text = "".join(f"\t\t{early_tier_key(gov, i)} = {{\n\t\t\treforms = {{\n\t\t\t\tkar_early_{gov}_{i}a_reform\n\t\t\t\tkar_early_{gov}_{i}b_reform\n\t\t\t}}\n\t\t}}\n"
                             for i in range(1, len(EARLY_THEMES) + 1))
        block = block[:first.end()] + tiers_text + block[first.end():]
        text = text[:m.start()] + block + text[m.end():]
    return text


def early_text():
    known = modifier_names()
    lines, pairs = [], []
    for gov, tier, key, icon, name, desc, mods, level in early_reforms():
        for mod in mods:
            assert mod.split("=")[0].strip() in known, (key, mod)
        lines += [f"{key} = {{", f'\ticon = "{icon}"', "\ttrigger = {", f"\t\tadm_tech = {level}", "\t}", "\tmodifiers = {"]
        lines += ["\t\t" + m for m in mods]
        lines += ["\t}", "\tai = {", "\t\tfactor = 0.5", "\t}", "}", ""]
        pairs += [(key, name), (key + "_desc", desc)]
    for gov in EARLY_NAMES:
        for i, theme in enumerate(EARLY_THEMES, start=1):
            pairs.append((early_tier_key(gov, i), theme[1]))
    return "\n".join(lines), pairs


if __name__ == "__main__":
    step_reforms()
