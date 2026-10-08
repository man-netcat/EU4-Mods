import os, re, glob, json

GAME = "/home/rick/Paradox/Games/Europa Universalis IV"
PROV = os.path.join(GAME, "history/provinces")

# continents from continent.txt
cont = {}
cur = None
with open(os.path.join(GAME, "map/continent.txt"), encoding="utf-8", errors="replace") as fh:
    for line in fh:
        m = re.match(r"^\s*(\w+)\s*=\s*\{", line)
        if m:
            cur = m.group(1); cont.setdefault(cur, []); continue
        if cur:
            for num in re.findall(r"\b\d+\b", line):
                cont[cur].append(int(num))
na = set(cont.get("north_america", []))
sa = set(cont.get("south_america", []))
amer_ids = na | sa

provs = {}
for f in glob.glob(os.path.join(PROV, "*.txt")):
    base = os.path.basename(f)
    m = re.match(r"^(\d+)\s*-\s*(.+)\.txt$", base)
    if not m: continue
    pid, name = int(m.group(1)), m.group(2).strip()
    if pid not in amer_ids: continue
    with open(f, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    def top(field):
        mm = re.search(r"(?m)^%s\s*=\s*(\S+)" % field, txt)
        return mm.group(1) if mm else None
    provs[pid] = {
        "name": name, "owner": top("owner"), "culture": top("culture"),
        "religion": top("religion"),
        "is_city": bool(re.search(r"(?m)^is_city\s*=\s*yes", txt)),
        "continent": "north" if pid in na else "south",
    }

# areas restricted to america
areas, cur = {}, None
with open(os.path.join(GAME, "map/area.txt"), encoding="utf-8", errors="replace") as fh:
    for line in fh:
        m = re.match(r"^\s*(\w+)\s*=\s*\{", line)
        if m:
            cur = m.group(1); areas.setdefault(cur, []); continue
        if cur:
            for num in re.findall(r"\b\d+\b", line):
                areas[cur].append(int(num))
amer_areas = {a: sorted(set(areas[a]) & amer_ids) for a in areas if set(areas[a]) & amer_ids}
amer_areas = {a: v for a, v in amer_areas.items() if v}

owners = {}
unowned = []
for pid in sorted(amer_ids):
    p = provs.get(pid)
    if not p: 
        continue
    if p["owner"]:
        owners.setdefault(p["owner"], []).append(pid)
    else:
        unowned.append(pid)
for t in owners: owners[t] = sorted(owners[t])

print("NA provinces:", len(na & set(provs)), "| SA:", len(sa & set(provs)), "| total:", len(provs))
print("owned at start:", sum(len(v) for v in owners.values()), "| unowned:", len(unowned))
print("vanilla native owners:", len(owners))

json.dump({"amer_ids": sorted(amer_ids), "na": sorted(na & set(provs)), "sa": sorted(sa & set(provs)),
           "areas": amer_areas, "provs": {str(k): provs[k] for k in sorted(provs)}},
          open(f"{os.path.dirname(os.path.abspath(__file__))}/america.json", "w"))
print("wrote america.json | areas:", len(amer_areas))
