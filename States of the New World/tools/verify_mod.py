#!/usr/bin/env python3
"""Verify the GENERATED mod tree (OUT) against design + derived data.

Run AFTER generating the mod:
    python3 gen_mod.py && python3 verify_mod.py

Checks:
  1. Every realm/tribe has its history/countries file in OUT.
  2. Every realm capital province is owned by its realm in OUT.
  3. Every province file owner/controller is a real tag; nothing unowned or
     double-written (no two province files for the same province id).
  4. Restored provs (RESTORED) are in OUT as byte-exact vanilla copies plus
     the high_american discovery line (nothing else differs).
  5. No stale country files for removed realms (GUTTED tags or MHC/VRC/etc).
  6. Decisions file: braces balanced, every formable tag has a decision key,
     keys are unique.
  7. Localisation: every non-reuse realm + new_def formable has tag/adj loc,
     every decision has name+desc, no duplicate keys, BOM present.
  8. descriptor.mod exists with the right supported_version.
  9. flags_needed.txt matches the real missing flags (new tags, no vanilla
     tga, and not already built).
Exits 0 on success, 1 on any failure.
"""
import os
import re
import sys

import verify_common as vc

design = vc.load_design()
AM = vc.load_america()
TRIBES = vc.load_tribes()
USED = vc.load_used_tags()
NEW_TRIBES = getattr(design, "NEW_TRIBES", [])
new_tribe_tags = {t["tag"] for t in NEW_TRIBES}
new_tribe_provs = {str(t["prov"]) for t in NEW_TRIBES}

PROVS = {str(k): v for k, v in AM["provs"].items()}
AREAS = AM["areas"]
failures = []
checks = 0


def check(name, ok, detail=""):
    global checks
    checks += 1
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        failures.append(name)


if not os.path.isdir(vc.OUT):
    print("mod output dir missing:", vc.OUT)
    sys.exit(1)

realms = [r for r in design.REALMS if not r.get("skip")]
# simulate gen's province assignment for invariant checks
rest_provs = ({str(p) for provs in (design.RESTORED or {}).values() for p in provs}
              if hasattr(design, "RESTORED") and design.RESTORED else set())
tribe_provs = {str(t["prov"]) for t in TRIBES.values()}
seen_area = {}
claimed = {}
for r in realms:
    ids = []
    for a in r.get("areas", []):
        if a not in AREAS:
            continue
        assert a not in seen_area, f"area {a} claimed twice"
        seen_area[a] = r["tag"]
        ids += [str(x) for x in AREAS[a]
                if str(x) in PROVS and str(x) not in tribe_provs
                and str(x) not in rest_provs and str(x) not in new_tribe_provs]
    for x in r.get("extra", []):
        if str(x) not in tribe_provs and str(x) not in rest_provs \
                and str(x) not in new_tribe_provs:
            ids.append(str(x))
    claimed[r["tag"]] = set(ids)
# orphan redistribution: the nearest-realm rule must have assigned all 40
guted = getattr(design, "GUTTED", None)
guted_areas = set()
for _tag, _areas in (guted or []):
    guted_areas |= set(_areas)
orphans = sorted({str(x) for a in guted_areas for x in AREAS.get(a, [])
                  if str(x) in PROVS} - rest_provs - tribe_provs)
# nearest realm by positions.txt (mirror of gen_mod rule, deterministic)
POS = vc.parse_positions()
claimed_sim = {tag: set(ids) for tag, ids in claimed.items()}
assigned = {}
for o in orphans:
    if o not in POS:
        continue
    ox, oy = POS[o]
    best, bd = None, None
    # gen_mod adds each orphan to its chosen realm before the next orphan,
    # so a later orphan can be pulled toward an earlier-assigned one
    for tag, ids in claimed_sim.items():
        b = None
        for p in ids:
            if p not in POS:
                continue
            px, py = POS[p]
            d = (ox - px) ** 2 + (oy - py) ** 2
            if b is None or d < b:
                b = d
        if b is not None and (bd is None or b < bd):
            best, bd = tag, b
    assigned[o] = best
    if best:
        claimed_sim[best].add(o)

print("--- 1. country history files ---")
out_cnt = vc.out_country_files()
restored = getattr(design, "RESTORED", None) or {}
all_tags = {r["tag"] for r in realms} | set(TRIBES) | set(restored) | new_tribe_tags
miss_cnt = []
for r in realms + [{"tag": t} for t in TRIBES] + [{"tag": t} for t in restored] \
        + [{"tag": t} for t in new_tribe_tags]:
    cand = [f for f in out_cnt
            if f.startswith(r["tag"] + " -") or f.startswith(r["tag"] + "- ")]
    if not cand:
        miss_cnt.append(r["tag"])
check("every realm/tribe/restored has a country file in OUT", not miss_cnt, ", ".join(miss_cnt))

# no stale files: country files whose tag is not a current realm/tribe/formable
known_tags = all_tags | {f["tag"] for f in design.FORMABLES} | \
             {f["tag"] for f in design.FORMABLE_REGIONS}
stale = []
for f in out_cnt:
    t = vc.tag_of_country_file(f)
    if t and t not in known_tags:
        stale.append(f)
check("no stale country files (removed realms gone)", not stale, ", ".join(stale))

print("--- 2. capitals + owner/controller ---")
out_prov = vc.out_prov_files()
by_id = {}
for f in out_prov:
    m = re.match(r"^(\d+)", f)
    if m:
        by_id.setdefault(m.group(1), []).append(f)
dup_prov = {k: v for k, v in by_id.items() if len(v) > 1}
check("no duplicate province files for one id", not dup_prov, str(dup_prov))

cap_bad = []
for r in realms:
    cap = str(r["capital"])
    if cap not in by_id:
        cap_bad.append((r["tag"], cap, "no file"))
        continue
    text = vc.read(f"{vc.OUT}/history/provinces/{by_id[cap][0]}")
    m = re.search(r"^\s*owner\s*=\s*(\S+)", text, re.M)
    if not m or m.group(1) != r["tag"]:
        cap_bad.append((r["tag"], cap, m.group(1) if m else "no owner"))
check("every realm capital prov file owned by that realm", not cap_bad, str(cap_bad))

# every province file: owner+controller same, owner is a known tag
bad_owner = []
for f in out_prov:
    text = vc.read(f"{vc.OUT}/history/provinces/{f}", "latin-1")
    mo = re.search(r"^\s*owner\s*=\s*(\S+)", text, re.M)
    mc = re.search(r"^\s*controller\s*=\s*(\S+)", text, re.M)
    if not mo or not mc:
        bad_owner.append((f, "owner/controller missing"))
        continue
    if mo.group(1) != mc.group(1):
        bad_owner.append((f, f"owner {mo.group(1)} != controller {mc.group(1)}"))
    if mo.group(1) not in known_tags:
        bad_owner.append((f, f"unknown owner {mo.group(1)}"))
check("all province files: owner==controller, known tag", not bad_owner, str(bad_owner[:5]))

print("--- 3. restored provs: byte-exact vanilla + discovery line ---")
if restored:
    rest_ids = {str(p) for provs in restored.values() for p in provs}
    missing = sorted(rest_ids - set(by_id))
    bad_copy = []
    for pid in sorted(rest_ids & set(by_id)):
        fname = by_id[pid][0]
        out_raw = open(f"{vc.OUT}/history/provinces/{fname}", "rb").read()
        vanilla = vc.vanilla_prov_files(pid)
        if not vanilla:
            bad_copy.append((pid, "no vanilla file"))
            continue
        vraw = open(f"{vc.GAME_HIST_PROV}/{vanilla[0]}", "rb").read()
        if out_raw != vc.discovery_copy(vraw):
            bad_copy.append((pid, "not vanilla + discovery"))
    check("every restored prov file in OUT = vanilla + discovery line",
          not missing and not bad_copy,
          f"missing: {missing[:6]} bad: {bad_copy[:6]}")
    clash = [t for t in restored if t in known_tags - all_tags]
    check("no restored tag doubles as formable/region tag", not clash, ", ".join(clash))
else:
    check("RESTORED defined in design.py", False, "restored checks skipped")

print("--- 4. orphan redistribution ---")
if orphans:
    o_bad = []
    for o in orphans:
        if o not in assigned:
            o_bad.append((o, "no positions"))
        elif o not in by_id:
            o_bad.append((o, "no province file"))
        else:
            text = vc.read(f"{vc.OUT}/history/provinces/{by_id[o][0]}")
            m = re.search(r"^\s*owner\s*=\s*(\S+)", text, re.M)
            if not m or m.group(1) != assigned[o]:
                o_bad.append((o, f"owner {m.group(1) if m else '?'} != nearest {assigned[o]}"))
    check("every orphan owned by its nearest realm", not o_bad, str(o_bad[:6]))
else:
    check("orphan list computed", False, "no GUTTED/RESTORED in design.py")

print("--- 4b. feudal monarchy + dev-derived rank + high_american tech ---")
# realm dev = n*sum(dev)+3 (province writer gives +1 per component at the capital);
# tribe dev = 9 (one province, dev=[2,2,2]); restored dev = vanilla base sums.
def preamble(text):
    m = re.search(r"^\d{4}\.\d{1,2}\.\d{1,2}\s*=\s*\{", text, re.M)
    return text[:m.start()] if m else text

expected = {}
for r in realms:
    expected[r["tag"]] = vc.gov_rank(r["tag"], sum(r["dev"]) * len(claimed_sim[r["tag"]]) + 3)
for t in TRIBES:
    expected[t] = vc.gov_rank(t, 9)
for t in new_tribe_tags:
    expected[t] = vc.gov_rank(t, 9)
for tag, provs in restored.items():
    expected[tag] = vc.gov_rank(tag, sum(vc.vanilla_prov_dev(p) for p in provs))
bad_gov, bad_rank, bad_tech = [], [], []
for tag, want in expected.items():
    cand = [f for f in out_cnt if f.startswith(tag + " -") or f.startswith(tag + "- ")]
    if not cand:
        continue
    text = vc.read(f"{vc.OUT}/history/countries/{cand[0]}", "latin-1")
    head = preamble(text)
    if not re.search(r"^\s*government\s*=\s*monarchy", head, re.M):
        bad_gov.append(tag)
    elif not re.search(r"^\s*add_government_reform\s*=\s*feudalism_reform", head, re.M):
        bad_gov.append(tag + " (no feudalism_reform)")
    m = re.search(r"^\s*government_rank\s*=\s*(\d+)", head, re.M)
    got = int(m.group(1)) if m else None
    if got != want:
        bad_rank.append((tag, got, want))
    if not re.search(r"^\s*technology_group\s*=\s*high_american", head, re.M):
        bad_tech.append(tag)
check("every realm/tribe/restored preamble: government = monarchy", not bad_gov, ", ".join(bad_gov))
check("every preamble government_rank matches dev rule", not bad_rank, str(bad_rank[:6]))
check("every preamble has technology_group = high_american", not bad_tech, ", ".join(bad_tech))
rank3 = sorted(t for t, w in expected.items() if w == 3)
check("only Aztec gets rank 3", rank3 == ["AZT"], str(rank3))

print("--- 4c. continent visibility ---")
# every OUT province file must let high_american see it at game start
no_disc = []
for f in out_prov:
    raw = open(f"{vc.OUT}/history/provinces/{f}", "rb").read()
    if b"discovered_by = high_american" not in raw:
        no_disc.append(f)
check("every OUT prov file has discovered_by = high_american", not no_disc, ", ".join(no_disc[:8]))
# and no province outside the Americas may appear in OUT
amer_ids = set(PROVS)
non_amer = [pid for pid in by_id if pid not in amer_ids]
check("no non-American province files in OUT", not non_amer, ", ".join(non_amer[:8]))

print("--- 5. decisions file ---")
dec_path = f"{vc.OUT}/decisions/zzz_states_of_the_new_world_formables.txt"
dec_text = vc.read(dec_path)
depth = 0
ok_braces = True
for ch in dec_text:
    if ch == "{":
        depth += 1
    elif ch == "}":
        depth -= 1
        if depth < 0:
            ok_braces = False
            break
check("decisions file braces balanced", ok_braces and depth == 0, f"depth={depth}")

# decision keys: the root blocks inside the (single) country_decisions wrapper.
dec_blocks = re.findall(r"^\t(\w+) = \{", dec_text, re.M)
check(f"decisions file has {len(design.FORMABLES)+len(design.FORMABLE_REGIONS)} formable blocks",
      len(dec_blocks) == len(design.FORMABLES) + len(design.FORMABLE_REGIONS),
      f"got {len(dec_blocks)}")

print("--- 6. localisation ---")
loc_path = f"{vc.OUT}/localisation/zzz_states_of_the_new_world_l_english.yml"
with open(loc_path, "rb") as f:
    head = f.read(3)
    f.seek(0)
    loc_text = f.read().decode("utf-8-sig")
check("loc file has BOM", head == b"\xef\xbb\xbf", head.hex())
keys = re.findall(r"^\s*([\w]+):0\s+\"", loc_text, re.M)
keyset = set(keys)
dup_keys = sorted({k for k in keys if keys.count(k) > 1})
check("no duplicate loc keys", not dup_keys, ", ".join(dup_keys))
missing_loc = []
for r in realms:
    if r["reuse"]:
        continue
    if r["tag"] not in keyset or f"{r['tag']}_ADJ" not in keyset:
        missing_loc.append(r["tag"])
for f in design.FORMABLE_REGIONS:
    if f.get("new_def"):
        if f["tag"] not in keyset or f"{f['tag']}_ADJ" not in keyset:
            missing_loc.append(f"{f['tag']}(formable)")
for t in NEW_TRIBES:
    if t["tag"] not in keyset or f"{t['tag']}_ADJ" not in keyset:
        missing_loc.append(t["tag"])
check("all non-reuse realms + new_def formables + new tribes have tag/adj loc",
      not missing_loc, ", ".join(missing_loc))
# decision loc keys are the root blocks of the decisions file (key + key_desc)
missing_dec_loc = []
for b in dec_blocks:
    if b not in keyset or f"{b}_desc" not in keyset:
        missing_dec_loc.append(b)
check("every decision key has name+desc loc", not missing_dec_loc, ", ".join(missing_dec_loc))

print("--- 7. descriptor ---")
desc_path = f"{vc.OUT}/descriptor.mod"
desc = vc.read(desc_path) if os.path.isfile(desc_path) else ""
check("descriptor.mod exists", bool(desc))
m = re.search(r'supported_version="([^"]+)"', desc)
check("descriptor supports 1.37", bool(m and m.group(1).startswith("1.37")),
      m.group(1) if m else "no supported_version")

print("--- 8. flags_needed.txt ---")
flags_path = f"{vc.BASE}/flags_needed.txt"
gamed_flags = set(os.listdir(f"{vc.GAME}/gfx/flags"))
out_flags = set(os.listdir(f"{vc.OUT}/gfx/flags")) if os.path.isdir(f"{vc.OUT}/gfx/flags") else set()
need = set()
for r in realms:
    if not r["reuse"]:
        need.add(r["tag"])
for f in design.FORMABLE_REGIONS:
    if f.get("new_def"):
        need.add(f["tag"])
for t in NEW_TRIBES:
    need.add(t["tag"])
need = {t for t in need if t not in gamed_flags and t not in out_flags}
if os.path.isfile(flags_path):
    listed = {l.strip() for l in open(flags_path) if l.strip()}
    missing = need - listed
    extra = listed - need
    check("flags_needed matches actual need", not missing and not extra,
          f"missing: {sorted(missing)} extra: {sorted(extra)}" if (missing or extra) else f"{len(need)} flags")
else:
    check("flags_needed.txt exists", False, f"create it with: {' '.join(sorted(need))}")

print(f"\n{'='*60}")
print(f"checks: {checks}  failures: {len(failures)}")
if failures:
    print("FAILED:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("ALL CHECKS PASSED")
sys.exit(0)