#!/usr/bin/env python3
"""Mission trees: written for the period in `tools/data/missions/*.missions`, generated into the base game's script shape.

How the base game's mission screen works (read from `interface/countrymissionsview.gui` and its 228 mission files):

* The screen is a grid of five columns. A series' `slot` (1..5) is its column; a mission's `position` is its row (1 = top).
  Every cell is 104x152 pixels: the icon, a title box 90x22 pixels (two lines of the 18pt font) and the arrows.
* A country shows one series per column: a series is offered when its `potential` holds, a series with `generic = no` beats
  `generic = yes` for the same slot. Two series for one country in one column would overlap.
* `required_missions` draws the arrows: straight down to the cell below, a branch to a neighbouring column one row down, a
  "skip tier" line through rows, a horizontal "skip slot" line across a column. A parent therefore lies in a higher row.
* A mission is done when its `trigger` holds; its `effect` is the reward. `provinces_to_highlight` marks the provinces on the
  map. Titles and descriptions are the localisation keys `<mission>_title` and `<mission>_desc`.
* Icons are sprites named `mission_*` in the base game's `countrymissionsview.gfx` (those of the later expansions are not used).

Data file format (`#` starts a comment; blank lines are free):

    [slug]                                   the series is `kar_<slug>`; one block per series
    slot = 1                                 the column, 1..5
    tags = BYZ,ROM                           who is offered it (the series' potential)
    shield = yes                             the realm's shield above the column
    modifier = kar_x | Name | Description | key value, key value        a modifier the rewards may use (event_modifiers)

    mission = id | Title | Description       short id (the full key is `kar_<slug>_<id>`)
    row = 1                                  the row
    needs = a, b, other_slug:c               parents in this series, or `slug:id` in another series of the same realm
    icon = mission_hands_praying
    when = owns 144,145 ; area thrace_area ; dev 300 ; cities 20 ; allies 2 ; subjects 1 ; prestige 50 ; stability 2 ;
           treasury 500 ; tradition 40                                     (all must hold)
    show = province 144,145 ; area thrace_area                             (default: what `when` asks to own)
    reward = prestige 10 ; adm 50 ; dip 50 ; mil 50 ; stability 1 ; treasury 100 ; modifier kar_x 10 ; claim 144,145 ;
             claim_area thrace_area ; core 144
    ai = 250                                 optional ai_weight factor

Rewards stay inside a budget (see `check_data`): the aim is the base game's size of reward, not more."""

import collections
import os
import re

from steps.ideas import FORBIDDEN, KEY_RE, vanilla_ranges
from steps.layout import GAME, MOD
from steps.output import write_loc, write_out

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data", "missions")

SLOTS = range(1, 6)
MAX_ROW = 12
TITLE_MAX = 26      # the title box is 90 x 22 pixels in the 18pt font: two short lines
DESC_RANGE = (40, 320)
MIN_MISSIONS, MAX_MISSIONS = 3, 8
MODIFIER_YEARS = (5, 25)
#: what one mission may give
BUDGET = {"prestige": 30, "adm": 100, "dip": 100, "mil": 100, "stability": 1, "treasury": 300, "claims": 10, "claim_areas": 3, "cores": 4}
MODIFIER_POWER = 1.5

#: trigger words -> the script they write (the value is the number, or the ids and areas)
TRIGGER_NUMBER = {"dev": "total_development", "cities": "num_of_cities", "allies": "num_of_allies", "subjects": "num_of_subjects",
                  "prestige": "prestige", "stability": "stability", "treasury": "treasury", "tradition": "army_tradition"}
TRIGGER_BOUNDS = {"dev": (10, 2000), "cities": (2, 120), "allies": (1, 8), "subjects": (1, 8), "prestige": (10, 100),
                  "stability": (-3, 3), "treasury": (50, 5000), "tradition": (10, 100)}
REWARD_NUMBER = {"prestige": "add_prestige", "adm": "add_adm_power", "dip": "add_dip_power", "mil": "add_mil_power",
                 "treasury": "add_treasury"}


def base_icons():
    """The mission icon sprites of the base game (`mission_*` in countrymissionsview.gfx), the only ones every player has."""
    text = open(os.path.join(GAME, "interface", "countrymissionsview.gfx"), encoding="cp1252", errors="replace").read()
    return set(re.findall(r'name\s*=\s*"(mission_[A-Za-z0-9_\-]+)"', text))


def _ids(text):
    return [int(x) for x in re.findall(r"\d+", text)]


def parse():
    """({slug: series}, [problems]) for every data file; a series keeps `missions` in file order."""
    problems, series, cur, mis = [], {}, None, None
    files = sorted(f for f in os.listdir(DATA) if f.endswith(".missions")) if os.path.isdir(DATA) else []
    for fn in files:
        pending = None  # a multi-line `when =` / `reward =` continues on lines that start with whitespace
        for n, raw in enumerate(open(os.path.join(DATA, fn), encoding="utf-8").read().splitlines(), 1):
            where = f"{fn}:{n}"
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if pending and raw[:1] in (" ", "\t"):
                target, key = pending
                target[key] += " ; " + line
                continue
            pending = None
            m = re.match(r"^\[([a-z][a-z_0-9]*)\]$", line)
            if m:
                cur = {"slug": m.group(1), "file": fn, "slot": None, "tags": [], "not_tags": [], "shield": "yes", "modifiers": {},
                       "missions": collections.OrderedDict()}
                if cur["slug"] in series:
                    problems.append(f"{where}: series {cur['slug']} is defined twice")
                series[cur["slug"]] = cur
                mis = None
                continue
            if cur is None or "=" not in line:
                problems.append(f"{where}: unreadable line {line!r}")
                continue
            key, _, rest = line.partition("=")
            key, rest = key.strip(), rest.strip()
            if key == "mission":
                parts = [p.strip() for p in rest.split("|")]
                if len(parts) != 3 or not re.match(r"^[a-z][a-z_0-9]*$", parts[0]):
                    problems.append(f"{where}: a mission is `id | Title | Description`")
                    mis = None
                    continue
                if parts[0] in cur["missions"]:
                    problems.append(f"{where}: mission {parts[0]} is defined twice in {cur['slug']}")
                mis = {"id": parts[0], "title": parts[1], "desc": parts[2], "row": None, "needs": [], "icon": None, "when": "",
                       "show": "", "reward": "", "ai": None, "where": where}
                cur["missions"][parts[0]] = mis
            elif key == "modifier" and mis is None:
                parts = [p.strip() for p in rest.split("|")]
                if len(parts) != 4:
                    problems.append(f"{where}: a modifier is `id | Name | Description | key value, key value`")
                    continue
                mods = []
                for bit in [b.strip() for b in parts[3].split(",") if b.strip()]:
                    kv = bit.split()
                    try:
                        mods.append((kv[0], float(kv[1])))
                    except (IndexError, ValueError):
                        problems.append(f"{where}: cannot read modifier part {bit!r}")
                cur["modifiers"][parts[0]] = {"name": parts[1], "desc": parts[2], "mods": mods, "where": where}
            elif mis is None:
                if key == "slot":
                    cur["slot"] = int(rest) if rest.isdigit() else rest
                elif key == "tags":
                    cur["tags"] = [t.strip() for t in rest.split(",") if t.strip()]
                elif key == "not_tags":
                    cur["not_tags"] = [t.strip() for t in rest.split(",") if t.strip()]
                elif key == "shield":
                    cur["shield"] = rest
                else:
                    problems.append(f"{where}: unknown series key {key!r}")
            else:
                if key == "row":
                    mis["row"] = int(rest) if rest.isdigit() else rest
                elif key == "needs":
                    mis["needs"] = [t.strip() for t in rest.split(",") if t.strip()]
                elif key == "icon":
                    mis["icon"] = rest
                elif key in ("when", "show", "reward"):
                    mis[key] = rest
                    pending = (mis, key)
                elif key == "ai":
                    mis["ai"] = int(rest) if rest.isdigit() else rest
                else:
                    problems.append(f"{where}: unknown mission key {key!r}")
    return series, problems


def clauses(text, where, problems, allowed):
    """[(word, args)] of a `;`-separated list; `args` is the text after the word."""
    out = []
    for part in [p.strip() for p in text.split(";") if p.strip()]:
        word, _, args = part.partition(" ")
        if word not in allowed:
            problems.append(f"{where}: {word!r} is not one of {sorted(allowed)}")
            continue
        out.append((word, args.strip()))
    return out


WHEN = set(TRIGGER_NUMBER) | {"owns", "area"}
SHOW = {"province", "area"}
REWARD = set(REWARD_NUMBER) | {"stability", "modifier", "claim", "claim_area", "core"}


def full_id(series, mid):
    return f"kar_{series['slug']}_{mid}"


def resolve_need(series_map, series, need):
    """The full key a `needs` entry points at, or None."""
    if ":" in need:
        slug, _, mid = need.partition(":")
        other = series_map.get(slug)
        return full_id(other, mid) if other and mid in other["missions"] else None
    return full_id(series, need) if need in series["missions"] else None


def check_data(series_map):
    """Everything the data must satisfy before a script is written; returns the problems."""
    from steps import provdata

    problems = []
    icons = base_icons()
    ranges = vanilla_ranges()
    land = set(provdata.vanilla_prov_ids()) - set(provdata.sea_ids()) - set(provdata.waste_ids()) - set(provdata.lake_ids())
    areas = provdata.load_areas()
    from tagdb import BY_TAG, FORMABLE_TAGS

    seen_ids = {}
    for s in series_map.values():
        w = s["slug"]
        if s["slot"] not in SLOTS:
            problems.append(f"{w}: slot must be 1..5, not {s['slot']!r}")
        if not s["tags"]:
            problems.append(f"{w}: no tags")
        problems += [f"{w}: tag {t} is not a landed tag here" for t in s["tags"] + s["not_tags"] if t not in BY_TAG and t not in FORMABLE_TAGS]
        if s["shield"] not in ("yes", "no"):
            problems.append(f"{w}: shield is yes or no")
        n = len(s["missions"])
        if not MIN_MISSIONS <= n <= MAX_MISSIONS:
            problems.append(f"{w}: {n} missions, the base game's series hold {MIN_MISSIONS}..{MAX_MISSIONS}")
        for mid, m in s["modifiers"].items():
            if not re.match(r"^kar_[a-z0-9_]+$", mid):
                problems.append(f"{m['where']}: modifier {mid} must be kar_<name>")
            if mid in seen_ids:
                problems.append(f"{m['where']}: modifier {mid} is defined twice")
            seen_ids[mid] = m["where"]
            if not 1 <= len(m["mods"]) <= 3:
                problems.append(f"{m['where']}: modifier {mid} must carry 1..3 effects")
            power = 0.0
            for k, v in m["mods"]:
                if FORBIDDEN.search(k) or k not in ranges or not KEY_RE.match(k):
                    problems.append(f"{m['where']}: {k} is not an allowed modifier")
                    continue
                lo, hi = ranges[k]
                if not min(lo, hi) - 1e-9 <= v <= max(lo, hi) + 1e-9:
                    problems.append(f"{m['where']}: {k} {v:g} is outside the base game's {lo:g}..{hi:g}")
                power += abs(v) / (max(abs(lo), abs(hi)) or 1)
            if power > MODIFIER_POWER + 1e-9:
                problems.append(f"{m['where']}: modifier {mid} is worth {power:.2f}, over {MODIFIER_POWER}")
        for mid, m in s["missions"].items():
            where = m["where"]
            full = full_id(s, mid)
            if full in seen_ids:
                problems.append(f"{where}: {full} is used twice")
            seen_ids[full] = where
            if not isinstance(m["row"], int) or not 1 <= m["row"] <= MAX_ROW:
                problems.append(f"{where}: row must be 1..{MAX_ROW}")
            if not 3 <= len(m["title"]) <= TITLE_MAX:
                problems.append(f"{where}: title {m['title']!r} must be 3..{TITLE_MAX} characters (the title box is two short lines)")
            if not DESC_RANGE[0] <= len(m["desc"]) <= DESC_RANGE[1] or not m["desc"].endswith((".", "!")):
                problems.append(f"{where}: description must be a sentence of {DESC_RANGE[0]}..{DESC_RANGE[1]} characters")
            if m["icon"] not in icons:
                problems.append(f"{where}: icon {m['icon']!r} is not a base-game mission sprite")
            for need in m["needs"]:
                if resolve_need(series_map, s, need) is None:
                    problems.append(f"{where}: needs {need!r}, which does not exist")
            if m["ai"] is not None and not (isinstance(m["ai"], int) and 1 <= m["ai"] <= 1000):
                problems.append(f"{where}: ai is a weight of 1..1000")
            if not m["when"]:
                problems.append(f"{where}: no `when`: a mission needs a condition")
            if not m["reward"]:
                problems.append(f"{where}: no `reward`")
            for word, args in clauses(m["when"], where, problems, WHEN):
                if word in TRIGGER_NUMBER:
                    lo, hi = TRIGGER_BOUNDS[word]
                    if not re.match(r"^-?\d+$", args) or not lo <= int(args) <= hi:
                        problems.append(f"{where}: {word} {args!r} must be a whole number {lo}..{hi}")
                elif word == "owns":
                    problems += [f"{where}: owns {p} is no land province" for p in _ids(args) if p not in land]
                    if not _ids(args):
                        problems.append(f"{where}: owns needs province ids")
                elif word == "area":
                    problems += [f"{where}: area {a} does not exist" for a in re.split(r"[,\s]+", args) if a and a not in areas]
            for word, args in clauses(m["show"], where, problems, SHOW):
                if word == "province":
                    problems += [f"{where}: show province {p} is no land province" for p in _ids(args) if p not in land]
                else:
                    problems += [f"{where}: show area {a} does not exist" for a in re.split(r"[,\s]+", args) if a and a not in areas]
            spent = collections.Counter()
            for word, args in clauses(m["reward"], where, problems, REWARD):
                if word in REWARD_NUMBER or word == "stability":
                    if not re.match(r"^\d+$", args) or int(args) < 1:
                        problems.append(f"{where}: {word} {args!r} must be a positive whole number")
                    else:
                        spent[word] += int(args)
                elif word == "modifier":
                    bits = args.split()
                    if len(bits) != 2 or not bits[1].isdigit() or not MODIFIER_YEARS[0] <= int(bits[1]) <= MODIFIER_YEARS[1]:
                        problems.append(f"{where}: modifier is `id years` with years {MODIFIER_YEARS[0]}..{MODIFIER_YEARS[1]}")
                    elif bits[0] not in s["modifiers"]:
                        problems.append(f"{where}: modifier {bits[0]} is not defined in series {s['slug']}")
                    spent["modifiers"] += 1
                elif word in ("claim", "core"):
                    ids = _ids(args)
                    problems += [f"{where}: {word} {p} is no land province" for p in ids if p not in land]
                    spent["claims" if word == "claim" else "cores"] += len(ids)
                elif word == "claim_area":
                    names = [a for a in re.split(r"[,\s]+", args) if a]
                    problems += [f"{where}: claim_area {a} does not exist" for a in names if a not in areas]
                    spent["claim_areas"] += len(names)
            for k, cap in BUDGET.items():
                if spent[k] > cap:
                    problems.append(f"{where}: {k} reward {spent[k]} is over the budget {cap}")
            if spent["modifiers"] > 1:
                problems.append(f"{where}: one modifier per mission")
    return problems


# --- writing -------------------------------------------------------------------------------------------------------------

def _area_claim(name):
    return (f"\t\t\t{name} = {{\n\t\t\t\tlimit = {{\n\t\t\t\t\tNOT = {{ is_core = ROOT }}\n\t\t\t\t\tNOT = {{ is_permanent_claim = ROOT }}\n"
            f"\t\t\t\t}}\n\t\t\t\tadd_permanent_claim = ROOT\n\t\t\t}}\n")


def trigger_text(m):
    out = []
    probs = []
    for word, args in clauses(m["when"], "", probs, WHEN):
        if word in TRIGGER_NUMBER:
            out.append(f"\t\t\t{TRIGGER_NUMBER[word]} = {int(args)}\n")
        elif word == "owns":
            out += [f"\t\t\towns_or_non_sovereign_subject_of = {p}\n" for p in _ids(args)]
        else:
            for a in [x for x in re.split(r"[,\s]+", args) if x]:
                out.append(f"\t\t\t{a} = {{\n\t\t\t\ttype = all\n\t\t\t\tcountry_or_non_sovereign_subject_holds = ROOT\n\t\t\t}}\n")
    return "".join(out)


def highlight(m):
    """(provinces, areas) the screen marks: `show`, or what `when` asks to own."""
    provs, areas = [], []
    source = clauses(m["show"], "", [], SHOW) if m["show"] else clauses(m["when"], "", [], {"owns", "area"})
    for word, args in source:
        if word in ("province", "owns"):
            provs += _ids(args)
        elif word == "area":
            areas += [x for x in re.split(r"[,\s]+", args) if x]
    return provs, areas


def highlight_text(m):
    provs, areas = highlight(m)
    if not provs and not areas:
        return ""
    items = [f"\t\t\t\tprovince_id = {p}\n" for p in provs] + [f"\t\t\t\tarea = {a}\n" for a in areas]
    if len(items) == 1:
        head = items[0].replace("\t\t\t\t", "\t\t\t")
    else:
        head = "\t\t\tOR = {\n" + "".join(items) + "\t\t\t}\n"
    return ("\t\tprovinces_to_highlight = {\n" + head + "\t\t\tNOT = { country_or_non_sovereign_subject_holds = ROOT }\n\t\t}\n")


def effect_text(m):
    out = []
    for word, args in clauses(m["reward"], "", [], REWARD):
        if word in REWARD_NUMBER:
            out.append(f"\t\t\t{REWARD_NUMBER[word]} = {int(args)}\n")
        elif word == "stability":
            out.append("\t\t\tadd_stability_or_adm_power = yes\n" * int(args))
        elif word == "modifier":
            name, years = args.split()
            out.append(f"\t\t\tadd_country_modifier = {{\n\t\t\t\tname = \"{name}\"\n\t\t\t\tduration = {int(years) * 365}\n\t\t\t}}\n")
        elif word == "claim":
            for p in _ids(args):
                out.append(f"\t\t\t{p} = {{\n\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{\n\t\t\t\t\t\tNOT = {{ is_core = ROOT }}\n"
                           f"\t\t\t\t\t\tNOT = {{ is_permanent_claim = ROOT }}\n\t\t\t\t\t}}\n\t\t\t\t\tadd_permanent_claim = ROOT\n\t\t\t\t}}\n\t\t\t}}\n")
        elif word == "claim_area":
            out += [_area_claim(a) for a in re.split(r"[,\s]+", args) if a]
        elif word == "core":
            for p in _ids(args):
                out.append(f"\t\t\t{p} = {{\n\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ owned_by = ROOT }}\n\t\t\t\t\tadd_core = ROOT\n\t\t\t\t}}\n\t\t\t}}\n")
    return "".join(out)


def potential_text(s):
    pos = [f"tag = {t}" for t in s["tags"]]
    lines = []
    if len(pos) == 1:
        lines.append(f"\t\t{pos[0]}\n")
    else:
        lines.append("\t\tOR = {\n" + "".join(f"\t\t\t{p}\n" for p in pos) + "\t\t}\n")
    for t in s["not_tags"]:
        lines.append(f"\t\tNOT = {{ tag = {t} }}\n")
    return "".join(lines)


def series_text(series_map, s):
    out = [f"kar_{s['slug']} = {{\n\n\tslot = {s['slot']}\n\tgeneric = no\n\tai = yes\n\n\tpotential = {{\n{potential_text(s)}\t}}\n"
           f"\thas_country_shield = {s['shield']}\n"]
    for mid, m in s["missions"].items():
        needs = " ".join(resolve_need(series_map, s, n) for n in m["needs"])
        block = [f"\n\t{full_id(s, mid)} = {{\n\t\ticon = {m['icon']}\n\t\trequired_missions = {{ {needs} }}\n\t\tposition = {m['row']}\n"]
        block.append(highlight_text(m))
        block.append("\t\ttrigger = {\n" + trigger_text(m) + "\t\t}\n")
        block.append("\t\teffect = {\n" + effect_text(m) + "\t\t}\n")
        if m["ai"]:
            block.append(f"\t\tai_weight = {{\n\t\t\tfactor = {m['ai']}\n\t\t}}\n")
        block.append("\t}\n")
        out.append("".join(block))
    out.append("}\n")
    return "".join(out)


def modifier_pairs(series_map):
    out = []
    for s in series_map.values():
        for mid, m in s["modifiers"].items():
            out.append((mid, m))
    return out


def modifiers_text(series_map):
    lines = ["# Generated by tools/steps/missions.py from tools/data/missions/*.missions; do not edit.\n"]
    for mid, m in modifier_pairs(series_map):
        body = "".join(f"\t{k} = {v:.4f}".rstrip("0").rstrip(".") + "\n" for k, v in m["mods"])
        lines.append(f"\n{mid} = {{\n{body}}}\n")
    return "".join(lines)


def loc_pairs(series_map):
    pairs = []
    for s in series_map.values():
        for mid, m in s["missions"].items():
            pairs += [(f"{full_id(s, mid)}_title", m["title"]), (f"{full_id(s, mid)}_desc", m["desc"])]
        for mid, m in s["modifiers"].items():
            pairs += [(mid, m["name"]), (f"desc_{mid}", m["desc"])]
    return pairs


def output_files(series_map):
    """{relative path: text} of the mission scripts, one per data file."""
    by_file = collections.OrderedDict()
    for s in series_map.values():
        by_file.setdefault(s["file"], []).append(s)
    head = "# Generated by tools/steps/missions.py from tools/data/missions/{}; do not edit.\n\n"
    return {os.path.join("missions", "kar_" + fn[:-len(".missions")] + ".txt"):
            head.format(fn) + "\n".join(series_text(series_map, s) for s in group) for fn, group in by_file.items()}


def step_missions():
    series_map, problems = parse()
    problems += check_data(series_map)
    if not problems:
        problems += check_flow(series_map)
    if problems:
        raise SystemExit("mission data:\n  " + "\n  ".join(problems[:40]))
    outdir = os.path.join(MOD, "missions")
    for rel, text in output_files(series_map).items():
        write_out(os.path.join(MOD, rel), text)
    write_out(os.path.join(MOD, "common", "event_modifiers", "kar_mission_modifiers.txt"), modifiers_text(series_map))
    write_loc(os.path.join(MOD, "localisation", "kar_missions_l_english.yml"), loc_pairs(series_map))
    total = sum(len(s["missions"]) for s in series_map.values())
    print(f"missions: {len(series_map)} series, {total} missions, {len(modifier_pairs(series_map))} modifiers; hand-written files kept in {outdir}")


# --- the grid and the flow, on the data ---------------------------------------------------------------------------------

def cells_by_tag(series_map):
    """{tag: [(series, mission id, slot, row)]} for every tag a series is offered to."""
    out = collections.defaultdict(list)
    for s in series_map.values():
        for t in s["tags"]:
            if t in s["not_tags"]:
                continue
            for mid, m in s["missions"].items():
                out[t].append((s, mid, s["slot"], m["row"]))
    return out


def check_flow(series_map):
    """The screen's rules on the data: one series per column, one mission per cell, parents above, arrows that can be drawn."""
    problems = []
    by_tag = collections.defaultdict(list)
    for s in series_map.values():
        for t in s["tags"]:
            by_tag[t].append(s)
    for tag, group in by_tag.items():
        slots = collections.Counter(s["slot"] for s in group)
        for slot, k in slots.items():
            if k > 1:
                problems.append(f"{tag}: {k} series in column {slot}: " + ", ".join(s["slug"] for s in group if s["slot"] == slot))
        cell = {}
        for s in group:
            for mid, m in s["missions"].items():
                if (s["slot"], m["row"]) in cell and cell[(s["slot"], m["row"])] != (s["slug"], mid):
                    problems.append(f"{tag}: {s['slug']}:{mid} and {cell[(s['slot'], m['row'])]} share a cell")
                cell[(s["slot"], m["row"])] = (s["slug"], mid)
    for s in series_map.values():
        rows = sorted({m["row"] for m in s["missions"].values() if isinstance(m["row"], int)})
        if rows and rows != list(range(1, rows[-1] + 1)):
            problems.append(f"{s['slug']}: rows {rows} must run 1..{rows[-1]} without a gap")
        if rows and len(rows) != len(s["missions"]):
            problems.append(f"{s['slug']}: a column holds one mission per row")
        for mid, m in s["missions"].items():
            for need in m["needs"]:
                key = resolve_need(series_map, s, need)
                if key is None:
                    continue
                other_slug, other_mid = (need.split(":") if ":" in need else (s["slug"], need))
                parent_series = series_map[other_slug]
                parent = parent_series["missions"][other_mid]
                if not isinstance(parent["row"], int) or not isinstance(m["row"], int):
                    continue
                if parent["row"] >= m["row"]:
                    problems.append(f"{m['where']}: {mid} (row {m['row']}) needs {need} in row {parent['row']}: a parent lies above")
                if abs(parent_series["slot"] - s["slot"]) > 2:
                    problems.append(f"{m['where']}: {mid} needs {need} {abs(parent_series['slot'] - s['slot'])} columns away")
                if ":" in need and not set(s["tags"]) <= set(parent_series["tags"]):
                    problems.append(f"{m['where']}: {need} is not offered to every realm that gets {s['slug']}")
            if not m["needs"] and m["row"] != 1:
                problems.append(f"{m['where']}: {mid} needs nothing but sits in row {m['row']}; a first mission is in row 1")
            if m["needs"] and m["row"] == 1:
                problems.append(f"{m['where']}: {mid} is in row 1 but has parents")
        # cycles
        graph = {mid: [n for n in m["needs"] if ":" not in n] for mid, m in s["missions"].items()}
        state = {}

        def visit(node, trail):
            if state.get(node) == 1:
                problems.append(f"{s['slug']}: a requirement cycle through {' -> '.join(trail + [node])}")
                return
            if state.get(node) == 2:
                return
            state[node] = 1
            for nxt in graph.get(node, []):
                if nxt in graph:
                    visit(nxt, trail + [node])
            state[node] = 2

        for node in graph:
            visit(node, [])
    return problems


# --- reading the scripts the mod ships (generated and hand-written alike) ------------------------------------------------

def _code(text):
    return "\n".join(ln.split("#", 1)[0] for ln in text.splitlines())


def _blocks(body):
    """[(name, inner text)] of the first-level `name = { ... }` blocks of a script text."""
    out, i = [], 0
    pat = re.compile(r"([A-Za-z0-9_.\-\"]+)\s*=\s*\{")
    while True:
        m = pat.search(body, i)
        if not m:
            return out
        depth, j = 1, m.end()
        while depth and j < len(body):
            depth += (body[j] == "{") - (body[j] == "}")
            j += 1
        out.append((m.group(1).strip('"'), body[m.end():j - 1]))
        i = j


def _scalar(body, key):
    """The value of a top-level `key = value` of a block body, or None."""
    depth = 0
    for ln in body.splitlines():
        if depth == 0:
            m = re.match(rf"\s*{key}\s*=\s*([^\s{{}}]+)\s*$", ln)
            if m:
                return m.group(1)
        depth += ln.count("{") - ln.count("}")
    return None


def load_scripts():
    """{series key: series} for every file in the mod's missions folder: slot, generic, shield, tags (from `potential`),
    and for each mission its icon, row, parents, trigger and effect text."""
    out = {}
    folder = os.path.join(MOD, "missions")
    for fn in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not fn.endswith(".txt"):
            continue
        text = _code(open(os.path.join(folder, fn), encoding="cp1252", errors="replace").read())
        for name, body in _blocks(text):
            pot = dict(_blocks(body)).get("potential", "")
            missions = collections.OrderedDict()
            for k, b in _blocks(body):
                if k in ("potential", "potential_on_load") or not re.search(r"\btrigger\s*=", b):
                    continue
                parts = dict(_blocks(b))
                req = re.search(r"required_missions\s*=\s*\{([^}]*)\}", b)
                row = _scalar(b, "position")
                missions[k] = {"icon": _scalar(b, "icon"), "row": int(row) if row and row.isdigit() else (1 if row is None else row),
                               "needs": req.group(1).split() if req else [], "trigger": parts.get("trigger", ""),
                               "effect": parts.get("effect", ""), "highlight": parts.get("provinces_to_highlight"), "file": fn}
            slot = _scalar(body, "slot")
            out[name] = {"key": name, "file": fn, "slot": int(slot) if slot and slot.isdigit() else slot,
                         "generic": _scalar(body, "generic"), "ai": _scalar(body, "ai"), "shield": _scalar(body, "has_country_shield"),
                         "potential": pot, "tags": re.findall(r"\btag\s*=\s*([A-Z0-9]{3})\b", pot), "missions": missions}
    return out


#: subject types that count as "held by the liege" for `country_or_non_sovereign_subject_holds` and `owns_or_non_sovereign_subject_of`
NON_SOVEREIGN = ("vassal", "theme_subject_type", "daimyo_vassal", "march", "appanage")


def liege_map():
    """{subject tag: liege tag} for the non-sovereign subjects of the start date."""
    from tagdb import DIPLOMACY

    return {d.subject: d.liege for d in DIPLOMACY if d.relation in NON_SOVEREIGN}


def holder_of(owner, lieges):
    """Who a province counts for: its owner, or the top liege that owner is a non-sovereign subject of."""
    seen = set()
    while owner in lieges and owner not in seen:
        seen.add(owner)
        owner = lieges[owner]
    return owner
