#!/usr/bin/env python3
"""The map's province facts: vanilla province files, sea, lake and waste ids, areas, regions."""

import json
import os
import re
from steps.layout import GAME, PROVDATA, VANILLA_HISTORY, VANILLA_PDIR
from steps.parsing import parse, parse_block_file


_PROVDATA = None


def _pd():
    global _PROVDATA
    if _PROVDATA is None:
        ensure()
        _PROVDATA = json.load(open(str(PROVDATA)))
    return _PROVDATA


_VANILLA_PROV_FILES: dict = {}


def vanilla_prov_file(pid):
    # pid -> vanilla history/provinces path, via one directory scan: the
    # per-pid listdir this replaces was the slowest loop in the province step.
    if not _VANILLA_PROV_FILES:
        for fn in os.listdir(VANILLA_PDIR):
            m = re.match(r"^(\d+)\s*-.*\.txt$", fn)
            if m:
                _VANILLA_PROV_FILES.setdefault(int(m.group(1)), fn)
    fn = _VANILLA_PROV_FILES.get(pid)
    return os.path.join(VANILLA_PDIR, fn) if fn else None


def vanilla_prov_ids():
    # Every province id with a vanilla history file.
    if not _VANILLA_PROV_FILES:
        vanilla_prov_file(0)
    return sorted(_VANILLA_PROV_FILES)


def _vanilla_id_set(path, section, flags=0):
    # Province ids from a vanilla map section (sea_starts, impassable,
    # lakes): grey/water land we never own, only restore visibility for.
    txt = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(section + r"\s*=\s*\{(.*?)\}", txt, re.S | flags)
    return sorted({int(x) for x in re.findall(r"\d+", m.group(1))})


def sea_ids():
    # The engine's own sea list: every water province whose visibility we
    # restore verbatim from vanilla (sea files carry only discovered_by).
    return _vanilla_id_set(os.path.join(GAME, "map", "default.map"), r"sea_starts")


def waste_ids():
    # The engine's own wasteland list: every province in the impassable
    # section of vanilla map/climate.txt renders grey and always-visible.
    # We ship no map files, so the set is vanilla's; like sea tiles these
    # files carry only discovered_by and keep their tech-group lines.
    return _vanilla_id_set(os.path.join(GAME, "map", "climate.txt"), r"impassable")


def lake_ids():
    # The engine's own lake list from vanilla map/default.map: water that
    # is neither sea nor land. Same treatment as sea and wasteland.
    return _vanilla_id_set(os.path.join(GAME, "map", "default.map"), r"^lakes", re.M)


AREA = os.path.join(GAME, "map", "area.txt")

REGION = os.path.join(GAME, "map", "region.txt")


def vanilla_is_newer() -> bool:
    if not PROVDATA.exists():
        return True
    try:
        return (
            max(p.stat().st_mtime for p in VANILLA_HISTORY.rglob("*.txt"))
            > PROVDATA.stat().st_mtime
        )
    except OSError:
        return False


def load_areas():
    areas = {}
    for key, lines in parse_block_file(AREA):
        ids = []
        for ln in lines[1:-1]:
            s = ln.strip()

            if re.match(r"^(color|provinces)\s*=", s):
                continue
            ids += [int(x) for x in re.findall(r"\d+", s)]
        areas[key] = sorted(set(ids))
    return areas


def load_region_areas():
    regions = {}
    for key, lines in parse_block_file(REGION):
        areas = []
        for ln in lines[1:-1]:
            m = re.match(r"^\s*([a-z0-9_]+)\s*$", ln)
            if m:
                areas.append(m.group(1))
        regions[key] = areas
    return regions


def load_provinces():
    provs = {}
    for fn in os.listdir(VANILLA_PDIR):
        if not fn.endswith(".txt"):
            continue
        path = os.path.join(VANILLA_PDIR, fn)
        m = re.match(r"^(\d+)\s*-\s*(.+)\.txt$", fn)
        if not m:
            continue
        pid, pname = int(m.group(1)), m.group(2)
        scalars, cores, _ = parse(path)

        def tok(key, cls):
            # First token in the old character class only: vanilla parks
            # two keys on one line (culture = ge discovered_by = ...) and
            # quotes some values (religion = "hinduism") - neither counted.
            v = scalars.get(key)
            if not v:
                return None
            first = v.split()[0]
            return first if re.fullmatch(cls, first) else None

        provs[pid] = {
            "id": pid,
            "name": pname,
            "file": fn,
            "cores": [
                c.split()[0]
                for c in cores
                if re.fullmatch(r"[A-Z0-9_]+", c.split()[0])
            ],
            "owner": tok("owner", r"[A-Z0-9_]+"),
            "controller": tok("controller", r"[A-Z0-9_]+"),
            "culture": tok("culture", r"[a-z0-9_]+"),
            "religion": tok("religion", r"[a-z0-9_]+"),
            "capital": "capital" in scalars,
            "is_city": scalars.get("is_city") == "yes",
            "sea": False,
        }
    return provs


def step_probe():
    areas = load_areas()
    regions = load_region_areas()
    provs = load_provinces()
    area_of = {}
    for a, ids in areas.items():
        for p in ids:
            area_of[p] = a
    region_of_area = {}
    for r, als in regions.items():
        for a in als:
            region_of_area[a] = r

    data = {
        "provs": provs,
        "areas": areas,
        "area_of": area_of,
        "region_of_area": region_of_area,
    }
    os.makedirs(os.path.dirname(str(PROVDATA)), exist_ok=True)
    with open(str(PROVDATA), "w") as f:
        json.dump(data, f)

    print(f"provinces: {len(provs)}  areas: {len(areas)}")


def ensure():
    """Probe the base game's province history, unless the cache is newer than the game's files."""
    if vanilla_is_newer():
        print("\n\033[1m==> probe vanilla province history\033[0m", flush=True)
        step_probe()
    else:
        print("\n\033[1m==> probe\033[0m\n    cache is current, skipping")
