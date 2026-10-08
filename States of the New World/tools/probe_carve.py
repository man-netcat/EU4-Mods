import json, os, os, re, sys, importlib.util

BASE = os.path.dirname(os.path.abspath(__file__))
GAME_POSITIONS = "/home/rick/Paradox/Games/Europa Universalis IV/map/positions.txt"

with open(f"{BASE}/america.json") as f:
    AM = json.load(f)
PROVS = {str(k): v for k, v in AM["provs"].items()}
AREAS = AM["areas"]
AMER_IDS = set(str(x) for x in AM["amer_ids"])

spec = importlib.util.spec_from_file_location("design", f"{BASE}/design.py")
design = importlib.util.module_from_spec(spec)
sys.modules["design"] = design
spec.loader.exec_module(design)

with open(f"{BASE}/tribes.json") as f:
    TRIBES = json.load(f)
TRIBE_PROVS = {str(t["prov"]) for t in TRIBES.values()}

RESTORED = {
    "AZT": [852, 853, 2645, 4570, 4571], "CCQ": [794, 2837, 2838],
    "CHM": [812, 816, 2821, 2822, 2826], "CHT": [839, 2637], "CJA": [813, 2824],
    "CLA": [802, 804, 2947], "CLM": [2643, 2657, 4579, 4580], "CNP": [845, 2650],
    "COC": [846, 2652, 4591], "COI": [2646, 4581], "CRA": [795, 2835, 2941, 2942],
    "CTM": [843, 2634, 4589], "CYA": [2823, 2943], "HJA": [814, 2825, 2827],
    "HST": [858, 2641], "ICM": [809], "ITZ": [842, 4588, 4594],
    "KAQ": [2636, 2653], "KER": [4632], "KIC": [841, 4587], "LAC": [2635, 4585, 4586],
    "MAT": [2623, 2626, 4572], "MCA": [825, 832, 4603], "MIX": [847, 2629],
    "OTO": [2642, 4573, 4641], "PCJ": [797, 2831, 2940, 2946], "TAR": [2622, 2624, 4574, 4575],
    "TEO": [2628, 4582], "TLA": [849, 851, 2627, 2648], "TLX": [850, 2644, 4583],
    "TON": [2617, 2621, 4640], "TOT": [848, 2647, 4598], "WKA": [810, 811],
    "XIU": [2633, 2651, 4590], "YOK": [2630, 2631, 2632],
}
REST_PROVS = {str(p) for provs in RESTORED.values() for p in provs}
assert len(REST_PROVS) == 99, len(REST_PROVS)

GUTTED = [
    ("MEX", ["mexico_area", "puebla_area", "guerrero_area", "guanajuato_area", "zacatecas_area", "gran_chichimeca_area"]),
    ("MHC", ["michoacan_area", "tierra_caliente_area"]),
    ("VRC", ["huasteca_area", "eastern_mexico_area"]),
    ("MAY", ["yucatan_area", "east_yucatan_area", "campeche_area"]),
    ("CXA", ["chiapas_area"]),
    ("GTM", ["guatemala_area", "guatemala_lowlands_area"]),
    ("COL", ["bogota_area", "cordillera_occidental_area", "popayan_area", "colombian_amazonas_area", "coquivacoa_area", "western_llanos"]),
    ("PEU", ["peruan_coast", "huanuco_area", "cajamarca_area", "chimor_area", "ucayali_area"]),
    ("BOL", ["antisuyu_area", "potosi_area", "upper_peru", "moxos_area", "beni_area"]),
]
gut_areas = {a for _t, areas in GUTTED for a in areas}
assert len(gut_areas) == 32, len(gut_areas)

# realms surviving (mirrors gen_mod with REST carve)
assigned = {}
carve_hits = {}
realm_ids = {}
for r in design.REALMS:
    ids = set()
    for a in r.get("areas", []):
        ids |= {str(x) for x in AREAS.get(a, []) if str(x) in PROVS}
    ids |= {str(x) for x in r.get("extra", [])}
    carve = ids & REST_PROVS
    if carve:
        carve_hits[r["tag"]] = sorted(int(x) for x in carve)
    ids -= TRIBE_PROVS | REST_PROVS
    assert r["capital"] and str(r["capital"]) in ids, f"capital {r['capital']} lost in {r['tag']}"
    for i in ids:
        assert i not in assigned, f"double {i}"
        assigned[i] = r["tag"]
    realm_ids[r["tag"]] = ids

print(f"realms: {len(design.REALMS)}  assigned after carve: {len(assigned)}")
print(f"realms losing provs to RESTORE carve: {len(carve_hits)}")
for t in sorted(carve_hits):
    print(f"  {t}: -{carve_hits[t]}")

# orphans from gutted areas
orphans = {str(x) for a in gut_areas for x in AREAS.get(a, []) if str(x) in PROVS}
rest_in_gut = orphans & REST_PROVS
tribe_in_gut = orphans & TRIBE_PROVS
orphans -= REST_PROVS | TRIBE_PROVS
print(f"\ngutted-area land provs: {len(orphans) + len(rest_in_gut) + len(tribe_in_gut)}")
print(f"  restored (vanilla keeps): {len(rest_in_gut)}")
print(f"  tribes (keep OPM): {len(tribe_in_gut)}")
print(f"  ORPHANS to redistribute: {len(orphans)}")

# positions
data = open(GAME_POSITIONS, encoding="latin-1").read()
pos = {}
for m in re.finditer(r"(\d+)\s*=\s*\{\s*position\s*=\s*\{\s*(-?[\d.]+)\s+(-?[\d.]+)", data):
    pos[m.group(1)] = (float(m.group(2)), float(m.group(3)))
missing_pos = sorted(orphans - set(pos))
print(f"orphans missing positions: {missing_pos}")

# nearest-realm assignment (deterministic: realm order, strict <)
def dist(p1, p2):
    return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2

def nearest(o):
    op = pos[o]
    best, bd = None, None
    for tag in sorted(realm_ids):
        b = min(dist(op, pos[p]) for p in realm_ids[tag] if p in pos)
        if bd is None or b < bd:
            best, bd = tag, b
    return best

from collections import defaultdict
per_realm = defaultdict(list)
for o in sorted(orphans):
    t = nearest(o)
    per_realm[t].append(int(o))
    assert o not in assigned, f"orphan {o} already assigned to {assigned[o]}"
    assigned[o] = t

print(f"\norphans after redistribution: {len(assigned) - (len(design.REALMS) * 0)} unassigned -> {len(orphans)}")
for t in sorted(per_realm):
    print(f"  {t}: +{sorted(per_realm[t])}")