#!/usr/bin/env python3
"""Generate the 'States of the New World' EU4 mod from design.py + america.json."""
import json, os, re, sys, importlib.util
from verify_common import gov_rank, vanilla_prov_dev, parse_country_tags

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = "/home/rick/Paradox/Mods/Europa Universalis IV/States of the New World"
GAME_DIR = "/home/rick/Paradox/Games/Europa Universalis IV"
GAME_COUNTRIES = f"{GAME_DIR}/common/countries"
GAME_HIST_CNT = f"{GAME_DIR}/history/countries"
GAME_HIST_PROV = f"{GAME_DIR}/history/provinces"
GAME_POSITIONS = f"{GAME_DIR}/map/positions.txt"

# tag -> vanilla def filename; used to hand tribes their first real monarch name.
DEFS_BY_TAG = parse_country_tags()

def first_monarch_name(tag):
    """First name from the vanilla country def's monarch_names pool, or None."""
    def_file = DEFS_BY_TAG.get(tag)
    if not def_file:
        return None
    path = f"{GAME_COUNTRIES}/{def_file}"
    if not os.path.isfile(path):
        return None
    text = open(path, encoding="latin-1").read()
    m = re.search(r"monarch_names\s*=\s*\{(.*?)\}", text, re.S)
    if not m:
        return None
    names = re.findall(r'"([^"]+)"', m.group(1))
    if not names:
        return None
    return re.sub(r"\s*#\d+\s*$", "", names[0])

# ---------- load data ----------
with open(f"{BASE}/america.json") as f:
    AM = json.load(f)
PROVS = {str(k): v for k, v in AM["provs"].items()}
AREAS = AM["areas"]          # name -> [ids]
AMER_IDS = set(str(x) for x in AM["amer_ids"])

with open(f"{BASE}/used_tags.txt") as f:
    USED = set(l.strip() for l in f if l.strip())

spec = importlib.util.spec_from_file_location("design", f"{BASE}/design.py")
design = importlib.util.module_from_spec(spec)
sys.modules["design"] = design
spec.loader.exec_module(design)
REALMS = [r for r in design.REALMS if not r.get("skip")]
SKIP_AREAS = set(design.SKIP_AREAS)
RESTORED = getattr(design, "RESTORED", {})
REST_PROVS = {str(p) for provs in RESTORED.values() for p in provs}
GUTTED = getattr(design, "GUTTED", [])
GUT_AREAS = {a for _t, areas in GUTTED for a in areas}

with open(f"{BASE}/tribes.json") as f:
    TRIBES = json.load(f)                       # tag -> tribe dict (108 vanilla native OPMs)
TRIBE_PROVS = {str(t["prov"]) for t in TRIBES.values()}

NEW_TRIBES = getattr(design, "NEW_TRIBES", [])  # new custom tribal tags (see design.py)
NEW_TRIBE_PROVS = {str(t["prov"]) for t in NEW_TRIBES}

FORBIDDEN = {"ADD","ADM","AND","AGE","ART","AUX","CAR","CAT","CAV","CON","DIP","HAS","HRE","INF",
             "JAM","MIL","MIN","NOT","NUL","PRN","RGB","SUM","VAL","VAN"}

# vanilla history/countries filename for reuse tags (must match EXACTLY to override).
# Auto-detect from the game folder instead of hardcoding, because vanilla names vary
# ("ALA - Alaska.txt" vs "LOU - Lousiana.txt" typo, etc.)
VANILLA_HIST = {}
for _r in REALMS:
    if _r["reuse"]:
        _cands = [f for f in os.listdir(GAME_HIST_CNT)
                  if f.startswith(_r["tag"] + " -")]
        assert _cands, f"No vanilla history file for reuse tag {_r['tag']}"
        _cands.sort()
        VANILLA_HIST[_r["tag"]] = _cands[0]
        if len(_cands) > 1:
            print(f"  note: multiple vanilla files for {_r['tag']}: {_cands}")

def mode(lst):
    counts = {}
    for x in lst:
        if x: counts[x] = counts.get(x, 0) + 1
    if not counts: return ""
    return max(counts, key=counts.get)

# ---------- validation ----------
tags = [r["tag"] for r in REALMS]
assert len(tags) == len(set(tags)), "duplicate tags"
for t in tags:
    assert t not in FORBIDDEN, f"forbidden tag {t}"
new_tags = [r["tag"] for r in REALMS if not r["reuse"]]
# formable tags that need a new def (ARG); BRZ reuses vanilla files
new_tags += [f["tag"] for f in design.FORMABLE_REGIONS if f.get("new_def")]
new_tags += [t["tag"] for t in NEW_TRIBES]
conflicts = [t for t in new_tags if t in USED]
assert not conflicts, f"new tag conflicts with vanilla: {conflicts}"

# ---------- resolve provinces per realm ----------
realm_by_tag = {}
assigned = {}
seen_area = {}
pre_owner = {}
for r in REALMS:
    ids = []
    for a in r.get("areas", []):
        if a not in AREAS:
            sys.exit(f"unknown area '{a}' (realm {r['tag']})")
        if a in seen_area:
            sys.exit(f"area '{a}' assigned twice ({seen_area[a]} and {r['tag']})")
        seen_area[a] = r["tag"]
        for x in AREAS[a]:
            if str(x) in PROVS:                 # land provinces only (sea has no file)
                pre_owner.setdefault(str(x), r["tag"])
        ids += [str(x) for x in AREAS[a]
                if str(x) in PROVS and str(x) not in TRIBE_PROVS
                and str(x) not in REST_PROVS and str(x) not in NEW_TRIBE_PROVS]
    for x in r.get("extra", []):
        pre_owner.setdefault(str(x), r["tag"])
    ids += [str(x) for x in r.get("extra", [])
            if str(x) not in TRIBE_PROVS and str(x) not in REST_PROVS
            and str(x) not in NEW_TRIBE_PROVS]
    ids = sorted(set(ids))
    assert ids, f"realm {r['tag']} has no provinces"
    assert r["capital"] and str(r["capital"]) in ids, f"capital {r['capital']} not in realm {r['tag']} provs"
    for i in ids:
        assert i not in assigned, f"province {i} double-assigned ({assigned[i]} vs {r['tag']})"
        assigned[i] = r["tag"]
    r["_ids"] = ids
    realm_by_tag[r["tag"]] = r

# ---- tribes: 108 vanilla native OPMs carved out of the realms above ----
TRIBE_REALMS = []
for tag, t in sorted(TRIBES.items()):
    prov = str(t["prov"])
    assert prov in PROVS, f"tribe {tag}: province {prov} not in PROVS"
    assert prov not in assigned, f"province {prov} double-assigned ({assigned.get(prov)} vs tribe {tag})"
    good = t["trade_good"]
    if good in (None, "", "unknown"):
        po = pre_owner.get(prov)
        assert po, f"tribe {tag}: no pre-carve realm for trade good fallback on {prov}"
        good = realm_by_tag[po]["trade_good"]
        print(f"  note: tribe {tag} ({prov}) trade_good 'unknown' -> {good} (pre-carve {po})")
    mon = t.get("monarch") or dict(name=None, adm=3, dip=3, mil=3, birth=None, dynasty=None)
    if not mon.get("name") or mon["name"] == "Native Council":
        mon["name"] = first_monarch_name(tag) or "Native Council"
    tr = {
        "tag": tag, "name": t["provname"], "adj": None, "reuse": True,
        "dev": [2, 2, 2], "trade_good": good,
        "culture": t["culture"], "religion": t["religion"],
        "capital": prov, "tech": "high_american", "unit": "western",
        "monarchs": [mon],
        "_ids": [prov], "_culture": t["culture"], "_religion": t["religion"],
    }
    TRIBE_REALMS.append(tr)
    realm_by_tag[tag] = tr
    assigned[prov] = tag

# ---- new custom tribes: carved the same way, but non-reuse (new def, loc,
# country_tags entry; no vanilla flag exists, they stay on flags_needed.txt) ----
NEW_TRIBE_REALMS = []
for t in sorted(NEW_TRIBES, key=lambda x: x["tag"]):
    prov = str(t["prov"])
    assert prov in PROVS, f"new tribe {t['tag']}: province {prov} not in PROVS"
    assert prov not in assigned, f"province {prov} double-assigned ({assigned.get(prov)} vs new tribe {t['tag']})"
    assert t["tag"] not in realm_by_tag, f"new tribe tag {t['tag']} collides with existing tag"
    assert t["tag"] not in FORBIDDEN, f"forbidden tag {t['tag']}"
    good = t.get("trade_good")
    if good in (None, "", "unknown"):
        po = pre_owner.get(prov)
        assert po, f"new tribe {t['tag']}: no pre-carve realm for trade good fallback on {prov}"
        good = realm_by_tag[po]["trade_good"]
    nt = {
        "tag": t["tag"], "name": t["name"], "adj": t["adj"], "reuse": False,
        "dev": [2, 2, 2], "trade_good": good,
        "culture": t["culture"], "religion": t["religion"],
        "color": t["color"], "graphical_culture": t["graphical_culture"],
        "names": t["names"], "ideas": t["ideas"],
        "monarchs": t["monarchs"], "heir": t.get("heir"),
        "capital": prov, "tech": "high_american", "unit": "western",
        "_ids": [prov], "_culture": t["culture"], "_religion": t["religion"],
    }
    NEW_TRIBE_REALMS.append(nt)
    realm_by_tag[nt["tag"]] = nt
    assigned[prov] = nt["tag"]

# ---- restore carve: gutted realms' leftover provs go to nearest realm ----
# REST_PROVS are gone (vanilla keeps them); tribe OPMs carved out already.
# Orphans = gutted-area provs minus both. Assign each to the surviving realm
# with the nearest province on the map (Euclidean, positions.txt first pair).
if REST_PROVS and GUT_AREAS:
    pos = {}
    for _m in re.finditer(
            r"(\d+)\s*=\s*\{\s*position\s*=\s*\{\s*(-?[\d.]+)\s+(-?[\d.]+)",
            open(GAME_POSITIONS, encoding="latin-1").read()):
        pos[_m.group(1)] = (float(_m.group(2)), float(_m.group(3)))
    orphans = sorted({str(x) for a in GUT_AREAS for x in AREAS.get(a, [])
                      if str(x) in PROVS} - REST_PROVS - TRIBE_PROVS)

    def nearest(o):
        op = pos[o]
        best, bd = None, None
        for r in REALMS:                     # design order = deterministic
            b = min((op[0] - pos[p][0]) ** 2 + (op[1] - pos[p][1]) ** 2
                    for p in r["_ids"] if p in pos)
            if bd is None or b < bd:
                best, bd = r["tag"], b
        return best

    for o in orphans:
        assert o not in assigned, f"orphan {o} already assigned to {assigned[o]}"
        t = nearest(o)
        realm_by_tag[t]["_ids"] = sorted(set(realm_by_tag[t]["_ids"]) | {o})
        assigned[o] = t
    if orphans:
        print(f"  restored carve: {len(orphans)} orphans redistributed to nearest realms")

# government rank from total development (rank 1 < 20, rank 2 >= 20, rank 3 only Aztec).
# Realm dev = n*sum(dev) + 3 because the province writer gives +1 per component at the capital.
# Tribes: 1 prov (the capital), dev=[2,2,2] → 9 → rank 1.  All ranks here, before hist_body.
for _r in REALMS + TRIBE_REALMS + NEW_TRIBE_REALMS:
    _r["_rank"] = gov_rank(_r["tag"], sum(_r["dev"]) * len(_r["_ids"]) + 3)

# vanilla history files for tribe + formable tags
for _r in TRIBE_REALMS + [dict(tag=f["tag"]) for f in design.FORMABLES]:
    _t = _r["tag"]
    if _t in VANILLA_HIST:
        continue
    _cands = [f for f in os.listdir(GAME_HIST_CNT) if f.startswith(_t + " -")]
    assert _cands, f"No vanilla history file for tag {_t}"
    _cands.sort()
    VANILLA_HIST[_t] = _cands[0]
    if len(_cands) > 1:
        print(f"  note: multiple vanilla files for {_t}: {_cands}")

# unassigned american provinces?
skipped = set()
for sa in SKIP_AREAS:
    for x in AREAS.get(sa, []):
        skipped.add(str(x))
SEA_AREAS = {"caribbean_sea_area","coast_of_brazil_sea_area","gulf_of_mexico_area","gulf_stream_area",
             "hudson_bay_sea_area","north_pacific_coast_area","sea_of_grau_area"}
for sa in SEA_AREAS:
    for x in AREAS.get(sa, []):
        skipped.add(str(x))
all_area_provs = set()
for a, ids in AREAS.items():
    if a in SKIP_AREAS or a in SEA_AREAS:
        continue
    all_area_provs |= {str(x) for x in ids if str(x) in PROVS}
no_area = (AMER_IDS & set(PROVS)) - all_area_provs     # wasteland / wilderness, stays unowned
skipped |= no_area
skipped |= REST_PROVS     # vanilla keeps these provinces; no mod file written
missing = sorted(AMER_IDS - set(assigned) - skipped)
if missing:
    print("WARNING unassigned amer provinces:", missing)
assert not missing, f"{len(missing)} unassigned american provinces"

# ---------- culture / religion mode ----------
for r in REALMS:
    cult = [PROVS[i].get("culture") for i in r["_ids"]]
    reli = [PROVS[i].get("religion") for i in r["_ids"]]
    r["_culture"] = r.get("culture") or mode(cult)
    r["_religion"] = r.get("religion") or mode(reli)

# ---------- report ----------
print(f"{'TAG':5} {'reuse':6} {'CULTURE':16} {'RELIGION':14} {'NPROV':6} CAP  NAME")
for r in sorted(REALMS, key=lambda x: (-len(x["_ids"]), x["tag"])):
    print(f"{r['tag']:5} {str(r['reuse']):6} {r['_culture']:16} {r['_religion']:14} "
          f"{len(r['_ids']):6} {r['capital']:4} {r['name']}")
print(f"\nrealms: {len(REALMS)}  tribes: {len(TRIBE_REALMS)}+{len(NEW_TRIBE_REALMS)} new  formables: "
      f"{len(design.FORMABLES) + len(design.FORMABLE_REGIONS)}  "
      f"provinces assigned: {len(assigned)}  "
      f"amer land provs: {len(AMER_IDS & set(PROVS))}  unassigned: {len(missing)}")

# ---------- generation ----------
# Wipe the regenerated dirs first so removed realms leave no stale files
# (history/countries, provinces, defs, tags, loc, decisions are all mod-owned)
for _rel in ("common/countries", "common/country_tags", "history/countries",
             "history/provinces", "localisation", "decisions"):
    _p = f"{OUT}/{_rel}"
    if os.path.isdir(_p):
        for _f in os.listdir(_p):
            os.remove(f"{_p}/{_f}")

def w(path, text, bom=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = text.encode("utf-8-sig") if bom else text.encode("utf-8")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote", path.replace(OUT, "."))

# formable decision definitions
DECISIONS = {
    "IRO": "form_iroquois_confederacy",
    "HUR": "form_huron_confederacy",
    "ILL": "form_illiniwek_confederacy",
    "CRE": "form_creek_nation",
    "PUE": "form_pueblo_nation",
    "SHA": "form_shawnee_nation",
    "BRZ": "form_brazil",
    "ARG": "form_argentina",
    "MEX": "form_mexico",
    "PEU": "form_peru",
    "COL": "form_colombia",
    "BOL": "form_bolivia",
    "GTM": "form_guatemala",
    "RCA": "form_republic_of_california",
    "GLC": "form_gulf_coast_federation",
    "MCP": "form_mississippi_confederation",
    "FWN": "form_federation_of_the_west_indies",
}
DECISION_NAMES = {
    "IRO": "Form the Iroquois Confederacy",
    "HUR": "Form the Huron Confederacy",
    "ILL": "Form the Illiniwek Confederacy",
    "CRE": "Form the Creek Nation",
    "PUE": "Form the Pueblo Nation",
    "SHA": "Form the Shawnee Nation",
    "BRZ": "Form Brazil",
    "ARG": "Form Argentina",
    "MEX": "Form Mexico",
    "PEU": "Form Peru",
    "COL": "Form Colombia",
    "BOL": "Form Bolivia",
    "GTM": "Form Guatemala",
    "RCA": "Form the Republic of California",
    "GLC": "Form the Gulf Coast Federation",
    "MCP": "Form the Mississippi Confederation",
    "FWN": "Form the Federation of the West Indies",
}
DECISION_DESCS = {
    "IRO": "Unite the Five Nations of the Haudenosaunee under a single Great Council.",
    "HUR": "Unite the Wendat peoples of the Great Lakes under one confederacy.",
    "ILL": "Unite the clans of the Illinois country under one confederacy.",
    "CRE": "Unite the Muskogean peoples of the south under one nation.",
    "PUE": "Unite the Pueblo peoples of the high desert under one nation.",
    "SHA": "Unite the Shawnee of the Ohio country under one nation.",
    "BRZ": "Unite the provinces of Brazil under one crown.",
    "ARG": "Unite the provinces of the Rio de la Plata under one republic.",
    "MEX": "Unite the provinces of Mexico under one crown.",
    "PEU": "Unite the provinces of Peru under one crown.",
    "COL": "Unite the provinces of Colombia under one crown.",
    "BOL": "Unite the provinces of the Altiplano under one republic.",
    "GTM": "Unite the provinces of Central America under one crown.",
    "RCA": "Unite the provinces of California under one republic.",
    "GLC": "Unite the provinces of the Gulf Coast under one federation.",
    "MCP": "Unite the peoples of the Mississippi country under one confederation.",
    "FWN": "Unite the islands of the West Indies under one federation.",
}

# country_tags + defs. Vanilla standard: each def in its own common/countries/<Name>.txt
# (no TAG wrapper - the tag comes from the country_tags mapping), one tag per file.
# Def filename must not collide with a vanilla def file: the mod file would REPLACE the
# vanilla def (breaking vanilla Georgia for our American "Georgia"). Fall back to the
# tag as filename when the name collides, because the country_tags mapping is what binds.
vanilla_defs = set(os.listdir(GAME_COUNTRIES))
tag_lines = []
for r in REALMS + NEW_TRIBE_REALMS:
    if r["reuse"]:
        continue
    c = r["color"]
    names = " ".join(f'"{n}"' for n in r["names"])
    ideas = "\n\t".join(r["ideas"])
    def_fname = f"{r['name']}.txt"
    if def_fname in vanilla_defs:
        print(f"  note: def name '{def_fname}' collides with vanilla, using '{r['tag']}.txt'")
        def_fname = f"{r['tag']}.txt"
        assert def_fname not in vanilla_defs, f"def '{def_fname}' still collides with vanilla"
    tag_lines.append(f'{r["tag"]} = "countries/{def_fname}"')
    def_body = (
f"""graphical_culture = {r['graphical_culture']}

color = {{ {c[0]} {c[1]} {c[2]} }}

monarch_names = {{ {names} }}

historical_idea_groups = {{
\t{ideas}
}}

random_nation_chance = 0
""")
    w(f"{OUT}/common/countries/{def_fname}", def_body)
# formable region tags with a new def (ARG) get the same treatment
for f in design.FORMABLE_REGIONS:
    if not f.get("new_def"):
        continue
    c = f["color"]
    names = " ".join(f'"{n}"' for n in f["names"])
    ideas = "\n\t".join(f["ideas"])
    def_fname = f"{f['name']}.txt"
    if def_fname in vanilla_defs:
        print(f"  note: def name '{def_fname}' collides with vanilla, using '{f['tag']}.txt'")
        def_fname = f"{f['tag']}.txt"
        assert def_fname not in vanilla_defs, f"def '{def_fname}' still collides with vanilla"
    tag_lines.append(f'{f["tag"]} = "countries/{def_fname}"')
    def_body = (
f"""graphical_culture = {f['graphical_culture']}

color = {{ {c[0]} {c[1]} {c[2]} }}

monarch_names = {{ {names} }}

historical_idea_groups = {{
\t{ideas}
}}

random_nation_chance = 0
""")
    w(f"{OUT}/common/countries/{def_fname}", def_body)
if tag_lines:
    w(f"{OUT}/common/country_tags/zzz_states_of_the_new_world_countries.txt", "\n".join(tag_lines) + "\n")

# history/countries
def hist_body(r):
    rank = r["_rank"]
    reform = "feudalism_reform"
    hist = [f"government = monarchy",
            f"add_government_reform = {reform}",
            f"technology_group = {r.get('tech', 'high_american')}",
            f"unit_type = {r.get('unit', 'western')}",
            f"primary_culture = {r['_culture']}",
            f"religion = {r['_religion']}",
            f"capital = {r['capital']}",
            f"government_rank = {rank}"]
    body = "\n".join(hist) + "\n\n"
    m = r["monarchs"][0]
    body += f"1444.11.11 = {{\n\tmonarch = {{\n\t\tname = \"{m['name']}\"\n"
    if m.get("dynasty"):
        body += f"\t\tdynasty = \"{m['dynasty']}\"\n"
    body += f"\t\tadm = {m['adm']}\n\t\tdip = {m['dip']}\n\t\tmil = {m['mil']}\n"
    if m.get("regent"):
        body += "\t\tregent = yes\n"
    body += "\t}\n}\n"
    h = r.get("heir")
    if h:
        body += f"1444.11.11 = {{\n\their = {{\n\t\tname = \"{h['name']}\"\n"
        if h.get("dynasty"):
            body += f"\t\tdynasty = \"{h['dynasty']}\"\n"
        body += (f"\t\tbirth_date = {h['birth']}\n\t\tdeath_date = {h['death']}\n"
                 f"\t\tclaim = {h['claim']}\n\t\tadm = {h['adm']}\n"
                 f"\t\tdip = {h['dip']}\n\t\tmil = {h['mil']}\n\t}}\n}}\n")
    return body

for r in REALMS + TRIBE_REALMS + NEW_TRIBE_REALMS:
    fname = f"{VANILLA_HIST[r['tag']]}" if r["reuse"] else f"{r['tag']} - {r['name']}.txt"
    w(f"{OUT}/history/countries/{fname}", hist_body(r))

# restored vanilla tags: their country preamble gets a feudal monarchy + dev-derived rank.
# provinces/defs/flags/loc stay vanilla.  Read/write latin-1 (CLM/ITZ/MCA/TLA are not UTF-8).
def patch_restored_preamble(text, reform, rank):
    m = re.search(r"^\d{4}\.\d{1,2}\.\d{1,2}\s*=\s*\{", text, re.M)
    head_end = m.start() if m else len(text)
    head, tail = text[:head_end], text[head_end:]
    out, rank_w, reform_w, tech_w = [], False, False, False
    for ln in head.split("\n"):
        if ln[:1].isspace() or not ln.strip():
            out.append(ln)
            continue
        s = ln.strip()
        if s.startswith("government_rank"):
            out.append(f"government_rank = {rank}")
            rank_w = True
        elif s.startswith("government ") or s == "government =":
            out.append("government = monarchy")
        elif s.startswith("add_government_reform"):
            if not reform_w:
                out.append(f"add_government_reform = {reform}")
                reform_w = True
        elif s.startswith("technology_group"):
            out.append("technology_group = high_american")
            tech_w = True
        else:
            out.append(ln)
    if not tech_w:
        out.append("technology_group = high_american")
    if not reform_w:
        out.append(f"add_government_reform = {reform}")
    if not rank_w:
        out.append(f"government_rank = {rank}")
    body = "\n".join(out)
    if not body.endswith("\n"):
        body += "\n"
    return body + tail

def restore_override(tag, provs):
    cands = [f for f in os.listdir(GAME_HIST_CNT)
             if f.startswith(tag + " -") or f.startswith(tag + "- ")]
    assert cands, f"No vanilla history file for restored tag {tag}"
    fname = cands[0]
    raw = open(f"{GAME_HIST_CNT}/{fname}", "rb").read()
    text = raw.decode("latin-1")
    total = sum(vanilla_prov_dev(p) for p in provs)
    rank = gov_rank(tag, total)
    reform = "feudalism_reform"
    new = patch_restored_preamble(text, reform, rank)
    if 'name = "Native Council"' in new:
        fmn = first_monarch_name(tag)
        if fmn:
            new = new.replace('name = "Native Council"', f'name = "{fmn}"')
        new = re.sub(r"[ \t]*regent = yes\n", "", new, count=1)
    with open(f"{OUT}/history/countries/{fname}", "wb") as f:
        f.write(new.encode("latin-1"))
    print(f"  restored: {fname} (rank {rank})")

for tag, provs in design.RESTORED.items():
    restore_override(tag, provs)

# federation formable overrides: change_tag applies these instead of vanilla's
# government=native template
for f in design.FORMABLES:
    body = ("government = monarchy\nadd_government_reform = feudalism_reform\n"
            "technology_group = high_american\nunit_type = western\n"
            f"primary_culture = {f['culture']}\nreligion = {f['religion']}\n"
            f"capital = {f['capital']}\ngovernment_rank = 2\n\n")
    w(f"{OUT}/history/countries/{VANILLA_HIST[f['tag']]}", body)

# Argentina: new tag - history mirrors vanilla La Plata (republic + despot reform)
for f in design.FORMABLE_REGIONS:
    if f.get("new_def"):
        body = ("government = republic\nadd_government_reform = presidential_despot_reform\n"
                "technology_group = western\nunit_type = western\n"
                f"primary_culture = {f['culture']}\nreligion = {f['religion']}\n"
                f"capital = {f['capital']}\n\n")
        w(f"{OUT}/history/countries/{f['tag']} - {f['name']}.txt", body)

# history/provinces
import os as _os
_vanilla_prov_files = {}
for _f in _os.listdir(GAME_HIST_PROV):
    _m = re.match(r"^(\d+).*\.txt$", _f)
    if _m:
        _vanilla_prov_files.setdefault(_m.group(1), _f)
for r in REALMS + TRIBE_REALMS + NEW_TRIBE_REALMS:
    dev = r["dev"]
    cap = str(r["capital"])
    for pid in r["_ids"]:
        v = PROVS[pid]
        name = v.get("name", pid)
        d = [x + (1 if pid == cap else 0) for x in dev]
        body = (f"# {pid} - {name}\n\n"
                f"owner = {r['tag']}\ncontroller = {r['tag']}\n"
                f"culture = {r['_culture']}\nreligion = {r['_religion']}\n"
                f"is_city = yes\n"
                f"base_tax = {d[0]}\nbase_production = {d[1]}\nbase_manpower = {d[2]}\n"
                f"add_core = {r['tag']}\n"
                f"trade_goods = {r['trade_good']}\n")
        fname = _vanilla_prov_files.get(pid, f"{pid} - {name}.txt")
        if fname != f"{pid} - {name}.txt":
            print(f"  note: using vanilla filename {fname!r} for province {pid}")
        w(f"{OUT}/history/provinces/{fname}", body)

# localisation (BOM)
loc = ["l_english:"]
for r in REALMS:
    if not r["reuse"]:
        loc.append(f' {r["tag"]}:0 "{r["name"]}"')
        loc.append(f' {r["tag"]}_ADJ:0 "{r["adj"]}"')
# renamed reuse tags
loc.append(' ZAP:0 "Oaxaca"')
loc.append(' ZAP_ADJ:0 "Oaxacan"')
# new tribal tags (no vanilla loc; name+adj are the historical group)
for r in NEW_TRIBE_REALMS:
    loc.append(f' {r["tag"]}:0 "{r["name"]}"')
    loc.append(f' {r["tag"]}_ADJ:0 "{r["adj"]}"')
# formable region tags with new defs (ARG; BRZ keeps vanilla loc)
for f in design.FORMABLE_REGIONS:
    if f.get("new_def"):
        loc.append(f' {f["tag"]}:0 "{f["name"]}"')
        loc.append(f' {f["tag"]}_ADJ:0 "{f["adj"]}"')
# decision name/desc keys
for f in design.FORMABLES + design.FORMABLE_REGIONS:
    key = DECISIONS[f["tag"]]
    loc.append(f' {key}:0 "{DECISION_NAMES[f["tag"]]}"')
    loc.append(f' {key}_desc:0 "{DECISION_DESCS[f["tag"]]}"')
w(f"{OUT}/localisation/zzz_states_of_the_new_world_l_english.yml", "\n".join(loc) + "\n", bom=True)

# decisions
def fed_decision(f):
    key = DECISIONS[f["tag"]]
    tags = "\n".join(f"\t\t\t\ttag = {m}" for m in f["members"])
    owns = "\n".join(f"\t\t\towns_core_province = {p}" for p in f["provs"])
    cores = "\n".join(f"\t\t\tadd_core = {p}" for p in f["provs"])
    return f"""
	{key} = {{
		major = yes
		potential = {{
			was_never_end_game_tag_trigger = yes
			is_random_new_world = no
			NOT = {{ tag = {f['tag']} }}
			OR = {{
{tags}
			}}
		}}
		allow = {{
			is_at_war = no
{owns}
			NOT = {{ exists = {f['tag']} }}
		}}
		effect = {{
			change_tag = {f['tag']}
			on_change_tag_effect = yes
			add_prestige = 25
			if = {{
				limit = {{ NOT = {{ government_rank = 2 }} }}
				set_government_rank = 2
			}}
{cores}
			swap_non_generic_missions = yes
		}}
		ai_will_do = {{
			factor = 1
		}}
	}}"""

def region_decision(f):
    key = DECISIONS[f["tag"]]
    return f"""
	{key} = {{
		major = yes
		potential = {{
			was_never_end_game_tag_trigger = yes
			is_random_new_world = no
			NOT = {{ tag = {f['tag']} }}
			capital_scope = {{
				colonial_region = {f['colonial']}
				is_core = ROOT
			}}
		}}
		allow = {{
			is_at_war = no
			is_free_or_tributary_trigger = yes
			capital_scope = {{
				colonial_region = {f['colonial']}
				is_core = ROOT
			}}
			num_of_owned_provinces_with = {{
				value = {f['value']}
				region = {f['region']}
				is_city = yes
			}}
			NOT = {{ exists = {f['tag']} }}
		}}
		effect = {{
			change_tag = {f['tag']}
			on_change_tag_effect = yes
			add_prestige = 25
			if = {{
				limit = {{ NOT = {{ government_rank = 2 }} }}
				set_government_rank = 2
			}}
			{f['colonial']} = {{
				limit = {{ NOT = {{ owned_by = ROOT }} }}
				add_permanent_claim = {f['tag']}
			}}
			if = {{
				limit = {{ has_custom_ideas = no }}
				country_event = {{ id = ideagroups.1 }}
			}}
			set_country_flag = changed_from_colonial_nation
		}}
		ai_will_do = {{
			factor = 1
		}}
	}}"""

dec_body = "country_decisions = {\n"
for f in design.FORMABLES:
    dec_body += fed_decision(f)
for f in design.FORMABLE_REGIONS:
    dec_body += region_decision(f)
dec_body += "\n}\n"
w(f"{OUT}/decisions/zzz_states_of_the_new_world_formables.txt", dec_body)

# descriptor.mod
w(f"{OUT}/descriptor.mod",
  'name="States of the New World"\n'
  'path="mod/States of the New World"\n'
  'supported_version="1.37.*"\n')

print("\nDONE")
print(f"mod output: {OUT}")