#!/usr/bin/env python3
"""The ages between 867 and the Age of Discovery.

The base game's first age is Discovery, which our start date long precedes. Age of Traditions follows EU5 (starting 1337);
the ones before it are our own invention, one per stretch of the Carolingian-to-late-medieval world. Each age gets four
objectives and three abilities written from the table below; common/ages/00_a_kar_early_ages.txt sorts before the base
game's file so the ages run in order. Discovery itself is patched in vanillapatch.py (it starts in 1437, EU5's date, so Traditions runs 1337-1437)."""

import os
from steps.layout import GAME, MOD
from steps.output import write_loc, write_out

# slug, start, name, short name, description, objectives [(slug, name, description, trigger)],
# abilities [(slug, name, modifiers)]
AGES = [
    ("successors", 867, "Age of the Successors", "Successors",
     "Charlemagne's empire is broken between his heirs and the great lords of the West rise in his shadow.\\nSecure your realm, bind your vassals and hold what your fathers won.",
     [("kar_obj_hold_court", "Hold Court", "Reach 40 prestige.", "prestige = 40"),
      ("kar_obj_loyal_realm", "A Loyal Realm", "Have at least 3 vassals.", "vassal = 3"),
      ("kar_obj_sworn_allies", "Sworn Allies", "Have at least 2 allies.", "num_of_allies = 2"),
      ("kar_obj_growing_domain", "A Growing Domain", "Reach a total of at least 60 development in your nation.", "total_development = 60")],
     [("kar_ab_oaths_of_fealty", "Oaths of Fealty", "reduced_liberty_desire = 10\n\t\t\t\tdiplomatic_reputation = 1"),
      ("kar_ab_levied_hosts", "Levied Hosts", "land_forcelimit_modifier = 0.15"),
      ("kar_ab_royal_demesne", "Royal Demesne", "global_tax_modifier = 0.1")]),
    ("raiders", 960, "Age of Raiders", "Raiders",
     "From the north, the east and the south come longships, horsemen and corsairs.\\nThe realms that learn to defend their shores and fortify their towns will outlast the storm.",
     [("kar_obj_walled_realm", "A Walled Realm", "Reach a total of at least 80 development in your nation.", "total_development = 80"),
      ("kar_obj_standing_host", "A Standing Host", "Have an army of at least 15 regiments.", "army_size = 15"),
      ("kar_obj_tribute_of_kings", "Tribute of Kings", "Have at least 2 subjects.", "vassal = 2"),
      ("kar_obj_steady_throne", "A Steady Throne", "Have at least +2 stability.", "stability = 2")],
     [("kar_ab_shore_watch", "Shore Watch", "naval_forcelimit_modifier = 0.2\n\t\t\t\tdefensiveness = 0.1"),
      ("kar_ab_burgh_walls", "Burgh Walls", "fort_maintenance_modifier = -0.2\n\t\t\t\tglobal_unrest = -1"),
      ("kar_ab_mounted_retinues", "Mounted Retinues", "cavalry_power = 0.1\n\t\t\t\tcav_to_inf_ratio = 0.1")]),
    ("feudalism", 1055, "Age of Feudalism", "Feudalism",
     "The land is parcelled into fiefs, castles crown every hill and the knight becomes the master of the field.\\nLords bargain with kings, and the Church and the crown grow ever closer.",
     [("kar_obj_castellans", "Castellans", "Have at least 5 vassals.", "vassal = 5"),
      ("kar_obj_great_domain", "A Great Domain", "Reach a total of at least 120 development in your nation.", "total_development = 120"),
      ("kar_obj_knights_host", "The Knights' Host", "Have an army of at least 25 regiments.", "army_size = 25"),
      ("kar_obj_pious_ruler", "A Pious Ruler", "Reach 100 legitimacy.", "legitimacy = 100")],
     [("kar_ab_knights_fees", "Knights' Fees", "land_forcelimit_modifier = 0.2\n\t\t\t\tcavalry_power = 0.1"),
      ("kar_ab_feudal_dues", "Feudal Dues", "vassal_income = 0.25\n\t\t\t\tglobal_tax_modifier = 0.1"),
      ("kar_ab_peace_of_god", "Peace of God", "stability_cost_modifier = -0.1\n\t\t\t\tglobal_unrest = -1")]),
    ("crusades", 1150, "Age of Crusades", "Crusades",
     "Pope and preacher call the faithful to war, and armies march to the ends of the known world.\\nFaith, plunder and glory drive the realms of the age.",
     [("kar_obj_holy_war", "Holy War", "Reach 150 prestige.", "prestige = 150"),
      ("kar_obj_rich_treasury", "A Rich Treasury", "Have at least 500 ducats in the treasury.", "treasury = 500"),
      ("kar_obj_realm_of_cities", "A Realm of Cities", "Own at least 25 provinces.", "num_of_cities = 25"),
      ("kar_obj_marriage_alliances", "Marriage Alliances", "Have at least 2 royal marriages.", "num_of_royal_marriages = 2")],
     [("kar_ab_crusader_zeal", "Crusader Zeal", "land_morale = 0.1\n\t\t\t\ttolerance_own = 1"),
      ("kar_ab_pilgrim_roads", "Pilgrim Roads", "trade_efficiency = 0.1\n\t\t\t\tglobal_trade_power = 0.1"),
      ("kar_ab_military_orders", "Military Orders", "discipline = 0.05\n\t\t\t\tland_maintenance_modifier = -0.1")]),
    ("estates", 1245, "Age of Estates", "Estates",
     "Charters are sealed, parliaments gather and towns win their liberties.\\nKings learn that the nobles, the clergy and the burghers must be heard.",
     [("kar_obj_charter_towns", "Chartered Towns", "Reach a total of at least 180 development in your nation.", "total_development = 180"),
      ("kar_obj_royal_council", "A Royal Council", "Have at least +1 stability.", "stability = 1"),
      ("kar_obj_grand_alliance", "A Grand Alliance", "Have at least 3 allies.", "num_of_allies = 3"),
      ("kar_obj_feared_crown", "A Feared Crown", "Reach 100 prestige.", "prestige = 100")],
     [("kar_ab_guild_charters", "Guild Charters", "production_efficiency = 0.1\n\t\t\t\tbuild_cost = -0.1"),
      ("kar_ab_common_law", "Common Law", "legitimacy = 0.5\n\t\t\t\tglobal_unrest = -1"),
      ("kar_ab_scutage", "Scutage", "global_manpower_modifier = 0.15\n\t\t\t\tadvisor_cost = -0.1")]),
    ("traditions", 1337, "Age of Traditions", "Traditions",
     "The old order is at its height, and its first cracks begin to show.\\nPlague, schism and long wars test the realms as they hold fast to custom.",
     [("kar_obj_ancient_customs", "Ancient Customs", "Reach a total of at least 250 development in your nation.", "total_development = 250"),
      ("kar_obj_great_host", "A Great Host", "Have an army of at least 40 regiments.", "army_size = 40"),
      ("kar_obj_loyal_lords", "Loyal Lords", "Have at least 5 subjects.", "vassal = 5"),
      ("kar_obj_deep_coffers", "Deep Coffers", "Have at least 1000 ducats in the treasury.", "treasury = 1000")],
     [("kar_ab_custom_and_law", "Custom and Law", "stability_cost_modifier = -0.1\n\t\t\t\tlegitimacy = 0.5"),
      ("kar_ab_long_bows", "Hardened Veterans", "infantry_power = 0.1\n\t\t\t\tland_forcelimit_modifier = 0.1"),
      ("kar_ab_burghers_purse", "The Burghers' Purse", "global_trade_power = 0.1\n\t\t\t\tglobal_tax_modifier = 0.1")]),
]


# the base game's ages window has one block per age (named after the age) and finds sprites by key; a current age with no block
# crashes the game on opening the window, so each of ours gets a copy of Discovery's block and sprites that reuse the base game's art
OBJECTIVE_ART = ["obj_100_development", "obj_large_forcelimit", "obj_many_vassals", "obj_cultures_accepted", "obj_universities",
                 "obj_disc_army", "obj_huge_capital", "obj_great_general", "obj_large_subject", "obj_parliament"]
ABILITY_ART = ["ab_allow_feudal_de_jure_law", "ab_claim_duration", "ab_justified_wars", "ab_free_war_taxes", "ab_cavalry_armies",
               "ab_mercenary_discipline", "ab_siege_blockades", "ab_culture_cost", "ab_autonomy", "ab_adm_efficiency"]


def ages_window_and_sprites(slugs, objective_keys, ability_keys):
    gui = open(os.path.join(GAME, "interface", "ages_view.gui"), "rb").read().decode("latin-1")
    nl = "\r\n" if "\r\n" in gui else "\n"
    start = gui.index("\t\tWindowType = {" + nl + '\t\t\tname = "age_of_discovery"')
    end = gui.index("\t\tWindowType = {" + nl + '\t\t\tname = "age_of_reformation"')
    block = gui[start:end]
    copies = "".join(block.replace('name = "age_of_discovery"', f'name = "age_of_{slug}"', 1) for slug in slugs)
    gui = gui[:start] + copies + gui[start:]
    sprite = lambda name, tex: f'\tspriteType = {{\n\t\tname = "GFX_{name}"\n\t\ttexturefile = "gfx/interface/ages/{tex}.dds"\n\t}}\n'
    out = ["spriteTypes = {", ""]
    out += [sprite(f"age_of_{slug}", "age_of_discovery") for slug in slugs]
    out += [sprite(k, OBJECTIVE_ART[i % len(OBJECTIVE_ART)]) for i, k in enumerate(objective_keys)]
    out += [sprite(k, ABILITY_ART[i % len(ABILITY_ART)]) for i, k in enumerate(ability_keys)]
    out.append("}")
    return gui, "\n".join(out) + "\n"


def step_ages() -> None:
    blocks = ["# Written by tools/steps/ages.py. Do not edit.", ""]
    pairs = []
    for slug, start, name, short, desc, objectives, abilities in AGES:
        age = "age_of_" + slug
        blocks += [f"{age} = {{", f"\tstart = {start}", "", "\tcan_start = {", f"\t\tis_year = {start}", "\t}", "", "\tobjectives = {"]
        for key, oname, odesc, trigger in objectives:
            blocks += [f"\t\t{key} = {{", f"\t\t\t{trigger}", "\t\t}"]
            pairs += [(key, oname), (key + "_desc", odesc)]
        blocks += ["\t}", "", "\tabilities = {"]
        for key, aname, mods in abilities:
            blocks += [f"\t\t{key} = {{", "\t\t\tmodifier = {", f"\t\t\t\t{mods}", "\t\t\t\tnum_of_age_rewards = 1", "\t\t\t}",
                       "\t\t\tai_will_do = {", "\t\t\t\tfactor = 10", "\t\t\t}", "\t\t}"]
            pairs.append((key, aname))
        blocks += ["\t}", "}", ""]
        pairs += [(age, name), (age + "_short", short), (age + "_desc", desc)]
    write_out(os.path.join(MOD, "common", "ages", "00_a_kar_early_ages.txt"), "\n".join(blocks))
    objs = [k for _s, _y, _n, _sh, _d, o, _a in AGES for k, *_ in o]
    abs_ = [k for _s, _y, _n, _sh, _d, _o, a in AGES for k, *_ in a]
    gui, gfx = ages_window_and_sprites([a[0] for a in AGES], objs, abs_)
    os.makedirs(os.path.join(MOD, "interface"), exist_ok=True)
    open(os.path.join(MOD, "interface", "ages_view.gui"), "wb").write(gui.encode("latin-1"))
    write_out(os.path.join(MOD, "interface", "kar_ages.gfx"), gfx)
    write_loc(os.path.join(MOD, "localisation", "kar_ages_l_english.yml"), pairs)
    print(f"wrote {len(AGES)} early ages")
