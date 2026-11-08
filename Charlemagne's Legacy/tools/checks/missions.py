#!/usr/bin/env python3
"""Mission trees: laid out and wired the way the base game's mission screen needs, and playable from the start date.

The rules come from the base game's own files (see tools/steps/missions.py): five columns (`slot`), rows (`position`), one series
per column and one mission per cell for a country, parents above their children, arrows that the screen can draw, icons that
exist, titles that fit the 90 x 22 pixel box, localisation for every mission, provinces that are land, and triggers that are not
already true when the game starts."""

import collections
import os
import re

from checks.context import BY_TAG, FORMABLE_TAGS, MOD
from checks.report import note


def _loc_keys():
    keys = set()
    folder = os.path.join(MOD, "localisation")
    for fn in os.listdir(folder):
        if fn.endswith("_l_english.yml"):
            keys |= set(re.findall(r"(?m)^\s*([A-Za-z0-9_.\-]+):\d*\s+\"", open(os.path.join(folder, fn), encoding="utf-8-sig").read()))
    return keys


def _loc_values():
    values = {}
    folder = os.path.join(MOD, "localisation")
    for fn in os.listdir(folder):
        if fn.endswith("_l_english.yml"):
            for k, v in re.findall(r"(?m)^\s*([A-Za-z0-9_.\-]+):\d*\s+\"(.*)\"\s*$", open(os.path.join(folder, fn), encoding="utf-8-sig").read()):
                values[k] = v
    return values


def _modifier_names():
    names = set()
    folder = os.path.join(MOD, "common", "event_modifiers")
    for fn in os.listdir(folder):
        if fn.endswith(".txt"):
            names |= set(re.findall(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{", open(os.path.join(folder, fn), encoding="cp1252", errors="replace").read()))
    return names


def _start_owners():
    """{province id: owner tag} from the generated province history, as the game starts."""
    owners = {}
    folder = os.path.join(MOD, "history", "provinces")
    for fn in os.listdir(folder):
        m = re.match(r"^(\d+)\s*-", fn)
        if not m:
            continue
        head = re.split(r"(?m)^\d+\.\d+\.\d+", open(os.path.join(folder, fn), encoding="cp1252", errors="replace").read(), maxsplit=1)[0]
        o = re.search(r"(?m)^owner\s*=\s*([A-Z0-9]{3})", head)
        if o:
            owners[int(m.group(1))] = o.group(1)
    return owners


def run() -> None:
    print("\n== mission trees (tools/steps/missions.py, tools/data/missions) ==")
    from steps import missions as M
    from steps import provdata

    series_map, problems = M.parse()
    problems += M.check_data(series_map)
    if not problems:
        problems += M.check_flow(series_map)
    note(not problems, f"{len(series_map)} mission series in the data are well formed, within the reward budget and wired ({len(problems)} problems)")
    for p in problems[:12]:
        print("        " + p)

    scripts = M.load_scripts()
    icons = M.base_icons()
    loc = _loc_keys()
    values = _loc_values()
    modifiers = _modifier_names()
    land = set(provdata.vanilla_prov_ids()) - set(provdata.sea_ids()) - set(provdata.waste_ids()) - set(provdata.lake_ids())
    areas = provdata.load_areas()
    lieges = M.liege_map()
    owners = {p: M.holder_of(o, lieges) for p, o in _start_owners().items()}

    # the script of every series, whether generated or written by hand
    shape = []
    seen = {}
    for key, s in scripts.items():
        if s["slot"] not in M.SLOTS:
            shape.append(f"{key}: slot {s['slot']!r} is not a column 1..5")
        if s["generic"] != "no" or s["ai"] != "yes":
            shape.append(f"{key}: generic = no and ai = yes like the base game's series")
        if s["shield"] not in ("yes", "no"):
            shape.append(f"{key}: has_country_shield missing")
        if not s["tags"]:
            shape.append(f"{key}: its potential names no tag")
        shape += [f"{key}: tag {t} does not exist here" for t in s["tags"] if t not in BY_TAG and t not in FORMABLE_TAGS]
        if not M.MIN_MISSIONS <= len(s["missions"]) <= M.MAX_MISSIONS:
            shape.append(f"{key}: {len(s['missions'])} missions, a series holds {M.MIN_MISSIONS}..{M.MAX_MISSIONS}")
        for mid, m in s["missions"].items():
            if mid in seen:
                shape.append(f"{mid} is defined in both {seen[mid]} and {key}")
            seen[mid] = key
            if m["icon"] not in icons:
                shape.append(f"{mid}: icon {m['icon']!r} is not a base-game mission sprite")
            if not isinstance(m["row"], int) or not 1 <= m["row"] <= M.MAX_ROW:
                shape.append(f"{mid}: position {m['row']!r} is outside 1..{M.MAX_ROW}")
            if not m["trigger"].strip() or not m["effect"].strip():
                shape.append(f"{mid}: a mission needs a trigger and an effect")
    note(not shape, f"every mission series is shaped like the base game's: column, icon, row, trigger and effect ({len(shape)} off)")
    for line in shape[:12]:
        print("        " + line)

    # one series per column and one mission per cell for each realm; parents above; arrows the screen can draw
    by_tag = collections.defaultdict(list)
    for s in scripts.values():
        for t in s["tags"]:
            by_tag[t].append(s)
    grid = []
    for tag, group in sorted(by_tag.items()):
        cols = collections.Counter(s["slot"] for s in group)
        grid += [f"{tag}: {n} series in column {c}: " + ", ".join(s["key"] for s in group if s["slot"] == c) for c, n in cols.items() if n > 1]
        cell = {}
        place = {}
        for s in group:
            for mid, m in s["missions"].items():
                if (s["slot"], m["row"]) in cell:
                    grid.append(f"{tag}: {mid} and {cell[(s['slot'], m['row'])]} share column {s['slot']} row {m['row']}")
                cell[(s["slot"], m["row"])] = mid
                place[mid] = (s["slot"], m["row"], s)
        for s in group:
            for mid, m in s["missions"].items():
                for need in m["needs"]:
                    if need not in place:
                        grid.append(f"{tag}: {mid} needs {need}, which this realm does not get")
                        continue
                    pc, pr, _ps = place[need]
                    if pr >= m["row"]:
                        grid.append(f"{tag}: {mid} (row {m['row']}) needs {need} (row {pr}): a parent lies above its child")
                    if abs(pc - s["slot"]) > 2:
                        grid.append(f"{tag}: {mid} needs {need} {abs(pc - s['slot'])} columns away; the screen draws at most two")
                if not m["needs"] and m["row"] != 1:
                    grid.append(f"{tag}: {mid} needs nothing but is in row {m['row']}")
                if m["needs"] and m["row"] == 1:
                    grid.append(f"{tag}: {mid} has parents but is in the first row")
    note(not grid, f"each realm gets one series per column, one mission per cell, parents above children ({len(grid)} problems)")
    for line in grid[:12]:
        print("        " + line)

    cycles = []
    for tag, group in by_tag.items():
        graph = {mid: m["needs"] for s in group for mid, m in s["missions"].items()}
        state = {}

        def visit(node, trail):
            if state.get(node) == 1:
                cycles.append(f"{tag}: cycle {' -> '.join(trail + [node])}")
                return
            if state.get(node) == 2 or node not in graph:
                return
            state[node] = 1
            for nxt in graph[node]:
                visit(nxt, trail + [node])
            state[node] = 2

        for node in graph:
            visit(node, [])
    note(not cycles, f"no mission waits on itself, and every mission can be reached from a first one ({len(cycles)} cycles)")
    for line in cycles[:6]:
        print("        " + line)

    # localisation: every mission has a title that fits its box and a description
    textual = []
    for key, s in scripts.items():
        for mid in s["missions"]:
            for suffix in ("title", "desc"):
                if f"{mid}_{suffix}" not in loc:
                    textual.append(f"{mid}_{suffix} has no localisation")
            title = values.get(f"{mid}_title", "")
            if len(title) > M.TITLE_MAX:
                textual.append(f"{mid}: title {title!r} is {len(title)} characters; the box fits {M.TITLE_MAX}")
            if "\\n" in title or '"' in title:
                textual.append(f"{mid}: no line breaks or quotes in a title")
            desc = values.get(f"{mid}_desc", "")
            if desc and not M.DESC_RANGE[0] <= len(desc) <= M.DESC_RANGE[1] + 80:
                textual.append(f"{mid}: description is {len(desc)} characters")
    note(not textual, f"every mission has a title that fits the screen's box and a description ({len(textual)} problems)")
    for line in textual[:12]:
        print("        " + line)

    # places: land provinces, real areas, modifiers that exist
    places = []
    for key, s in scripts.items():
        for mid, m in s["missions"].items():
            text = m["trigger"] + "\n" + m["effect"] + "\n" + (m["highlight"] or "")
            for p in re.findall(r"\b(?:province_id|owns_or_non_sovereign_subject_of|owns|owned_by_province)\s*=\s*(\d+)\b", text) \
                    + re.findall(r"(?m)^\s*(\d+)\s*=\s*\{", text):
                if int(p) not in land:
                    places.append(f"{mid}: province {p} is not a land province")
            for a in re.findall(r"\barea\s*=\s*([a-z0-9_]+)\b", text) + re.findall(r"(?m)^\s*([a-z0-9_]+_area)\s*=\s*\{", text):
                if a not in areas:
                    places.append(f"{mid}: area {a} does not exist")
            for mod in re.findall(r'add_country_modifier\s*=\s*\{\s*name\s*=\s*"?([A-Za-z0-9_]+)"?', m["effect"]):
                if mod not in modifiers:
                    places.append(f"{mid}: modifier {mod} is not defined")
                elif f"{mod}" not in loc:
                    places.append(f"{mid}: modifier {mod} has no name in localisation")
    note(not places, f"every province, area and modifier a mission names exists ({len(places)} do not)")
    for line in places[:12]:
        print("        " + line)

    # territorial missions mark the map
    unmarked = []
    for key, s in scripts.items():
        for mid, m in s["missions"].items():
            asks = re.search(r"owns_or_non_sovereign_subject_of|\bowns\b|type\s*=\s*all", m["trigger"])
            if asks and not m["highlight"]:
                unmarked.append(f"{mid}: asks for provinces but marks none (provinces_to_highlight)")
    note(not unmarked, f"every mission that asks for land marks it on the map ({len(unmarked)} do not)")
    for line in unmarked[:8]:
        print("        " + line)

    # first missions are not already done at the start date
    done = []
    for key, s in scripts.items():
        for tag in s["tags"]:
            for mid, m in s["missions"].items():
                if m["needs"]:
                    continue
                terms = re.findall(r"\b(?:owns_or_non_sovereign_subject_of|owns)\s*=\s*(\d+)\b", m["trigger"])
                holds = re.findall(r"([a-z0-9_]+_area)\s*=\s*\{\s*type\s*=\s*all", m["trigger"])
                if not terms and not holds:
                    continue
                have = all(owners.get(int(p)) == tag for p in terms) and all(
                    all(owners.get(p) == tag for p in areas.get(a, [])) for a in holds)
                other = re.sub(r"\b(owns_or_non_sovereign_subject_of|owns)\s*=\s*\d+|[a-z0-9_]+_area\s*=\s*\{[^{}]*\}", "", m["trigger"])
                if have and not other.strip():
                    done.append(f"{tag}: first mission {mid} is already complete at the start")
    note(not done, f"no first mission is already complete when the game starts ({len(done)} are)")
    for line in done[:8]:
        print("        " + line)
