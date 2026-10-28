"""Where the province mapping is least certain, region by region, and what could settle it.

    python3 tools/audit_regions.py europe              # summary and the low-confidence provinces of Europe
    python3 tools/audit_regions.py france_region ...   # the same for named EU4 regions, with each area's free EU5 provinces

Low confidence: a province matched only to a whole EU5 area (`area-node`, `area-fallback`), one that shares its pool of EU5
locations with others, or none at all. For those, the EU5 provinces of the EU4 area that no certain province claims are
listed with their owners: the hand aliases in data/aliases.json (`pid: [EU5 node or location, ...]`) are written from this.
"""
import collections
import json
import os
import re
import sys

from loc2prov import L5, eu4_geo, eu4_provinces, eu5_tree, land_provinces, norm, yml
from paths import MOD

EUROPE = ("scandinavia_region british_isles_region france_region iberia_region italy_region low_countries_region "
          "north_german_region south_german_region poland_region baltic_region russia_region ruthenia_region "
          "carpathia_region balkan_region crimea_region").split()


def owners_of(path_text):
    out = {}
    for f in (MOD / "history/provinces").iterdir():
        top = re.split(r"(?m)^\d{3,4}\.\d+\.\d+\s*=", f.read_text(encoding="latin-1"))[0]
        m = re.search(r"(?m)^owner = (\w+)", top)
        out[int(re.match(r"\d+", f.name)[0])] = m[1] if m else None
    return out


def main(regions):
    from eu5setup import ownership
    from popdata import location_pops
    import eu5info
    nodes, level, locs, path = eu5_tree()
    o, _c, _co = ownership()
    lp = location_pops()
    area, reg = eu4_geo()
    names, land = eu4_provinces(), land_provinces()
    m = json.load(open(MOD / "tools/data/loc2prov.json"))
    own = owners_of(None)
    pools = collections.Counter(tuple(sorted(v["locations"])) for v in m.values())

    def flagged(p):
        v = m.get(str(p))
        return not v or v["tier"] in ("area-node", "area-fallback") or pools[tuple(sorted(v["locations"]))] > 1

    def owner_mix(ls):
        c = collections.Counter()
        for l in ls:
            c[o.get(l)] += lp.get(l, {"pop": 0})["pop"] or 0.01
        return [(eu5info.display(t) if t else None, round(w)) for t, w in c.most_common(2)]

    claimed = set()
    for p, v in m.items():
        if not flagged(int(p)):
            claimed |= set(v["locations"])
    tiers = collections.Counter()
    todo = collections.defaultdict(list)
    for p in sorted(land):
        if reg.get(area.get(p)) in regions:
            tiers["flagged" if flagged(p) else "certain"] += 1
            if flagged(p):
                todo[area[p]].append(p)
    print(dict(tiers))
    for a, ps in todo.items():
        print(f"\n## {a}: " + ", ".join(f"{p} {names[p][0]} ({own.get(p)})" for p in ps))
        if len(sys.argv) > 2 or sys.argv[1] != "europe":
            votes = collections.Counter(n for p in area if area[p] == a and not flagged(p) and str(p) in m
                                        for l in m[str(p)]["locations"] for n in path[l] if n.endswith("_area"))
            free = collections.defaultdict(list)
            for ar in [x for x, _ in votes.most_common(3)]:
                for l in nodes[ar]:
                    if l not in claimed:
                        prov = next((n for n in path[l] if n.endswith("_province")), l)
                        free[prov].append(l)
            for prov, ls in sorted(free.items()):
                print(f"   free: {prov} ({len(ls)}) {owner_mix(ls)}")


if __name__ == "__main__":
    main(set(EUROPE) if sys.argv[1] == "europe" else set(sys.argv[1:]))
