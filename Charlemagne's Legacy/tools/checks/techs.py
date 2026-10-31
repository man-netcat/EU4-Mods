#!/usr/bin/env python3
"""The early technology levels, the base game's level checks moved with them, governing capacity, and the new reforms."""

import os
import re

from checks.context import BY_TAG, GAME, MOD
from checks.report import note

import reforms
import techs


def _read(path):
    return open(path, "rb").read().decode("latin-1")


def _mod(rel):
    return _read(os.path.join(MOD, rel))


def _vanilla(rel):
    return _read(os.path.join(GAME, rel))


def tech_tables_carry_the_early_levels() -> None:
    print("\n== early technology levels ==")
    bad = []
    for cat in techs.CATS:
        mod_text = _mod(f"common/technologies/{cat}.txt").replace("\r\n", "\n")
        van_text = _vanilla(f"common/technologies/{cat}.txt").replace("\r\n", "\n")
        mb, vb = techs._blocks(mod_text), techs._blocks(van_text)
        if len(mb) != len(vb) + techs.NEW:
            bad.append(f"{cat}: {len(mb)} levels, want {len(vb)} + {techs.NEW}")
            continue
        years = [int(re.search(r"year = (\d+)", mod_text[a:b]).group(1)) for a, b in mb]
        if years != sorted(set(years)) or years[0] != techs.FIRST_YEAR:
            bad.append(f"{cat}: years not rising from {techs.FIRST_YEAR}")
        if [mod_text[a:b] for a, b in mb[techs.NEW:]] != [van_text[a:b] for a, b in vb]:
            bad.append(f"{cat}: the base game's levels were changed")
        level0 = mod_text[mb[0][0]:mb[0][1]]
        for a, b in vb[:3]:
            for line in van_text[a:b].split("\n"):
                m = techs.FLAG.match(line)
                if m and m.group(1) not in level0:
                    bad.append(f"{cat}: level 0 lacks the pre-era unlock {m.group(1)}")
        caps = sum(int(x) for x in re.findall(r"governing_capacity = (\d+)", "".join(mod_text[a:b] for a, b in mb[:techs.NEW])))
        if cat == "adm" and caps != 120:
            bad.append(f"adm: the new levels give {caps} governing capacity, want 120")
    note(not bad, f"each table is {techs.NEW} new levels (from {techs.FIRST_YEAR}) before the base game's, whose unlocks level 0 carries" + (": " + "; ".join(bad) if bad else ""))

    groups = _mod("common/technology.txt")
    got = dict(re.findall(r"(?m)^\t(\w+) = \{[^\n]*\n\t\tstart_level = (\d+)", groups))
    wrong = [g for g, lv in techs.BASE_LEVEL.items() if got.get(g) != str(lv)]
    note(not wrong and all(0 <= v < techs.NEW for v in techs.BASE_LEVEL.values()), "every technology group starts at its 867 level" + (": " + ", ".join(wrong) if wrong else ""))

    loc = _mod("localisation/kar_technology_l_english.yml")
    lacking = [f"{c}_{i}" for c in techs.CATS for i in range(techs.NEW) if f" {c}_tech_cs_{i}_name:" not in loc]
    shifted = all(f" {c}_tech_cs_{techs.NEW + 3}_name:" in loc for c in techs.CATS)
    note(not lacking and shifted, "every new level has a name and the base game's names moved up with their levels" + (": " + ", ".join(lacking[:5]) if lacking else ""))


def base_game_level_checks_moved() -> None:
    print("\n== the base game's tech level checks move with the levels ==")
    bad, n = [], 0
    for rel in techs.vanilla_files_with_checks():
        n += 1
        dest = os.path.join(MOD, rel)
        if not os.path.exists(dest):
            bad.append(f"{rel} (no copy)")
            continue
        text = _read(dest)
        if not techs._marked(text):
            bad.append(f"{rel} (not shifted)")
            continue
        got = [int(m.group(2)) for m in techs.NUMERIC_CHECK.finditer(text)]
        base = [int(m.group(2)) + techs.NEW for m in techs.NUMERIC_CHECK.finditer(_vanilla(rel))]
        it = iter(base)  # events and decisions are filtered copies: their checks are a subsequence of the base game's
        if not all(any(g == b for b in it) for g in got):
            bad.append(f"{rel} (checks differ from the base game's + {techs.NEW})")
    note(not bad, f"{n} base-game files carry their tech level checks +{techs.NEW}" + (": " + ", ".join(bad[:6]) if bad else ""))

    d = _mod("common/defines.lua")
    off = []
    for name in ("MIN_TECH_FOR_CIRCUMNAVIGATE", "REBEL_ARTILLERY_INCREASE_LEVEL_1_TECH", "REBEL_ARTILLERY_INCREASE_LEVEL_2_TECH",
                 "HORDE_RAZE_TECH_BASE_LEVEL", "DEVOTION_RAZE_TECH_BASE_LEVEL", "FORCE_COMPOSITION_CHANGE_TECH_LEVEL"):
        a = int(re.search(rf"\b{name}\s*=\s*(\d+)", _vanilla("common/defines.lua")).group(1))
        b = int(re.search(rf"\b{name}\s*=\s*(\d+)", d).group(1))
        if b != a + techs.NEW:
            off.append(name)
    note(not off, "the defines that name a tech level moved with the levels" + (": " + ", ".join(off) if off else ""))


def governing_capacity_is_earned() -> None:
    print("\n== governing capacity ==")
    base = int(re.search(r"(?ms)^base_values = \{.*?^\tgoverning_capacity = (\d+)", _mod("common/static_modifiers/00_static_modifiers.txt")).group(1))
    note(base == techs.GOVERNING_CAPACITY_BASE, f"every country's flat governing capacity is {techs.GOVERNING_CAPACITY_BASE} (the base game's is 200)")
    ranks = {m.group(1): int(m.group(2)) for m in re.finditer(r"(?ms)^(\d) = \{.*?governing_capacity = (\d+)", _mod("common/government_ranks/zz_kar_government_ranks.txt"))}
    note(ranks == {"2": 20, "3": 40, "4": 60, "5": 100}, f"government ranks give 20/40/60/100 governing capacity (the base game's: 200/400/600/1000): {ranks}")
    note(f"governing_capacity_modifier = {techs.GOVERNING_CAPACITY_MODIFIER}" in _mod("common/static_modifiers/00_static_modifiers.txt"), "every country's governing capacity is cut by the base modifier")

    # an upper bound on what a realm uses: every province counted at its full development (the game counts territories at a
    # quarter); a realm's capacity is the flat part, its rank and its group's early administration, less the base modifier
    dev = {}
    pdir = os.path.join(MOD, "history", "provinces")
    for fn in os.listdir(pdir):
        t = _read(os.path.join(pdir, fn))
        head = re.split(r"(?m)^\d+\.\d+\.\d+\s*=", t)[0]
        o = re.search(r"(?m)^owner = (\w+)", head)
        if o:
            dev[o.group(1)] = dev.get(o.group(1), 0) + sum(int(x) for x in re.findall(r"(?m)^base_(?:tax|production|manpower) = (\d+)", head))
    rank_cap = {"1": 0, "2": 20, "3": 40, "4": 60, "5": 100}

    def capacity(tag):
        t = BY_TAG[tag]
        return (base + rank_cap.get(str(t.rank), 0) + 8 * techs.BASE_LEVEL.get(t.technology_group, 0)) * (1 + techs.GOVERNING_CAPACITY_MODIFIER)

    out = []
    for tag in ("ARB", "ADU"):
        c, u = capacity(tag), dev.get(tag, 0)
        if not c < u:
            out.append(f"{tag}: capacity {c:.0f} vs development {u}")
    note(not out, "the Abbasids and Andalusia start over their governing capacity, with no modifier of their own" + (": " + "; ".join(out) if out else f" (ARB {capacity('ARB'):.0f} of {dev.get('ARB')}, ADU {capacity('ADU'):.0f} of {dev.get('ADU')})"))
    over = sorted((t for t in dev if t in BY_TAG and capacity(t) < dev[t]), key=lambda t: -dev[t] / max(capacity(t), 1))
    print(f"  info {len(over)} of {len(dev)} realms have more development than capacity (counting every province as a full state): {', '.join(over[:12])}")


def new_reforms_are_listed_and_localised() -> None:
    print("\n== government reforms ==")
    gov = _mod("common/governments/00_governments.txt").replace("\r\n", "\n")
    text = _mod("common/government_reforms/zz_kar_government_reforms.txt")
    loc = _mod("localisation/kar_government_reforms_l_english.yml")
    bad = []
    for g, tier, key, _icon, _n, _d, _m, lvl in reforms.REFORMS + reforms.early_reforms():
        block = re.search(rf"(?ms)^{g} = \{{.*?^\}}", gov).group(0)
        if not re.search(rf"\t\t{tier} = \{{\n\t\t\treforms = \{{\n(?:\t\t\t\t[^\n]*\n)*?\t\t\t\t{key}\n", block):
            bad.append(f"{key} not in {g}/{tier}")
        if f"{key} = {{" not in text or f" {key}:" not in loc or f" {key}_desc:" not in loc:
            bad.append(f"{key} missing text")
        if f"adm_tech = {lvl}" not in text or not 0 <= lvl < techs.NEW:
            bad.append(f"{key} unlocked at level {lvl}")
    for g in reforms.EARLY_NAMES:
        block = re.search(rf"(?ms)^{g} = \{{.*?^\}}", gov).group(0)
        order = re.findall(r"(?m)^\t\t(\w+) = \{\n\t\t\treforms", block)
        want = [reforms.early_tier_key(g, i) for i in range(1, len(reforms.EARLY_THEMES) + 1)]
        if order[1:1 + len(want)] != want:
            bad.append(f"{g}: the early tiers do not follow the first tier")
        for k in want:
            if f" {k}:" not in loc:
                bad.append(f"{k} has no name")
    note(not bad, f"{len(reforms.REFORMS) + len(reforms.early_reforms())} new reforms (incl. {len(reforms.EARLY_NAMES)} x {len(reforms.EARLY_THEMES)} early tiers of two) sit in their tiers, are localised and unlock within the new levels" + (": " + "; ".join(bad[:5]) if bad else ""))


def et_style_balance() -> None:
    print("\n== base values and development limits ==")
    st = _mod("common/static_modifiers/00_static_modifiers.txt")
    base = re.search(r"(?ms)^base_values = \{.*?^\}", st).group(0)
    bad = [k for k, (_o, v) in techs.BASE_VALUES.items() if not re.search(rf"(?m)^\t{k}\s*=\s*{re.escape(str(v))}\b", base)]
    bad += [n for n, (_o, v) in techs.CLIMATE_DEVELOPMENT_COST.items() if not re.search(rf"(?ms)^{n} = \{{.*?^\tlocal_development_cost\s*=\s*{v}\b", st)]
    note(not bad, "every country's base values and the climates' development costs follow Extended Timeline's" + (": " + ", ".join(bad) if bad else ""))
    d = _mod("common/defines.lua")
    bad = [k for k, (_o, v) in techs.ET_DEFINES.items() if not re.search(rf"\b{k}\s*=\s*{re.escape(v)}\b", d)]
    note(not bad, "the development limits, reform costs and professionalism per age follow Extended Timeline's" + (": " + ", ".join(bad) if bad else ""))
    note(techs.EARLY_YEARS == sorted(set(techs.EARLY_YEARS)) and techs.EARLY_YEARS[0] == techs.FIRST_YEAR and techs.EARLY_YEARS[-1] < techs.LAST_YEAR,
         "the early levels' years rise from the start date to the base game's first level")


def run() -> None:
    tech_tables_carry_the_early_levels()
    base_game_level_checks_moved()
    governing_capacity_is_earned()
    new_reforms_are_listed_and_localised()
    et_style_balance()
