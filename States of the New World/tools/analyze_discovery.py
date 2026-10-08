#!/usr/bin/env python3
"""Survey vanilla EU4 discovery mechanics for the American provinces.

Reads every vanilla history file for the mod's American prov ids and reports:
  - how many carry discovered_by
  - the undated discovered_by tags per file (top-level, no date)
  - dated discovered_by blocks (date + tags)
  - whether tech-group discovered_by appears on American files
Also scans the vanilla history/countries files of every mod tag for
undated/dated `discovered = { ... }` blocks.
"""
import json, os, os, re
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
GAME_HIST_PROV = "/home/rick/Paradox/Games/Europa Universalis IV/history/provinces"
GAME_HIST_CNT = "/home/rick/Paradox/Games/Europa Universalis IV/history/countries"

AM = json.load(open(f"{BASE}/america.json"))
AMER_IDS = {str(x) for x in AM["amer_ids"]}

TOKEN = re.compile(r"\b[A-Z]{3}\b")

prov_files = {}
for f in os.listdir(GAME_HIST_PROV):
    m = re.match(r"^(\d+)", f)
    if m:
        prov_files.setdefault(m.group(1), f)

# ---- province files ----
undated = defaultdict(list)      # pid -> [tags]
dated = defaultdict(list)        # pid -> [(date, tags)]
techgroups = Counter()
n_by, total = 0, 0
for pid in sorted(AMER_IDS):
    if pid not in prov_files:
        continue
    total += 1
    text = open(f"{GAME_HIST_PROV}/{prov_files[pid]}", encoding="latin-1").read()
    # top-level (undated) discovered_by lines: at column 0, outside any { } block
    depth, have = 0, False
    for ln in text.splitlines():
        s = ln.strip()
        if "{" in ln:
            depth += 1
        if s.startswith("discovered_by =") and depth == 0:
            m = re.search(r"discovered_by\s*=\s*(\S+)", s)
            if m:
                undated[pid].append(m.group(1))
                have = True
        if "}" in ln and depth > 0:
            depth -= 1
    # dated blocks containing discovered_by
    depth = 0
    for ln in text.splitlines():
        s = ln.strip()
        if "{" in ln:
            depth += 1
        if s.startswith("discovered_by =") and depth > 0:
            have = True
        if "}" in ln and depth > 0:
            depth -= 1
    for m in re.finditer(r"^(\d{4}\.\d{1,2}\.\d{1,2})\s*=\s*\{\s*discovered_by\s*=\s*(\S+)",
                         text, re.M):
        dated[pid].append((m.group(1), m.group(2)))
    if have:
        n_by += 1

print(f"=== PROVINCES: {n_by}/{total} American files carry discovered_by ===")
allt = Counter()
for tags in undated.values():
    allt.update(tags)
print("\n-- top undated discovered_by tags (tag: #provinces) --")
for t, c in allt.most_common(40):
    print(f"  {t}: {c}")
dt = Counter(t for lst in dated.values() for _d, t in lst)
print("\n-- dated discovered_by tags --")
for t, c in dt.most_common(30):
    print(f"  {t}: {c}")
tg = {t for tags in undated.values() for t in tags if t not in allt and t.islower()}
print("\n-- lowercase (tech-group?) undated targets --", sorted(tg))
print("\n-- provs with dated discovered_by: first 40 --")
for pid, lst in sorted(dated.items())[:40]:
    print(f"  {pid}: {lst}")

# how many distinct tags appear in each file (spread check)
spread = sorted((len(v), k) for k, v in undated.items())
print("\n-- undated-tag count distribution --")
c = Counter(n for n, _ in spread)
for n in sorted(c):
    print(f"  {n} tags: {c[n]} provinces")

print("\n-- sample files with most undated tags --")
for n, pid in spread[-10:]:
    print(f"  {pid}: {undated[pid]}")

# ---- country files: discovered = { ... } blocks ----
MODE_TAGS = set()
REALMS = []
import importlib.util
spec = importlib.util.spec_from_file_location("design", f"{BASE}/design.py")
design = importlib.util.module_from_spec(spec)
spec.loader.exec_module(design)
for r in design.REALMS + [dict(tag=t) for t in json.load(open(f"{BASE}/tribes.json"))]:
    MODE_TAGS.add(r["tag"])
for t in design.RESTORED:
    MODE_TAGS.add(t)

print("\n=== COUNTRY FILES: discovered = {} blocks in vanilla ===")
for tag in sorted(MODE_TAGS):
    cands = [f for f in os.listdir(GAME_HIST_CNT) if f.startswith(tag + " -")]
    if not cands:
        continue
    text = open(f"{GAME_HIST_CNT}/{cands[0]}", encoding="latin-1").read()
    hits = []
    for m in re.finditer(r"discovered\s*=\s*\{", text):
        # crude: capture up to matching close brace
        i = m.end()
        depth = 1
        out = []
        while depth and i < len(text):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            if depth:
                out.append(ch)
            i += 1
        hits.append((text.count("\n", 0, m.start()), "".join(out)))
    if hits:
        print(f"  {tag}:")
        for ln, body in hits:
            n_ids = len(re.findall(r"\d+", body))
            print(f"    line {ln}: {n_ids} ids")