"""National ideas for the larger new tags.

EU5 has no national ideas, so the sets are built from what the tag is (government, religion, culture group, size,
what its provinces produce) out of themed lists of modifiers. A modifier is only used if the base game's own idea
files use it (`vanilla_modifiers`), and its value is the median the base game gives it, so the sets stay inside
the base game's balance. `python3 tools/ideas.py` prints the harvest and the check.
"""
import hashlib
import re
import statistics
from collections import defaultdict

from paths import EU4_GAME
from pdx import parse

IDEA_FILES = ("00_country_ideas.txt", "zz_group_ideas.txt", "00_basic_ideas.txt", "zzz_default_idea.txt")
NOT_MODIFIERS = {"trigger", "free", "ai_will_do", "category", "ideas", "ai_importance"}


def vanilla_modifiers():
    """{modifier: {'idea': [values], 'start': [...], 'bonus': [...]}} of every numeric modifier the base game's idea
    sets use, by the part of the set it appears in."""
    out = defaultdict(lambda: defaultdict(list))
    for fn in IDEA_FILES:
        text = (EU4_GAME / "common/ideas" / fn).read_text(encoding="latin-1")
        for _name, body in parse(text):
            if not isinstance(body, list):
                continue
            for key, part in body:
                if key in NOT_MODIFIERS or not isinstance(part, list):
                    continue
                kind = key if key in ("start", "bonus") else "idea"
                for mod, val in part:
                    if mod and mod not in NOT_MODIFIERS and isinstance(val, str):
                        try:
                            out[mod][kind].append(float(val))
                        except ValueError:
                            pass
    return out


# theme -> [(modifier, idea name)]. Every modifier has to occur in the base game's ideas (checked below).
THEMES = {
    "land": [("infantry_power", "Levy Infantry"), ("cavalry_power", "Mounted Retinues"),
             ("artillery_power", "Siege Craft"), ("discipline", "Drilled Ranks"), ("land_morale", "Martial Pride"),
             ("land_forcelimit_modifier", "Muster of the Realm"), ("global_manpower_modifier", "Sons of the Soil"),
             ("manpower_recovery_speed", "Quick Recruitment"), ("siege_ability", "Siege Engineers")],
    "defence": [("defensiveness", "Stout Walls"), ("hostile_attrition", "Harsh Frontier"),
                ("garrison_size", "Standing Garrisons"), ("fort_maintenance_modifier", "Frugal Fortresses")],
    "economy": [("global_tax_modifier", "Careful Collectors"), ("production_efficiency", "Busy Workshops"),
                ("development_cost", "Steady Growth"), ("build_cost", "Master Builders"),
                ("global_trade_goods_size_modifier", "Bountiful Harvests"), ("inflation_reduction", "Sound Coinage")],
    "trade": [("trade_efficiency", "Honest Merchants"), ("global_trade_power", "Caravan Roads"),
              ("merchants", "Travelling Merchants"), ("trade_steering", "Market Influence"),
              ("caravan_power", "Caravan Guilds")],
    "naval": [("naval_forcelimit_modifier", "Shipwrights"), ("naval_morale", "Seasoned Mariners"),
              ("global_ship_cost", "Cheap Hulls"), ("global_ship_trade_power", "Merchant Fleets")],
    "admin": [("stability_cost_modifier", "Peaceful Order"), ("core_creation", "Careful Integration"),
              ("idea_cost", "Open Minds"), ("advisor_cost", "Loyal Counsellors"), ("global_unrest", "Contented Subjects"),
              ("legitimacy", "Rightful Rule"), ("prestige", "Renowned Court")],
    "diplomacy": [("diplomatic_reputation", "Honoured Envoys"), ("diplomats", "Skilled Diplomats"),
                  ("improve_relation_modifier", "Gift Giving"), ("diplomatic_upkeep", "Wide Alliances")],
    "faith": [("tolerance_own", "Devout Realm"), ("global_missionary_strength", "Zealous Preachers"),
              ("tolerance_heathen", "Open Hearth"), ("devotion", "Pious Rulers")],
    "republic": [("republican_tradition", "Civic Pride")],
    "horde": [("horde_unity", "Bond of the Horde")],
    "theocracy": [("church_power_modifier", "Hierarchy of the Church")],
}
# which themes a tag leans on, by government and by culture/religion group; weights add up
GOV_WEIGHT = {
    "monarchy": {"land": 2, "admin": 2, "economy": 1, "defence": 1},
    "republic": {"trade": 3, "naval": 2, "economy": 2, "republic": 3, "admin": 1},
    "theocracy": {"faith": 3, "admin": 2, "theocracy": 3, "defence": 1},
    "tribal": {"land": 3, "defence": 2, "faith": 1},
    "native": {"land": 2, "defence": 2, "faith": 1, "economy": 1},
}
GROUP_WEIGHT = {  # culture group -> themes
    "turko_tatar": {"land": 2, "horde": 2}, "mongol": {"land": 2, "horde": 2}, "altaic": {"land": 2},
    "arabic": {"trade": 1, "faith": 1}, "iranian": {"economy": 1, "diplomacy": 1},
    "germanic": {"economy": 1, "admin": 1}, "latin": {"trade": 1, "diplomacy": 1},
    "east_asian": {"admin": 2, "economy": 1}, "indian": {"economy": 1, "faith": 1},
}
RELIGION_WEIGHT = {"muslim": {"faith": 1}, "christian": {"faith": 1, "diplomacy": 1}, "dharmic": {"faith": 1},
                   "eastern": {"admin": 1}, "pagan": {"defence": 1}}
SET_SIZE = 7


def check_themes(mods=None):
    mods = mods or vanilla_modifiers()
    missing = [m for t in THEMES.values() for m, _ in t if not mods.get(m, {}).get("idea")]
    if missing:
        raise SystemExit(f"ideas: modifiers the base game's ideas never use: {missing}")
    return mods


def value(mods, mod, kind):
    vals = mods[mod].get(kind) or mods[mod]["idea"]
    v = statistics.median(vals)
    return round(v, 3)


def _rank(tag, salt):
    return int(hashlib.md5(f"{tag}:{salt}".encode()).hexdigest(), 16)


def choose(tag, feats, mods):
    """(start [(mod, val)], bonus (mod, val), ideas [(key, name, mod, val)]) for a tag's features."""
    w = defaultdict(float)
    for src, key in ((GOV_WEIGHT, feats["gov"]), (GROUP_WEIGHT, feats["culture_group"]),
                     (RELIGION_WEIGHT, feats["religion_group"])):
        for th, n in src.get(key, {}).items():
            w[th] += n
    for th in ("land", "admin", "economy", "trade", "diplomacy", "defence"):
        w[th] += 0.5  # every realm has a little of the basics
    if feats.get("horde"):
        w["horde"] += 3
        w["land"] += 2
    if feats.get("coastal"):
        w["naval"] += 2
        w["trade"] += 1
    if feats.get("rich"):
        w["economy"] += 1
    cand = [(th, m, n) for th, lst in THEMES.items() for m, n in lst if w[th] > 0]
    # strongest theme first, ties and the rest in a per-tag order so sets differ
    ordered = sorted(cand, key=lambda c: (-w[c[0]], _rank(tag, c[1])))
    picked, themes = [], defaultdict(int)
    for th, m, n in ordered:
        if themes[th] >= 3 or any(p[1] == m for p in picked):
            continue
        picked.append((th, m, n))
        themes[th] += 1
        if len(picked) == SET_SIZE + 3:
            break
    if len(picked) < SET_SIZE + 3:
        raise SystemExit(f"ideas: not enough modifiers for {tag}")
    start = [(m, value(mods, m, "start")) for _, m, _ in picked[:2]]
    bonus = (picked[2][1], value(mods, picked[2][1], "bonus"))
    ideas = [(f"{tag}_idea_{i}", n, m, value(mods, m, "idea")) for i, (_, m, n) in enumerate(picked[3:], 1)]
    return start, bonus, ideas


def tag_features():
    """{tag: features} for every tag the mod registers that holds at least MIN_PROVINCES provinces or MIN_DEV
    development, read back from the generated history."""
    import json
    from paths import MOD
    groups = {}
    ctext = (EU4_GAME / "common/cultures/00_cultures.txt").read_text(encoding="latin-1")
    for g, body in parse(ctext):
        if isinstance(body, list):
            for k, v in body:
                if isinstance(v, list) and k not in ("dynasty_names", "male_names", "female_names"):
                    groups[k] = g
    rel_group = {}
    for g, body in parse((EU4_GAME / "common/religions/00_religion.txt").read_text(encoding="latin-1")):
        if isinstance(body, list):
            for k, v in body:
                if isinstance(v, list):
                    rel_group[k] = g
    for g, body in parse((MOD / "common/religions/1337_religions.txt").read_text(encoding="latin-1")):
        for k, v in body:
            if isinstance(v, list):
                rel_group[k] = g
    held, dev, goods = defaultdict(int), defaultdict(int), defaultdict(set)
    for f in (MOD / "history/provinces").iterdir():
        top = re.split(r"(?m)^\d{3,4}\.\d+\.\d+\s*=", f.read_text(encoding="latin-1"))[0]
        m = re.search(r"(?m)^owner = (\w+)", top)
        if not m:
            continue
        held[m[1]] += 1
        dev[m[1]] += sum(int(x) for x in re.findall(r"(?m)^base_(?:tax|production|manpower)\s*=\s*(\d+)", top))
        g = re.search(r"(?m)^trade_goods\s*=\s*(\w+)", top)
        if g:
            goods[m[1]].add(g[1])
        if re.search(r"(?m)^shipyard\s*=\s*yes", top):
            goods[m[1]].add("shipyard")
    new = {v["eu4"] for v in json.load(open(MOD / "tools/data/tags.json")).values() if v["new"]}
    out = {}
    for tag in sorted(new):
        if held[tag] < MIN_PROVINCES and dev[tag] < MIN_DEV:
            continue
        f = next((MOD / "history/countries").glob(f"{tag} - *.txt"))
        t = f.read_text(encoding="latin-1")
        gov = re.search(r"(?m)^government = (\w+)", t)[1]
        cul = re.search(r"(?m)^primary_culture = (\w+)", t)
        rel = re.search(r"(?m)^religion = (\w+)", t)
        out[tag] = dict(gov=gov, culture_group=groups.get(cul[1]) if cul else None,
                        religion_group=rel_group.get(rel[1]) if rel else None,
                        coastal=bool(goods[tag] & {"fish", "naval_supplies", "shipyard"}), rich=dev[tag] >= MIN_DEV,
                        horde="steppe_horde" in t, provinces=held[tag])
    return out


MIN_PROVINCES, MIN_DEV = 3, 25


def write(mods=None):
    """common/ideas/1337_national_ideas.txt and localisation/1337_ideas_l_english.yml; returns the tag count."""
    from paths import MOD
    mods = check_themes(mods)
    loc_src = (MOD / "localisation/1337_countries_l_english.yml").read_text(encoding="utf-8-sig")
    adj = dict(re.findall(r'^ ([A-Z0-9]{3})_ADJ:\d+ "(.*)"', loc_src, re.M))
    feats = tag_features()
    text, loc = ["# generated by tools/ideas.py - do not edit"], ["l_english:"]
    for tag, f in feats.items():
        start, bonus, ideas = choose(tag, f, mods)
        a = adj.get(tag, tag)
        text += ["", f"{tag}_ideas = {{", "\tstart = {"] + [f"\t\t{m} = {v}" for m, v in start] + ["\t}",
                 "\tbonus = {", f"\t\t{bonus[0]} = {bonus[1]}", "\t}",
                 "\ttrigger = {", f"\t\ttag = {tag}", "\t}", "\tfree = yes"]
        for key, name, m, v in ideas:
            text += [f"\t{key} = {{", f"\t\t{m} = {v}", "\t}"]
        text.append("}")
        loc += [f' {tag}_ideas:0 "{a} Ideas"', f' {tag}_ideas_start:0 "{a} Traditions"',
                f' {tag}_ideas_bonus:0 "{a} Ambition"']
        for key, name, m, v in ideas:
            loc += [f' {key}:0 "{a} {name}"', f' {key}_desc:0 "{name} shapes how the {a} realm fights, governs and trades."']
    out = MOD / "common/ideas"
    out.mkdir(parents=True, exist_ok=True)
    (out / "1337_national_ideas.txt").write_bytes(("\n".join(text) + "\n").encode("latin-1", "replace"))
    (MOD / "localisation/1337_ideas_l_english.yml").write_text("\ufeff" + "\n".join(loc) + "\n", encoding="utf-8")
    return len(feats)


if __name__ == "__main__":
    mods = check_themes()
    print(len(mods), "modifiers in the base game's ideas; every theme modifier is among them")
    print(write(mods), "idea sets written")
