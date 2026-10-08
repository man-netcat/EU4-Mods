import os, re, glob

GAME = "/home/rick/Paradox/Games/Europa Universalis IV"
PROV = os.path.join(GAME, "history/provinces")
files = sorted(glob.glob(os.path.join(PROV, "*.txt")))

# Parse province files
provs = {}  # id -> {"name":, "owner":, "culture":, "religion":, "is_city":}
for f in files:
    base = os.path.basename(f)
    m = re.match(r"^(\d+)\s*-\s*(.+)\.txt$", base)
    if not m:
        continue
    pid = int(m.group(1))
    name = m.group(2).strip()
    with open(f, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    owner = re.search(r"^\s*owner\s*=\s*(\S+)", txt, re.M)
    culture = re.search(r"^\s*culture\s*=\s*(\S+)", txt, re.M)
    religion = re.search(r"^\s*religion\s*=\s*(\S+)", txt, re.M)
    is_city = re.search(r"^\s*is_city\s*=\s*yes", txt, re.M)
    provs[pid] = {
        "name": name, "owner": owner.group(1) if owner else None,
        "culture": culture.group(1) if culture else None,
        "religion": religion.group(1) if religion else None,
        "is_city": bool(is_city),
    }

# America ID ranges from continent.txt
AMERICA_IDS = set()
for lo, hi in [(835,1011),(1104,1105),(1804,1814),(2003,2023),(2476,2672),
               (4570,4650),(4871,4933),(481,501),(1881,1881),
               (741,834),(2803,2947),(4596,4617)]:
    AMERICA_IDS.update(range(lo, hi+1))

if provs:  # merged with ranges; fill in ids not in ranges but in files named with american tells
    pass

# area.txt: area -> [province ids]
areas = {}
cur = None
with open(os.path.join(GAME, "map/area.txt"), encoding="utf-8", errors="replace") as fh:
    for line in fh:
        m = re.match(r"^\s*(\w+)\s*=\s*\{", line)
        if m:
            cur = m.group(1)
            areas[cur] = []
            continue
        if cur:
            for num in re.findall(r"\b\d+\b", line):
                areas[cur].append(int(num))
    for a in areas:
        areas[a] = sorted(set(areas[a]))

# America areas = areas touching America
amer_areas = {}
for a, ids in areas.items():
    hit = [i for i in ids if i in AMERICA_IDS]
    if hit:
        amer_areas[a] = hit

# Owners in america
owners = {}
for pid in sorted(AMERICA_IDS):
    p = provs.get(pid)
    if p and p["owner"]:
        owners.setdefault(p["owner"], []).append((pid, p["name"]))

print("=== AMERICA AREAS (%d) ===" % len(amer_areas))
for a in sorted(amer_areas):
    print("%-32s %s" % (a, amer_areas[a]))

print("\n=== OWNERS IN AMERICA ===")
for tag in sorted(owners):
    print("%s (%d): %s" % (tag, len(owners[tag]), [n for _, n in owners[tag]][:8]))

print("\nTotal american provinces with files:", len([p for p in provs if p in AMERICA_IDS]))