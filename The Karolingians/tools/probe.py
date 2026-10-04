#!/usr/bin/env python3
"""Parse EU4 base game province history + map areas into a queryable dataset."""
import os, re, json, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

GAME = "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV"
PROV_DIR = os.path.join(GAME, "history", "provinces")
AREA = os.path.join(GAME, "map", "area.txt")
REGION = os.path.join(GAME, "map", "region.txt")


def parse_block_file(path):
    """Return list of (key, [lines]) top-level blocks."""
    text = open(path, encoding="utf-8", errors="replace").read()
    blocks = []
    cur_key, cur = None, []
    depth = 0
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            if cur_key is not None:
                cur.append(line)
            continue
        if depth == 0:
            m = re.match(r"^([A-Za-z0-9_]+)\s*=\s*\{", s)
            if m:
                cur_key, cur = m.group(1), [line]
                depth = 1
                continue
        else:
            cur.append(line)
            depth += s.count("{") - s.count("}")
            if depth == 0:
                blocks.append((cur_key, cur))
                cur_key, cur = None, []
    return blocks


def load_areas():
    areas = {}
    for key, lines in parse_block_file(AREA):
        ids = []
        for ln in lines[1:-1]:
            s = ln.strip()
            # skip "color = { ... }" and any other keyed sub-entry
            if re.match(r"^(color|provinces)\s*=", s):
                continue
            ids += [int(x) for x in re.findall(r"\d+", s)]
        areas[key] = sorted(set(ids))
    return areas


def load_region_areas():
    """region -> list of areas"""
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
    """pid -> dict(owner, controller, cores[], culture, religion, hre, capital, name)"""
    provs = {}
    for fn in os.listdir(PROV_DIR):
        if not fn.endswith(".txt"):
            continue
        path = os.path.join(PROV_DIR, fn)
        m = re.match(r"^(\d+)\s*-\s*(.+)\.txt$", fn)
        if not m:
            continue
        pid, pname = int(m.group(1)), m.group(2)
        text = open(path, encoding="utf-8", errors="replace").read()
        d = {"id": pid, "name": pname, "file": fn, "cores": [],
             "owner": None, "controller": None, "culture": None,
             "religion": None, "hre": False, "capital": False, "sea": False}
        # only the pre-1444.11.11 (undated) block matters for ownership
        for ln in text.splitlines():
            s = ln.strip()
            if re.match(r"^\d+\.\d+\.\d+\s*=", s):
                break  # dated block -> stop, start state is above
            if s.startswith("#") or not s:
                continue
            if m2 := re.match(r"^owner\s*=\s*([A-Z0-9_]+)", s):
                d["owner"] = m2.group(1)
            elif m2 := re.match(r"^controller\s*=\s*([A-Z0-9_]+)", s):
                d["controller"] = m2.group(1)
            elif m2 := re.match(r"^add_core\s*=\s*([A-Z0-9_]+)", s):
                d["cores"].append(m2.group(1))
            elif m2 := re.match(r"^culture\s*=\s*([a-z0-9_]+)", s):
                d["culture"] = m2.group(1)
            elif m2 := re.match(r"^religion\s*=\s*([a-z0-9_]+)", s):
                d["religion"] = m2.group(1)
            elif m2 := re.match(r"^hre\s*=\s*(\w+)", s):
                d["hre"] = m2.group(1) == "yes"
            elif m2 := re.match(r"^is_city\s*=\s*(\w+)", s):
                d["is_city"] = m2.group(1) == "yes"
            elif m2 := re.match(r"^capital\s*=", s):
                d["capital"] = True
        provs[pid] = d
    return provs


def main():
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

    data = {"provs": provs, "areas": areas, "area_of": area_of,
            "region_of_area": region_of_area}
    with open(str(CACHE / "provdata.json"), "w") as f:
        json.dump(data, f)

    print(f"provinces: {len(provs)}  areas: {len(areas)}")
    print(f"hre=yes: {sum(1 for p in provs.values() if p['hre'])}")

    # owner tag -> provinces, only HRE + nearby
    hre_owners = defaultdict(list)
    for p in provs.values():
        if p["hre"]:
            hre_owners[p["owner"]].append(p["id"])
    print(f"\ndistinct owners inside HRE boundary: {len(hre_owners)}")
    for t, ids in sorted(hre_owners.items(), key=lambda x: -len(x[1]))[:40]:
        print(f"  {t:5} {len(ids):3}")


if __name__ == "__main__":
    main()
