#!/usr/bin/env python3
"""Verify design.py against the game files and derived data.

Run BEFORE generating the mod:
    python3 verify_design.py

Exits 0 when every check passes, 1 otherwise. Prints one PASS/FAIL line
per check so a failed run says exactly which invariant broke.
"""
import os
import sys

import verify_common as vc

design = vc.load_design()
AM = vc.load_america()
TRIBES = vc.load_tribes()
USED = vc.load_used_tags()

PROVS = {str(k): v for k, v in AM["provs"].items()}
AREAS = AM["areas"]
TRIBE_PROVS = {str(t["prov"]) for t in TRIBES.values()}
COUNTRY_TAGS = vc.parse_country_tags()
REGIONS = vc.parse_region_names()
COLONIALS = vc.parse_colonial_names()
POS = vc.parse_positions()

# only amer provs that have a file (land) matter; sea ids have no entries
failures = []
checks = 0


def check(name, ok, detail=""):
    global checks
    checks += 1
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        failures.append(name)


# ---------------- RESTORED: the 35 vanilla tags / 99 provinces ----------------
restored = getattr(design, "RESTORED", None)
print("\n--- RESTORED (1444 basegame restore) ---")
if restored is None:
    check("RESTORED dict present in design.py", False, "missing: 35 tags / 99 provs to add")
else:
    all_provs = []
    check("RESTORED has 35 tags", len(restored) == 35, f"got {len(restored)}")
    for tag, provs in restored.items():
        all_provs += [str(p) for p in provs]
        bad = [p for p in provs if str(p) not in PROVS]
        check(f"RESTORED {tag}: all provs exist in america.json", not bad,
              ", ".join(map(str, bad)) or f"{len(provs)} provs")
        trib = [p for p in provs if str(p) in TRIBE_PROVS]
        check(f"RESTORED {tag}: no tribe provs", not trib, ", ".join(map(str, trib)))
        vh = vc.vanilla_hist_files(tag)
        check(f"RESTORED {tag}: vanilla history file exists", bool(vh),
              vh[0] if vh else "not found in history/countries")
        check(f"RESTORED {tag}: bound in vanilla country_tags", tag in COUNTRY_TAGS,
              COUNTRY_TAGS.get(tag, "MISSING"))
        missing_pf = [p for p in provs if not vc.vanilla_prov_files(str(p))]
        check(f"RESTORED {tag}: vanilla province files exist", not missing_pf,
              ", ".join(map(str, missing_pf)) or "all present")
    dup = [p for p in set(all_provs) if all_provs.count(p) > 1]
    check("RESTORED provs unique across tags", not dup, ", ".join(dup))
    check("RESTORED totals 99 provs", len(all_provs) == 99, f"got {len(all_provs)}")

# ---------------- GUTTED: 9 removed realms + orphan provs ----------------
guted = getattr(design, "GUTTED", None)
rest_provs = ({str(p) for provs in restored.values() for p in provs}
              if restored else set())
print("\n--- GUTTED (realms removed by the restore) ---")
if guted is None:
    check("GUTTED list present in design.py", False, "missing: 9 realms with their areas")
else:
    check("GUTTED has 9 realms", len(guted) == 9, f"got {len(guted)}")
    gut_areas = set()
    for tag, areas in guted:
        bad = [a for a in areas if a not in AREAS]
        check(f"GUTTED {tag}: areas exist", not bad, ", ".join(bad))
        gut_areas |= set(areas)
    # no gutted area may belong to a surviving realm
    surv_areas = {}
    for r in design.REALMS:
        if r.get("skip"):
            continue
        for a in r.get("areas", []):
            surv_areas.setdefault(a, r["tag"])
    clash = sorted(gut_areas & set(surv_areas))
    check("no area shared between GUTTED and surviving realms", not clash,
          ", ".join(clash))
    if restored is not None and guted is not None:
        orphans = sorted({str(x) for a in gut_areas for x in AREAS.get(a, [])
                          if str(x) in PROVS} - rest_provs - TRIBE_PROVS)
        check("orphan count vs expected 40", len(orphans) == 40, f"got {len(orphans)}")
        no_pos = [o for o in orphans if o not in POS]
        check("every orphan has a map position", not no_pos,
              ", ".join(no_pos) or "all positioned")

# ---------------- REALMS (survivors) ----------------
print("\n--- REALMS ---")
realms = [r for r in design.REALMS if not r.get("skip")]
tags = [r["tag"] for r in realms]
check("realm tags unique", len(tags) == len(set(tags)))
for t in tags:
    check(f"realm {t} not forbidden", t not in vc.FORBIDDEN, "forbidden tag!" if t in vc.FORBIDDEN else "")
new_tags = [r["tag"] for r in realms if not r["reuse"]]
new_tags += [f["tag"] for f in getattr(design, "FORMABLE_REGIONS", []) if f.get("new_def")]
conflicts = [t for t in new_tags if t in USED]
check("no new tag conflicts with vanilla (used_tags.txt)", not conflicts,
      ", ".join(conflicts) or "clean")

seen_area = {}
double = []
unknown_area = []
no_provs = []
cap_out = []
reuse_missing_hist = []
reuse_missing_flag = []
for r in sorted(realms, key=lambda x: x["tag"]):
    ids = []
    for a in r.get("areas", []):
        if a not in AREAS:
            unknown_area.append((r["tag"], a))
            continue
        if a in seen_area:
            double.append((seen_area[a], r["tag"], a))
            continue
        seen_area[a] = r["tag"]
        ids += [str(x) for x in AREAS[a]
                if str(x) in PROVS and str(x) not in TRIBE_PROVS
                and str(x) not in rest_provs]
    for x in r.get("extra", []):
        if str(x) not in TRIBE_PROVS and str(x) not in rest_provs:
            ids.append(str(x))
    ids = sorted(set(ids))
    if not ids:
        no_provs.append(r["tag"])
    if r["capital"] and str(r["capital"]) not in ids:
        cap_out.append((r["tag"], r["capital"]))
    if r["reuse"]:
        if not vc.vanilla_hist_files(r["tag"]):
            reuse_missing_hist.append(r["tag"])
        if not os.path.isfile(f"{vc.GAME}/gfx/flags/{r['tag']}.tga"):
            reuse_missing_flag.append(r["tag"])
    else:
        need = [k for k in ("color", "names", "ideas", "graphical_culture") if k not in r]
        check(f"realm {r['tag']}: new-def fields present", not need,
              ", ".join(need) or "ok")
check("no unknown realm areas", not unknown_area, str(unknown_area))
check("no area double-assigned", not double, str(double))
check("every realm has provinces after carve", not no_provs, ", ".join(no_provs))
check("every realm capital in own provs", not cap_out, str(cap_out))
check("reuse realms: vanilla history file exists", not reuse_missing_hist,
      ", ".join(reuse_missing_hist))
check("reuse realms: vanilla flag exists", not reuse_missing_flag,
      ", ".join(reuse_missing_flag) or "all flags present")

# tribes: no double assignment, and unknown-good fallback realm survives
print("\n--- TRIBES ---")
claimed = set()
for r in realms:
    for a in r.get("areas", []):
        claimed |= {str(x) for x in AREAS.get(a, [])}
    claimed |= {str(x) for x in r.get("extra", [])}
claimed_land = {p for p in claimed if p in PROVS} - TRIBE_PROVS
bt = [t for t, v in TRIBES.items() if str(v["prov"]) in claimed_land]
check("no tribe prov inside a realm claim", not bt, ", ".join(bt))

# unknown-good tribes: their pre-carve realm must still exist post-gutting
pre_owner = {}
for a, tag in seen_area.items():
    for x in AREAS[a]:
        pre_owner.setdefault(str(x), tag)
surviving_tags = set(tags)
guted_tags = {t for t, _ in (guted or [])}
no_po = []
for t, v in TRIBES.items():
    if v.get("trade_good") in (None, "", "unknown"):
        po = pre_owner.get(str(v["prov"]))
        if po is None or po in guted_tags:
            no_po.append((t, v["prov"], po))
check("unknown-good tribes: pre-carve realm survives", not no_po, str(no_po))

# ---------------- FORMABLES (federations + regions) ----------------
print("\n--- FORMABLES ---")
fed_tags = set()
for f in getattr(design, "FORMABLES", []):
    fed_tags.add(f["tag"])
    miss = [m for m in f.get("members", []) if m not in set(tags) | set(TRIBES)]
    check(f"formable {f['tag']}: members exist", not miss, ", ".join(miss))
    badp = [p for p in f.get("provs", []) if str(p) not in PROVS]
    check(f"formable {f['tag']}: provs valid", not badp, ", ".join(map(str, badp)))
    if f.get("capital") and str(f["capital"]) not in {str(p) for p in f.get("provs", [])}:
        check(f"formable {f['tag']}: capital among provs", False, f"capital {f['capital']}")

for f in getattr(design, "FORMABLE_REGIONS", []):
    reg_ok = f.get("region") in REGIONS
    col_ok = f.get("colonial") in COLONIALS
    check(f"region formable {f['tag']}: region exists", reg_ok, f.get("region", "?"))
    check(f"region formable {f['tag']}: colonial region exists", col_ok, f.get("colonial", "?"))
    if f.get("new_def"):
        need = [k for k in ("color", "names", "ideas", "culture", "religion", "capital", "adj")
                if k not in f]
        check(f"region formable {f['tag']}: new-def fields present", not need, ", ".join(need))
        check(f"region formable {f['tag']}: tag not in used_tags", f["tag"] not in USED,
              "CONFLICTS with vanilla!" if f["tag"] in USED else "clean")
    else:
        vh = vc.vanilla_hist_files(f["tag"])
        check(f"region formable {f['tag']}: vanilla history exists", bool(vh),
              vh[0] if vh else "not found")
        check(f"region formable {f['tag']}: vanilla flag exists",
              os.path.isfile(f"{vc.GAME}/gfx/flags/{f['tag']}.tga"),
              "flag file missing" if not os.path.isfile(f"{vc.GAME}/gfx/flags/{f['tag']}.tga") else "ok")

# decision key collisions between fed and region formables
all_dec = [f["tag"] for f in getattr(design, "FORMABLES", [])] + \
          [f["tag"] for f in getattr(design, "FORMABLE_REGIONS", [])]
check("formable tags unique", len(all_dec) == len(set(all_dec)),
      ", ".join(sorted({t for t in all_dec if all_dec.count(t) > 1})) or "clean")

# ---------------- summary ----------------
print(f"\n{'='*60}")
print(f"checks: {checks}  failures: {len(failures)}")
if failures:
    print("FAILED:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("ALL CHECKS PASSED")
sys.exit(0)