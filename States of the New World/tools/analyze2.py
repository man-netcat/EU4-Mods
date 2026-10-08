import os, re, glob

GAME = "/home/rick/Paradox/Games/Europa Universalis IV"
PROV = os.path.join(GAME, "history/provinces")

provs = {}
for f in glob.glob(os.path.join(PROV, "*.txt")):
    base = os.path.basename(f)
    m = re.match(r"^(\d+)\s*-\s*(.+)\.txt$", base)
    if not m: continue
    pid, name = int(m.group(1)), m.group(2).strip()
    with open(f, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    # TOP-LEVEL fields only (no leading whitespace = outside dated blocks)
    def top(field):
        mm = re.search(r"(?m)^%s\s*=\s*(\S+)" % field, txt)
        return mm.group(1) if mm else None
    provs[pid] = {
        "name": name, "owner": top("owner"), "culture": top("culture"),
        "religion": top("religion"),
        "is_city": bool(re.search(r"(?m)^is_city\s*=\s*yes", txt)),
        "capital": bool(re.search(r'(?m)^capital\s*=', txt)),
    }

# areas
areas, cur = {}, None
with open(os.path.join(GAME, "map/area.txt"), encoding="utf-8", errors="replace") as fh:
    for line in fh:
        m = re.match(r"^\s*(\w+)\s*=\s*\{", line)
        if m:
            cur = m.group(1); areas[cur] = []; continue
        if cur:
            for num in re.findall(r"\b\d+\b", line):
                areas[cur].append(int(num))
    for a in areas: areas[a] = sorted(set(areas[a]))

# American areas = those whose names suggest America OR containing american-ish provinces
NAMED = re.compile(r"(california|texas|florida|carolina|mexico|yucatan|yucat|brazil|amazon|andes|peru|chile|patagonia|"
                   r"colombia|venezuela|panama|nicaragua|honduras|guatemala|cuba|haiti|caribbean|antilles|quebec|canada|"
                   r"ontario|hudson|labrador|newfoundland|acadia|maine|massachusetts|connecticut|virginia|pennsyl|ohio|"
                   r"kentucky|tennessee|alabama|georgia|mississippi|louisiana|dakota|iowa|kansas|mississip|illinois|"
                   r"michigan|wisconsin|minnessota|mnnesota|minnesota|arkansas|ozarks|colorado|arizona|chihuahua|coahuila|"
                   r"sonora|sinaloa|durango|zacatecas|guanaj|quir|queret|michoacan|oaxaca|veracruz|tabasco|chiapas|puebla|"
                   r"guerrero|jalisco|nayarit|colima|tamaulipas|sinaloa|asuncion|paraguay|uruguay|buenos|tucuman|mendoza|"
                   r"cuyo|cordoba|mato|goias|minas|bahia|pernambuco|ceara|maranhao|paraiba|serge|espirito|rio_de|saopao|"
                   r"sao_paolo|pampa|pampas|gran_chaco|chaco|guarani|andean|antisuyu|kuntisuyu|chinchay|colla|charqa|"
                   r"llano|llanos|orinoco|cumana|guyana|suriname|essequibo|appalachia|piedmont_north|miami|dakota|"
                   r"lakota|sioux|cheyenne|comanche|navajo|pueblo|hopi|zuni|apache|seminole|creek|choctaw|chickasaw|"
                   r"iroquo|huron|algon|ojibwa|potawatomi|ottawa|tuscarora|cherokee|powhatan|shoshone|ute|paiute|"
                   r"nebraska|oklahoma|tejas|pecos|rгande|saskatchewan|assiniboia|prairies|athabasca|yukon)")
amer_area_names = [a for a in areas if NAMED.search(a) or any(p in areas[a] for p in range(4700, 4940))]
# force include from continent list
CONT_RANGES = [(835,1011),(1104,1105),(1804,1814),(2003,2023),(2476,2672),(4570,4650),(4871,4933),(481,501),(1881,1881),(741,834),(2803,2947),(4596,4617)]
cont_ids = set()
for lo,hi in CONT_RANGES: cont_ids.update(range(lo,hi+1))
amer_area_names = sorted({a for a in areas if set(areas[a]) & cont_ids})
amer_ids = set()
for a in amer_area_names: amer_ids.update(areas[a])

owners = {}
for pid in sorted(amer_ids):
    p = provs.get(pid)
    if p and p["owner"]:
        owners.setdefault(p["owner"], []).append((pid, p["name"]))

print("American provinces:", len(amer_ids), "| areas:", len(amer_area_names))
print("\n=== TOP-LEVEL OWNERS (1444 start) ===")
for tag in sorted(owners):
    print("%-5s %2d: %s" % (tag, len(owners[tag]), ", ".join(n for _, n in owners[tag][:12])))

import json
json.dump({"amer_ids": sorted(amer_ids), "areas": {a: areas[a] for a in amer_area_names},
           "provs": {str(k): provs[k] for k in provs if k in amer_ids}},
          open(f"{os.path.dirname(os.path.abspath(__file__))}/america.json","w"))
print("\nwrote america.json")
