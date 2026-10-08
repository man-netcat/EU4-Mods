#!/usr/bin/env python3
"""Analyze the tribe carve: realms losing capitals, remaining provinces with names,
special tribes (no monarch, unknown trade good), and federation-member province ids."""
import json, os, importlib.util, sys

BASE = os.path.dirname(os.path.abspath(__file__))

AM = json.load(open(f"{BASE}/america.json"))
PROVS = {str(k): v for k, v in AM["provs"].items()}
AREAS = AM["areas"]

spec = importlib.util.spec_from_file_location("design", f"{BASE}/design.py")
design = importlib.util.module_from_spec(spec)
sys.modules["design"] = design
spec.loader.exec_module(design)
REALMS = [r for r in design.REALMS if not r.get("skip")]

tribes = json.load(open(f"{BASE}/tribes.json"))
tprovs = {t["prov"] for t in tribes.values()}
tprovs |= {t["prov"] for t in tribes.values()}  # prov strings like "2564"

def realm_ids(r):
    ids = {str(x) for x in r.get("extra", [])}
    for a in r.get("areas", []):
        ids |= {str(x) for x in AREAS[a] if str(x) in PROVS}
    return ids

print("=== REALMS LOSING CAPITAL (remain: id name) ===")
for r in sorted(REALMS, key=lambda x: x["tag"]):
    remain = sorted(realm_ids(r) - tprovs)
    if str(r["capital"]) in tprovs:
        print(f"{r['tag']}: old cap {r['capital']} -> remain {[(i, PROVS[i].get('name','?')) for i in remain]}")

print("\n=== REALMS WITH 0 REMAINING PROVINCES ===")
for r in REALMS:
    if not realm_ids(r) - tprovs:
        print(f"{r['tag']} IS EMPTY")

print("\n=== TRIBES WITH NO MONARCH ===")
for tag, t in sorted(tribes.items()):
    if not t.get("monarch"):
        print(f"{tag}: {t['prov']} {t['provname']}")

print("\n=== TRIBES WITH UNKNOWN TRADE GOOD ===")
for tag, t in sorted(tribes.items()):
    if t.get("trade_good") == "unknown":
        # find which realm's area contains this province
        owner = None
        for r in REALMS:
            if t["prov"] in realm_ids(r):
                owner = r["tag"]
                break
        print(f"{tag}: {t['prov']} {t['provname']} (pre-carve owner {owner})")

print("\n=== FEDERATION MEMBER PROVINCES (from tribes.json) ===")
for tag in sorted(tribes):
    t = tribes[tag]
    if t.get("federation"):
        print(f"{tag}: fed={t['federation']} prov={t['prov']} {t['provname']}")

print("\n=== ALL TRIBE TAGS: tag prov name culture rel good ===")
for tag in sorted(tribes):
    t = tribes[tag]
    print(f"{tag} {t['prov']} {t['provname']} {t['culture']} {t['religion']} {t['trade_good']}")