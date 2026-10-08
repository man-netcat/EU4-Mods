#!/usr/bin/env python3
"""Scan vanilla native tags -> 1444 province, monarchs, federation blocks.
Also computes how the carve hits existing REALMS (provinces lost, dead realms)."""
import json, os, os, re, importlib.util, sys

BASE = os.path.dirname(os.path.abspath(__file__))
GAME = "/home/rick/Paradox/Games/Europa Universalis IV"
HIST_CNT = f"{GAME}/history/countries"
HIST_PROV = f"{GAME}/history/provinces"

with open(f"{BASE}/america.json") as f:
    AM = json.load(f)
PROVS = {str(k): v for k, v in AM["provs"].items()}
AREAS = AM["areas"]
AMER_IDS = set(str(x) for x in AM["amer_ids"])

spec = importlib.util.spec_from_file_location("design", f"{BASE}/design.py")
design = importlib.util.module_from_spec(spec)
sys.modules["design"] = design
spec.loader.exec_module(design)
REALMS = [r for r in design.REALMS if not r.get("skip")]

def first_top(dates, want):
    dates = sorted(dates)
    for d in dates:
        if d <= want:
            return d
    return dates[0] if dates else None

def parse_country_file(path):
    """Return dict with capital, monarch candidate (<=1444.11.11), federation block."""
    with open(path, encoding="utf-8", errors="replace") as f:
        txt = f.read()
    out = {}
    # capital: top-level or first dated block
    m = re.search(r"(?m)^capital\s*=\s*(\d+)", txt)
    if m:
        out["capital"] = m.group(1)
    # federation block
    m = re.search(r"(?s)federation\s*=\s*\{(.*?)\}", txt)
    if m:
        mem = re.findall(r"\b([A-Z]{3})\b", m.group(1))
        nm = re.search(r'name\s*=\s*"?([^"\s}]+)"?', m.group(1))
        out["federation"] = {"name": nm.group(1) if nm else "?", "members": mem}
    # monarch blocks with dates; collect (date, block)
    mon_blocks = []
    for dm in re.finditer(r"(?s)(\d+\.\d+\.\d+)\s*=\s*\{\s*monarch\s*=\s*\{(.*?)\}\s*\}", txt):
        date = dm.group(1).strip()
        body = dm.group(2)
        name = re.search(r'name\s*=\s*"?([^"\n]+)"?', body)
        dyn = re.search(r'dynasty\s*=\s*"?([^"\n]+)"?', body)
        adm = re.search(r'adm\s*=\s*(\d+)', body)
        dip = re.search(r'dip\s*=\s*(\d+)', body)
        mil = re.search(r'mil\s*=\s*(\d+)', body)
        birth = re.search(r'birth_date\s*=\s*([\d.]+)', body)
        mon_blocks.append(dict(date=date,
                               name=name.group(1).strip('" ') if name else None,
                               dynasty=dyn.group(1).strip('" ') if dyn else None,
                               adm=int(adm.group(1)) if adm else 0,
                               dip=int(dip.group(1)) if dip else 0,
                               mil=int(mil.group(1)) if mil else 0,
                               birth=birth.group(1) if birth else None))
    out["monarchs"] = mon_blocks
    return out

def parse_date(d):
    y, mo, dy = (int(x) for x in d.split("."))
    return y * 10000 + mo * 100 + dy

def prov_file_for(pid):
    for f in os.listdir(HIST_PROV):
        m = re.match(rf"^{pid}\b", f)
        if m:
            return f
    return None

def prov_top_owner(pid):
    fn = prov_file_for(pid)
    if not fn:
        return None, None
    with open(f"{HIST_PROV}/{fn}", encoding="utf-8", errors="replace") as f:
        txt = f.read()
    m = re.search(r"(?m)^owner\s*=\s*([A-Z]{3})", txt)
    tg = re.search(r"(?m)^trade_goods\s*=\s*(\w+)", txt)
    return (m.group(1) if m else None), (tg.group(1) if tg else None)

# ---------- find native tags ----------
natives = {}
for fn in os.listdir(HIST_CNT):
    m = re.match(r"^([A-Z]{3}) - ", fn)
    if not m:
        continue
    tag = m.group(1)
    with open(f"{HIST_CNT}/{fn}", encoding="utf-8", errors="replace") as f:
        txt = f.read()
    if re.search(r"(?m)^government\s*=\s*native\b", txt):
        natives.setdefault(tag, []).append(fn)

print(f"native tags found: {len(natives)}")
# ---------- ownership at 1444 (top-level owner in province file) ----------
tribes = {}
multi = {}
for tag, files in sorted(natives.items()):
    provs = []
    for fn in os.listdir(HIST_PROV):
        with open(f"{HIST_PROV}/{fn}", encoding="utf-8", errors="replace") as f:
            txt = f.read()
        m = re.search(r"(?m)^owner\s*=\s*" + tag + r"\b", txt)
        if m:
            pid = re.match(r"^(\d+)", fn).group(1)
            provs.append(pid)
    provs = sorted(provs, key=int)
    am = [p for p in provs if p in AMER_IDS]
    if len(am) == 1:
        tribes[tag] = am[0]
    elif len(am) > 1:
        multi[tag] = am

print(f"native tags owning exactly 1 AMER province: {len(tribes)}")
print(f"native tags owning >1 AMER prov (should be none): {multi}")
no_amer = sorted(set(natives) - set(tribes) - set(multi))
print(f"native tags owning no AMER province: {len(no_amer)} -> {no_amer}")

# ---------- details per tribe ----------
data = {}
for tag, pid in sorted(tribes.items()):
    fn = natives[tag][0]
    c = parse_country_file(f"{HIST_CNT}/{fn}")
    owner, tgood = prov_top_owner(pid)
    assert owner == tag, f"{tag}: province {pid} top owner {owner}"
    pv = PROVS.get(pid, {})
    mondate = None
    mon = None
    want = parse_date("1444.11.11")
    for mb in c["monarchs"]:
        d = parse_date(mb["date"])
        if d <= want:
            if mon is None or d > parse_date(mondate):
                mondate, mon = mb["date"], mb
    data[tag] = dict(prov=pid, provname=pv.get("name", pid),
                     culture=pv.get("culture"), religion=pv.get("religion"),
                     trade_good=tgood, capital=c.get("capital", pid),
                     monarch=mon, federation=c.get("federation"))

with open(f"{BASE}/tribes.json", "w") as f:
    json.dump(data, f, indent=1)
print(f"saved {BASE}/tribes.json")

# federation blocks found (all native tags)
print("\n=== federation blocks among all natives ===")
for tag, pid in sorted(tribes.items()):
    fb = data[tag]["federation"]
    if fb:
        print(f"  {tag} (prov {pid}): name={fb['name']} members={fb['members']}")
for tag in no_amer:
    c = parse_country_file(f"{HIST_CNT}/{natives[tag][0]}")
    if c.get("federation"):
        print(f"  {tag} (no prov): name={c['federation']['name']} members={c['federation']['members']}")

# ---------- carve impact on REALMS ----------
print("\n=== carve impact (realm provinces lost to tribes) ===")
native_provs = {v["prov"] for v in data.values()}
seen_area = {}
dead = []
for r in REALMS:
    ids = []
    for a in r.get("areas", []):
        ids += [str(x) for x in AREAS.get(a, []) if str(x) in PROVS]
    ids += [str(x) for x in r.get("extra", [])]
    ids = set(ids)
    lost = ids & native_provs
    remain = ids - native_provs
    cap_lost = str(r["capital"]) in lost
    status = ""
    if not remain:
        status = "  ** DEAD (all provinces carved) **"
        dead.append(r["tag"])
    elif cap_lost:
        status = "  capital carved -> needs new capital"
    if lost or status:
        print(f"  {r['tag']:5} lost {len(lost):2} provs {sorted(lost, key=int)}  remain {len(remain)}{status}")
print(f"\nrealms that die: {dead}")

# also check: any tribe province NOT in any realm's territory?
all_realm = set()
for r in REALMS:
    ids = []
    for a in r.get("areas", []):
        ids += [str(x) for x in AREAS.get(a, []) if str(x) in PROVS]
    ids += [str(x) for x in r.get("extra", [])]
    all_realm |= set(ids)
no_owner = native_provs - all_realm
print(f"tribe provinces outside all realm areas: {sorted(no_owner, key=int) if no_owner else 'none'}")

# ---------- federation tag country files (for formable history) ----------
print("\n=== federation tag vanilla files (head) ===")
for tag in ("IRO", "HUR", "ILL", "CRE", "PUE", "SHA"):
    fn = natives.get(tag, [None])[0]
    if not fn:
        print(f"  {tag}: NO native file?!")
        continue
    with open(f"{HIST_CNT}/{fn}", encoding="utf-8", errors="replace") as f:
        txt = f.read()
    lines = txt.splitlines()
    head = [l for l in lines if not l.startswith("#") and l.strip()][:25]
    print(f"  --- {fn} ---")
    for l in head:
        print(f"    {l}")
    print()