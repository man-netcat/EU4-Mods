#!/usr/bin/env python3
"""Build the entire mod. One command, from the base game, CK3 and the spec.

    python3 tools/build.py

This file and tagdb.py are the whole build. tagdb.py holds the data - one Tag
object per realm, each carrying its areas and its provinces - and holds nothing
else. This file reads that data and turns it into files: the allocation, the
country files, the empire decision and the CK3 ruler sync.

The work used to be split across phase modules that had to be run in an order
nobody could remember. Two of those orders silently broke things: running
gen_countries before ck3ruler reverted all fifteen CK3-sourced rulers to their
hand-written pre-lift names, and letting the province files drift out of step
with the country files. In one file the order below is just the order the
statements run in, so neither bug has anywhere to hide.

Why probe runs before the cache is read
---------------------------------------
The allocation tables below are derived from cache/provdata.json when this file
loads, so the snapshot has to be refreshed above them rather than inside a build
step. That is why this looks like a phase that runs before the phases.
"""
from __future__ import annotations

import collections, json, os, pathlib, re, shutil, sys, time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
PROVDATA = CACHE / "provdata.json"
GAME = "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV"
MOD = HERE.parent
VANILLA_HISTORY = Path(GAME) / "history"

# Derived directories, defined once so that a module building one with
# os.path.join (a str) and another with / (a Path) cannot disagree.
VDIR = VANILLA_PDIR = Path(GAME) / "history" / "provinces"
VANILLA_CDIR = Path(GAME) / "history" / "countries"
PDIR = PROV_OUT = MOD / "history" / "provinces"
COUNTRY_OUT = MOD / "history" / "countries"

# tagdb is the data module: every Tag, every table.
from tagdb import *  # noqa: F401,F403


def vanilla_is_newer() -> bool:
    """True if the vanilla install looks newer than our snapshot of it."""
    if not PROVDATA.exists():
        return True
    try:
        return max(p.stat().st_mtime for p in VANILLA_HISTORY.rglob("*.txt")) > \
            PROVDATA.stat().st_mtime
    except OSError:
        return False



def parse(path):
    """Return (initial_scalars, initial_cores, all_cores, hre_any)."""
    txt = open(path, encoding="utf-8", errors="surrogateescape").read()
    lines = []
    for ln in txt.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        lines.append((len(ln) - len(ln.lstrip()), s))

    depth = 0
    started_dated = False
    scalars, cores0, cores_all = {}, [], []
    hre_any = False
    for _, s in lines:
        opens = s.count("{")
        closes = s.count("}")
        m = None
        if depth == 0 and not started_dated and "=" in s and not s.endswith("{"):
            m = s
        if depth == 0:
            if s.split("=")[0].strip().replace("_", "").isdigit() and "=" in s:
                started_dated = True
        if m:
            k, _, v = m.partition("=")
            k, v = k.strip(), re.split(r"#|//", v, 1)[0].strip()
            if k == "add_core":
                cores0.append(v)
                cores_all.append(v)
            else:
                scalars[k] = v
        else:
            for c in re.findall(r"add_core\s*=\s*([A-Z]{3})", s):
                cores_all.append(c)
        if re.search(r"\bhre\s*=\s*yes\b", s):
            hre_any = True
        depth += opens - closes
        if depth < 0:
            depth = 0
    return scalars, cores0, cores_all, hre_any


import re  # noqa: E402  (used by parse)


# The whole cache directory is gitignored, so on a fresh clone it does not exist
# and writing provdata.json into it raised FileNotFoundError. Created here rather
# than by build.py so probe.py also works when run on its own.
os.makedirs(CACHE, exist_ok=True)

PROV_DIR = os.path.join(GAME, "history", "provinces")
AREA = os.path.join(GAME, "map", "area.txt")
REGION = os.path.join(GAME, "map", "region.txt")


def parse_block_file(path):
    """Return list of (key, [lines]) top-level blocks."""
    text = open(path, encoding="utf-8", errors="replace").read()
    blocks = []
    cur_key, cur = None, []
    depth = 0
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            if cur_key is not None:
                cur.append(line)
            continue
        if depth == 0:
            m = re.match(r"^([A-Za-z0-9_]+)\s*=\s*\{", s)
            if m:
                cur_key, cur = m.group(1), [line]
                depth = 1
                continue
        else:
            cur.append(line)
            depth += s.count("{") - s.count("}")
            if depth == 0:
                blocks.append((cur_key, cur))
                cur_key, cur = None, []
    return blocks


def load_areas():
    areas = {}
    for key, lines in parse_block_file(AREA):
        ids = []
        for ln in lines[1:-1]:
            s = ln.strip()
            # skip "color = { ... }" and any other keyed sub-entry
            if re.match(r"^(color|provinces)\s*=", s):
                continue
            ids += [int(x) for x in re.findall(r"\d+", s)]
        areas[key] = sorted(set(ids))
    return areas


def load_region_areas():
    """region -> list of areas"""
    regions = {}
    for key, lines in parse_block_file(REGION):
        areas = []
        for ln in lines[1:-1]:
            m = re.match(r"^\s*([a-z0-9_]+)\s*$", ln)
            if m:
                areas.append(m.group(1))
        regions[key] = areas
    return regions


def load_provinces():
    """pid -> dict(owner, controller, cores[], culture, religion, hre, capital, name)"""
    provs = {}
    for fn in os.listdir(PROV_DIR):
        if not fn.endswith(".txt"):
            continue
        path = os.path.join(PROV_DIR, fn)
        m = re.match(r"^(\d+)\s*-\s*(.+)\.txt$", fn)
        if not m:
            continue
        pid, pname = int(m.group(1)), m.group(2)
        text = open(path, encoding="utf-8", errors="replace").read()
        d = {"id": pid, "name": pname, "file": fn, "cores": [],
             "owner": None, "controller": None, "culture": None,
             "religion": None, "hre": False, "capital": False, "sea": False}
        # only the pre-1444.11.11 (undated) block matters for ownership
        for ln in text.splitlines():
            s = ln.strip()
            if re.match(r"^\d+\.\d+\.\d+\s*=", s):
                break  # dated block -> stop, start state is above
            if s.startswith("#") or not s:
                continue
            if m2 := re.match(r"^owner\s*=\s*([A-Z0-9_]+)", s):
                d["owner"] = m2.group(1)
            elif m2 := re.match(r"^controller\s*=\s*([A-Z0-9_]+)", s):
                d["controller"] = m2.group(1)
            elif m2 := re.match(r"^add_core\s*=\s*([A-Z0-9_]+)", s):
                d["cores"].append(m2.group(1))
            elif m2 := re.match(r"^culture\s*=\s*([a-z0-9_]+)", s):
                d["culture"] = m2.group(1)
            elif m2 := re.match(r"^religion\s*=\s*([a-z0-9_]+)", s):
                d["religion"] = m2.group(1)
            elif m2 := re.match(r"^hre\s*=\s*(\w+)", s):
                d["hre"] = m2.group(1) == "yes"
            elif m2 := re.match(r"^is_city\s*=\s*(\w+)", s):
                d["is_city"] = m2.group(1) == "yes"
            elif m2 := re.match(r"^capital\s*=", s):
                d["capital"] = True
        provs[pid] = d
    return provs


def step_probe():
    areas = load_areas()
    regions = load_region_areas()
    provs = load_provinces()
    area_of = {}
    for a, ids in areas.items():
        for p in ids:
            area_of[p] = a
    region_of_area = {}
    for r, als in regions.items():
        for a in als:
            region_of_area[a] = r

    data = {"provs": provs, "areas": areas, "area_of": area_of,
            "region_of_area": region_of_area}
    with open(str(CACHE / "provdata.json"), "w") as f:
        json.dump(data, f)

    print(f"provinces: {len(provs)}  areas: {len(areas)}")
    print(f"hre=yes: {sum(1 for p in provs.values() if p['hre'])}")

    # owner tag -> provinces, only HRE + nearby
    hre_owners = defaultdict(list)
    for p in provs.values():
        if p["hre"]:
            hre_owners[p["owner"]].append(p["id"])
    print(f"\ndistinct owners inside HRE boundary: {len(hre_owners)}")
    for t, ids in sorted(hre_owners.items(), key=lambda x: -len(x[1]))[:40]:
        print(f"  {t:5} {len(ids):3}")


# Refresh the snapshot before anything reads it (see the module docstring).
if vanilla_is_newer():
    print("\n\033[1m==> probe vanilla province history\033[0m", flush=True)
    step_probe()
else:
    print("\n\033[1m==> probe\033[0m\n    cache is current, skipping")


# --------------------------------------------------------------------
# vanilla province and area data
# --------------------------------------------------------------------



# --------------------------------------------------------------------
# allocation and province files
# --------------------------------------------------------------------



_PROVDATA = json.load(open(str(CACHE / "provdata.json")))
# Vanilla province/area lookups the specification is resolved against.
provs = _PROVDATA["provs"]
AREAS = _PROVDATA["areas"]

_AREA_OF = _PROVDATA["area_of"]
_REGION_OF_AREA = _PROVDATA["region_of_area"]


def _owned(tag, region=None, exclude_regions=()):
    """Province ids owned by `tag` at the 1444.11.11 start, filtered by region.

    owner_1444, not the top-level `owner`. The top level of a vanilla province
    file is the state before any dated block fires, and 158 provinces have an
    owner or core change dated inside (867, 1444]. Erzincan is the case in point:
    top level says TIM with add_core = TIM, but a 1402.1.1 block gives it to the
    Aq Qoyunlu and removes the Timurid core. This mod ships no defines.lua, so it
    runs on vanilla's 1444.11.11 start and the resolved value is the true one.
    """
    if isinstance(exclude_regions, str):
        exclude_regions = (exclude_regions,)
    out = []
    for pid, pr in _PROVDATA["provs"].items():
        if pr.get("owner_1444", pr.get("owner")) != tag:
            continue
        reg = _REGION_OF_AREA.get(_AREA_OF.get(pid))
        if region is not None and reg != region:
            continue
        if reg in exclude_regions:
            continue
        out.append(int(pid))
    return sorted(out)


def _region(pid):
    """Region of a province id, via its area. None if the area is unknown."""
    return _REGION_OF_AREA.get(_AREA_OF.get(str(pid)))


def _area(*areas):
    """Province ids belonging to any of the named areas, sorted and de-duped.

    Used where a transfer was specified as "these areas" rather than as a list
    of province ids, so the code says what was asked for instead of hiding it
    behind 17 bare numbers. Province membership comes from provdata's `areas`
    index, which is the same source _owned() reads owners from, so an area and
    the provinces in it can never disagree.
    """
    out = set()
    for area in areas:
        out |= {int(pid) for pid in _PROVDATA["areas"].get(area, ())}
    return sorted(out)


# ARABIA_MAMLUK is the Mamluks' land OUTSIDE Egypt, and it is the only part of
# vanilla MAM that the Abbasids take: Palestine, Transjordan and the Hejaz coast.
# horn_of_africa_region is excluded because Suakin (1232) and Halaib (2324) are
# Red Sea / Beja land which the Mamluks ruled as Sudan, and Egypt kept those two
# when the Mamluks were folded into the EGY tag (see EGY_ALL).

# Tag lists live in tagdb.py, which every other tool imports too. They used to
# be copied into four scripts and the copies drifted - gen_countries still
# treated Lusatia as a partition kingdom while the mod's own localisation had
# always described a five-kingdom empire with Lusatia outside it.
#
# The aliases below are kept because half the file refers to them by these names.

# Why: docs/DESIGN.md - How land is allocated
UNTRACKED_OWNERS = {
    112: "VEN",
}


#: Layer 2 in the order the allocator reads it: the untracked holder first, then
#: everything the database declares. Every province appears exactly once, so this
#: ordering carries no meaning - the allocator deliberately makes one province's
#: claim beat its area's regardless of where it sits in the dict.
PROVINCE_OWNERS = {**UNTRACKED_OWNERS, **PROVINCE_OWNERS}

#: Capitals and names for the realms whose country file this generator writes.
#: Both are Tag fields; this is the projection this script reads.

#: The realms whose province files carry an explicit capital, keyed as before.
#: That set is exactly the realms taking whole areas in layer 1 - the partition
#: proper. The single-province carve-outs (Silesia, Great Moravia, Navarra) are
#: tagged with a capital too, but they hold a province or two rather than a
#: region, and no capital is declared on their behalf.
CAPITAL = {tag: BY_TAG[tag].capital for tag in AREA_OWNERS}
NAME = {tag: BY_TAG[tag].name for tag in AREA_OWNERS}


# The named land blocks - BYZ_ALL, ARABIA_ALL, BUL_ALL, MOGYERS_LEVIDIA and the
# rest - live in tagdb.py, so a tag's land is not defined in two files at
# once. They are computed from the same provdata cache, by the same _owned() and
# _area() helpers, as they were when they sat below in this file.


# The two province-FILE text transforms, and the constants only they use. These
# rewrite a file's text rather than naming land, so they stay here with the
# writer that calls them.

# There is deliberately no tag-rename pass here. A tag that takes land it did not
# hold in 867 gets its own core added by patch() the same way every other realm
# does; the province keeps the core it already had. Rewriting those tags out of
# the file - MAM into EGY, say - would mean the mod's one realm with a special
# rule was also the one realm quietly losing history.


# Why: docs/DESIGN.md - Cultures that do not exist in 867 (CULTURE_GONE_867)

CULTURE_GONE_867 = {"turkish": "greek", "pontic_greek": "greek"}

# CONQUERED_BY_THE_ARABS - the five of those 32 that the Abbasids hold, and which
# therefore keep Muslim religion. Adana 327, Marash 332, Malatya 2303, Ayntab 4298
# and Divrigi 4310. Ayntab and Divrigi really had fallen to the Arabs by 867
# (851 and 855); the other three were still Byzantine and fall in 895-979, so they
# are this mod's deliberate early conquest rather than a 867 record. Named
# explicitly so the rule reads as "Byzantine land, minus what the Arabs took"
# instead of "whatever tag happens to be holding it today".
CONQUERED_BY_THE_ARABS = {327, 332, 2303, 4298, 4310}


# Two Muslim denominations turn up among the 33 Turkish-culture provinces, not
# one: 26 are sunni, and Malatya 2303, Sivas 329 and Divrigi 4310 are shiite. A
# rewrite that only matched `sunni` left Sivas as greek + shiite on Byzantine land,
# so both are matched here. Malatya and Divrigi are Arab-held and so keep theirs
# either way; Sivas is the one that silently went wrong.
MUSLIM_RELIGIONS_867 = ("sunni", "shiite")

# Why: docs/DESIGN.md - One province whose own comment disagrees (CULTURE_COMMENT_NOTES)
CULTURE_COMMENT_NOTES = {
    318: "# The \"not Greek\" warning below is a 1444 note, not an 867 one. Vanilla\n"
         "# is right about its own date: the Aydinids took Smyrna c. 1330. This\n"
         "# scenario is 867, when it was Byzantine Greek - the Saracen raid on the\n"
         "# city is 869, two years after the start date.",
}


def apply_867_culture(text, pid):
    """Rewrite culture (and religion) for provinces whose vanilla culture is later
    than 867. Culture is rewritten once, at the top-level province block; religion
    is rewritten everywhere it appears, because a dated block that re-sets
    religion would otherwise leave the province Muslim after 1444."""
    m = re.search(r"^(\s*)culture\s*=\s*(\w+)", text, re.M)
    if not m:
        return text
    culture = CULTURE_GONE_867.get(m.group(2))
    if not culture:
        return text
    text = (text[:m.start()]
            + f"{m.group(1)}culture = {culture}"
            + text[m.end():])
    if pid not in CONQUERED_BY_THE_ARABS:
        text = re.sub(rf"^(\s*religion\s*=\s*)({'|'.join(MUSLIM_RELIGIONS_867)})\b",
                      r"\1orthodox", text, flags=re.M)
    note = CULTURE_COMMENT_NOTES.get(pid)
    if note:
        text = text.replace(f"culture = {culture}",
                            f"{note}\n{m.group(1)}culture = {culture}", 1)
    return text

# The rest of the Ottomans, i.e. neither cored nor Anatolian. Ten, all Balkan:
# Tarnovo, Silistria, Nis, Vidin, Plovdiv, Skopje, Kostendil, Tirnovo, Tolcu,
# Ohrid. Vlore used to be here and moved to Byzantium with the rest of Albania.




# vanilla EGY owns nothing at all, so _owned("EGY") would return an empty list.
# The rest of the Ottomans, i.e. neither cored nor Anatolian. Ten, all Balkan:
# Tarnovo, Silistria, Nis, Vidin, Plovdiv, Skopje, Kostendil, Tirnovo, Tolcu,

# ------------------------------------------------------------------ combine --

# Layer 3, in order. A later entry wins any overlap with an earlier one (which is
# why Albania sits after Anatolia and why BYZ_GREECE is last of all). The order
# and the province lists both come from the database now - see Tag.grants and
# Tag.grant_order in tagdb.py, which is where a realm declares what blocks it
# takes and in what precedence.

LAYER2_MOVES: list = []


def build(verbose=False):
    """{tag: [province ids]} - the whole allocation. The one answer.

    Areas, then loose provinces, then transfers, in that order and only in that
    direction. Filtered to the tags the mod actually hands provinces to, so a tag
    that only appears in a comment or an area list cannot leak into the result.
    """
    LAYER2_MOVES.clear()
    alloc: dict = {}
    owner_of: dict = {}
    overlaps = []

    # Layer 1: areas.
    for tag, areas in AREA_OWNERS.items():
        ids = []
        for area in areas:
            for pid in AREAS.get(area, ()):
                pr = provs.get(str(pid))
                if not (pr and pr.get("owner")):
                    continue
                ids.append(pid)
                if pid in owner_of:
                    overlaps.append((pid, owner_of[pid], tag))
                else:
                    owner_of[pid] = tag
        alloc[tag] = sorted(set(ids))
    if overlaps:
        raise SystemExit(
            "build.py: provinces claimed by two areas, fix AREA_OWNERS: "
            + ", ".join(f"{p} ({a} and {b})" for p, a, b in overlaps))

    # Layer 2: loose provinces, applied after every area so one always beats its
    # area regardless of the order the dict is written in.
    for pid, tag in PROVINCE_OWNERS.items():
        prev = owner_of.get(pid)
        owner_of[pid] = tag
        if prev in alloc:
            alloc[prev] = [p for p in alloc[prev] if p != pid]
        alloc.setdefault(tag, [])
        if pid not in alloc[tag]:
            alloc[tag] = sorted(alloc[tag] + [pid])
        LAYER2_MOVES.append((pid, provs[str(pid)]["name"], prev, tag))

    # Layer 3: transfers. `claimed` deliberately includes the tag's own
    # provinces: the point is to add unclaimed land, never to move land a tag
    # already holds, which is what lets the layers compose with no precedence
    # table.
    for tag, extra in TRANSFERS:
        claimed = set(alloc.get(tag, ()))
        for other in alloc:
            if other != tag:
                claimed |= set(alloc[other])
        alloc[tag] = sorted(set(alloc.get(tag, [])) |
                            {p for p in extra if p not in claimed})

    if verbose:
        for pid, name, prev, tag in LAYER2_MOVES:
            print(f"  override: province {pid} {name} {prev} -> {tag}")
    return {t: sorted(alloc[t]) for t in ALL_TAGS if t in alloc and alloc[t]}


def owner_map(alloc=None):
    """{province id: tag}, for callers asking about one province at a time."""
    alloc = build() if alloc is None else alloc
    return {p: t for t, ps in alloc.items() for p in ps}


# Why: docs/DESIGN.md - Where the 867 empire was (EMPIRE_CORE_AREAS)
EMPIRE_CORE_AREAS = (
    "alsace_area", "austria_proper_area", "bourgogne_area", "brabant_area",
    "braunschweig_area", "carinthia_area", "catalonia_area", "central_italy_area",
    "champagne_area", "corsica_sardinia_area", "east_bavaria_area",
    "emilia_romagna_area", "flanders_area", "franconia_area", "frisia_area",
    "guyenne_area", "hesse_area", "holland_area", "ile_de_france_area",
    "inner_austria_area", "languedoc_area", "lazio_area", "liguria_area",
    "loire_area", "lombardy_area", "lorraine_area", "lower_bavaria_area",
    "lower_rhineland_area", "lower_saxony_area", "lower_swabia_area",
    "massif_central_area", "normandy_area", "north_brabant_area",
    "north_rhine_area", "north_westphalia_area", "northern_saxony_area",
    "orleans_area", "palatinate_area", "picardy_area", "piedmont_area",
    "po_valley_area", "poitou_area", "provence_area", "pyrenees_area",
    "romandie_area", "savoy_dauphine_area", "south_saxony_area",
    "switzerland_area", "thuringia_area", "tirol_area", "tuscany_area",
    "upper_bavaria_area", "upper_franconia_area", "upper_rhineland_area",
    "upper_swabia_area", "venetia_area", "wallonia_area", "weser_area",
    "west_burgundy_area", "westphalia_area",
)

# Why: docs/DESIGN.md - The eleven non-imperial provinces inside those areas (NOT_IMPERIAL_867)
NOT_IMPERIAL_867 = {
    59, 61, 112, 118, 120, 127, 2965, 2986, 2988, 4735, 4744,
}


def empire_core():
    """The provinces the 867 empire held, from EMPIRE_CORE_AREAS minus
    NOT_IMPERIAL_867. Sorted, and the same 226 the old five-tag list produced."""
    core = set()
    for area in EMPIRE_CORE_AREAS:
        for pid in AREAS.get(area, ()):
            if pid not in NOT_IMPERIAL_867 and provs.get(str(pid), {}).get("owner"):
                core.add(pid)
    return sorted(core)


def dev(pid):
    """base_tax + base_production, for the report's balance column."""
    for fn in os.listdir(VANILLA_PDIR):
        if re.match(rf"^{pid}\s*-", fn):
            txt = open(os.path.join(VANILLA_PDIR, fn), encoding="utf-8",
                       errors="replace").read()
            ta = re.search(r"base_tax\s*=\s*([\d.]+)", txt)
            pr = re.search(r"base_production\s*=\s*([\d.]+)", txt)
            return ((float(ta.group(1)) if ta else 0.0)
                    + (float(pr.group(1)) if pr else 0.0))
    return 0.0


PROV_DATE = "1444.11.11"  # the mod's start date


def force_block(new_owner):
    """Dated block that re-asserts our ownership at the start date.

    EU4 fires every dated history entry up to and including the start date,
    in file order, AFTER the undated baseline. Vanilla therefore overrides
    the undated owner/controller for any province it hands over before
    1444.11.11 - Verona to Venice in 1405, Aquitaine to England in 1306,
    Avignon to the Pope in 1274, East Frisia to EFR, and so on. Patching only
    the undated header is not enough, so the province gets a final dated block
    that wins. Appending it last also means we override vanilla, not the
    other way round, and add_core/hre are re-stated because the same pre-1444
    events can drop a core or re-enable the empire flag.
    """
    return (
        f"\n{PROV_DATE} = {{\towner = {new_owner}\n"
        f"\tcontroller = {new_owner}\n"
        f"\tadd_core = {new_owner}\n"
        f"\thre = no\n"
        f"}} # The Karolingians: hold the 867 partition at the 1444 start\n"
    )


def unown(text):
    """Strip owner and controller so the province starts unowned.

    An unowned province is a normal EU4 state, not a trick: 1472 vanilla
    provinces have no owner at all, land included (Grain Coast, Kumasi,
    Pensacola), and their files simply carry no `owner` key. A mod province
    file replaces the vanilla one for that id, so deleting the key is enough.

    Cores are deliberately kept. These three are Hungarian land being parked
    for the Balaton tag, and leaving them HUN-cored means Balaton can inherit
    them without anyone having to remember which provinces they were.
    """
    lines = text.splitlines()
    dated_start = len(lines)
    for idx, ln in enumerate(lines):
        if re.match(r"^\d+\.\d+\.\d+\s*=", ln.strip()):
            dated_start = idx
            break
    out = [ln for idx, ln in enumerate(lines)
           if idx >= dated_start or not re.match(r"^(owner|controller)\s*=", ln.strip())]
    return "\n".join(out) + (
        f"\n# The Karolingians: unowned, held for the Balaton tag\n")


def patch(text, new_owner):
    """Rewrite the start-state (undated) portion of a province file."""
    out, i, n = [], 0, len(text.splitlines())
    lines = text.splitlines()
    # locate end of the undated header: first dated block
    dated_start = len(lines)
    for idx, ln in enumerate(lines):
        s = ln.strip()
        if re.match(r"^\d+\.\d+\.\d+\s*=", s):
            dated_start = idx
            break

    for idx, ln in enumerate(lines):
        if idx >= dated_start:
            out.append(ln)
            continue
        s = ln.strip()
        # --- hre flag -------------------------------------------------
        if re.match(r"^hre\s*=", s):
            out.append(re.sub(r"hre\s*=\s*\w+", "hre = no", ln))
            continue
        # --- owner / controller --------------------------------------
        m = re.match(r"^(owner|controller)\s*=\s*", s)
        if m:
            indent = ln[:len(ln) - len(ln.lstrip())]
            out.append(f"{indent}{m.group(1)} = {new_owner}")
            continue
        # --- add_core: remember existing, append ours at end of header --
        out.append(ln)

    # inject our core just before the first dated block (end of header).
    # Skip it when the vanilla file already grants this core - Morea and
    # Constantinople ship `add_core = BYZ` and are now in the allocation, so
    # without this they would end up with the line twice.
    have_core = any(re.match(rf"^\s*add_core\s*=\s*{re.escape(new_owner)}\s*$", lines[idx])
                    for idx in range(dated_start))
    core_line = f"add_core = {new_owner}"
    if have_core:
        return "\n".join(out) + "\n" + force_block(new_owner)
    # find insertion point: after the last add_core in header, else at end
    ins = dated_start
    last_core = None
    for idx in range(dated_start):
        if re.match(r"^\s*add_core\s*=", lines[idx]):
            last_core = idx
    if last_core is not None:
        ins = last_core + 1
        out.insert(ins, core_line)
    else:
        out.insert(dated_start, core_line)

    return "\n".join(out) + "\n" + force_block(new_owner)


def step_provinces(argv):
    alloc = build(verbose="--report" in argv)
    # every allocated province, gifts included - note Venezia is NOT in here:
    # it is deliberately left vanilla so the base game creates it.
    owner_of = {p: t for t, ps in alloc.items() for p in ps}

    # every province that must be written: the partition + every hre=yes
    provs = _PROVDATA["provs"]
    hre_yes = {int(p) for p, pr in provs.items() if pr["hre"]}
    todo = sorted(set(owner_of) | hre_yes | set(BALATON_RESERVED))

    if os.path.isdir(PROV_OUT):
        shutil.rmtree(PROV_OUT)
    os.makedirs(PROV_OUT, exist_ok=True)

    written = 0
    for pid in todo:
        src = None
        for fn in os.listdir(VANILLA_PDIR):
            if re.match(rf"^{pid}\s*-.*\.txt$", fn):
                src = os.path.join(VANILLA_PDIR, fn)
                break
        if not src:
            print(f"!! no vanilla file for province {pid}")
            continue
        text = apply_867_culture(
            open(src, encoding="utf-8", errors="surrogateescape").read(), pid)
        tag = owner_of.get(pid)
        if pid in BALATON_RESERVED:
            new = unown(text)
        else:
            new = patch(text, tag) if tag else text
        # Global HRE strip at ANY depth: catches the initial flag plus later
        # dated events such as 1464.1.1 East Frisia / 1548.6.26 Flanders that
        # would otherwise re-join the empire long after 1444.
        new = re.sub(r"(\bhre\s*=\s*)yes\b", r"\1no", new)
        open(os.path.join(PROV_OUT, os.path.basename(src)), "w",
             encoding="utf-8", errors="surrogateescape").write(new)
        written += 1

    print(f"wrote {written} province files")
    for tag, ps in sorted(alloc.items(), key=lambda kv: -len(kv[1])):
        print(f"  {tag:4} {len(ps):3}")
    print(f"  hre=yes stripped : {len(hre_yes)}")
    print(f"  total            : {len(todo)}")


def report(alloc):
    """Balance report. Writes nothing - the diagnostic half of the pipeline."""
    owner_of = owner_map(alloc)
    caps = {}
    for fn in os.listdir(VANILLA_CDIR):
        if not fn.endswith(".txt"):
            continue
        tag = fn.split(" ")[0].split("-")[0].strip()
        m = re.search(r"^\s*capital\s*=\s*(\d+)", open(
            os.path.join(VANILLA_CDIR, fn), encoding="utf-8",
            errors="replace").read(), re.M)
        if m:
            caps[tag] = int(m.group(1))
    total = 0
    for tag in sorted(alloc, key=lambda t: -len(alloc[t])):
        ids = alloc[tag]
        cap = CAPITAL.get(tag)
        if cap is not None:
            assert cap in ids, f"{tag} capital {cap} not in its own area set!"
        olds = defaultdict(int)
        for pid in ids:
            olds[provs[str(pid)]["owner"]] += 1
        hre = sum(1 for pid in ids if provs[str(pid)]["hre"])
        print(f"{tag} {NAME.get(tag, tag):13} n={len(ids):3} dev={sum(dev(p) for p in ids):6.0f}"
              + (f" cap={cap}({provs[str(cap)]['name']})" if cap else "")
              + f" hre={hre}")
        print("     from: " + " ".join(f"{k}:{v}" for k, v in
                                       sorted(olds.items(), key=lambda x: -x[1])))
        total += len(ids)
    print("=" * 78)
    print(f"{len(owner_of)} provinces reassigned")


# --------------------------------------------------------------------
# gen_hre_decision
# --------------------------------------------------------------------




d = json.load(open(str(CACHE / "provdata.json")))
area_of = d["area_of"]

# The empire is defined by where it was in 867, not by who holds it. There is no
# list of eligible tags here and no realm that is privileged: the requirement is
# land, and any tag that comes to hold all of it may form the empire. That
# includes Lusatia, Brittany, and anything added later - none of which is named
# as an outsider anywhere in this file, because none of them is one.
#
# empire_core() comes from build.py, where the 60 areas and the 11
# documented non-imperial provinces live, so the decision cannot disagree with
# the rest of the mod about where the empire was.
empire_provs = empire_core()
areas = sorted({area_of[str(p)] for p in empire_provs})

all_areas = set(re.findall(r"^\t*([a-z_]+) = \{",
    open(f"{GAME}/map/area.txt", encoding="utf-8", errors="replace").read(), re.M))
missing = [a for a in areas if a not in all_areas]
assert not missing, f"unknown areas: {missing}"

T = "\t"
area_or = "\n".join(f"{T*4}area = {a}" for a in areas)
claims = "\n".join(
    f"{T*3}{a} = {{\n"
    f"{T*4}limit = {{\n"
    f"{T*5}NOT = {{ is_core = ROOT }}\n"
    f"{T*5}NOT = {{ is_permanent_claim = ROOT }}\n"
    f"{T*4}}}\n"
    f"{T*4}add_permanent_claim = ROOT\n"
    f"{T*3}}}" for a in areas)
# allow: land, and nothing else. "NOT = { <id> = { ... } }" is true when that
# province is not held by you or your non-sovereign subjects, so requiring every
# one of them to be false means holding all of them.
held = "\n".join(
    f"{T*4}NOT = {{ {p} = {{ country_or_non_sovereign_subject_holds = ROOT }} }}"
    for p in empire_provs)

txt = f"""# The Karolingians - "Unite the Karlings"
#
# The imperial title has no land at all in 867, because the empire is split
# among its heirs. Once one ruler holds the old imperial heartlands in a single
# hand the empire can be made whole again. This mirrors vanilla's own "form
# Germany" / "Restore Roman Empire" decisions and uses change_tag, so the
# country really becomes HLR rather than merely renaming itself.
#
# Any ruler who comes to hold that land may do this. The decision names no
# realm as eligible or ineligible, because the empire is a place, not a set of
# dynasties: whether the five Frankish kingdoms, Lusatia, or anyone else
# reunites it is the game's business, not this file's.

country_decisions = {{

\tkar_form_hre = {{
\t\tmajor = yes

\t\tpotential = {{
\t\t\tNOT = {{ map_setup = map_setup_random }}
\t\t\tNOT = {{ tag = HLR }}
\t\t\tNOT = {{ has_country_flag = kar_formed_hre }}
\t\t\tNOT = {{ exists = ROM }}
\t\t\tNOT = {{ exists = ARH }}
\t\t\tis_free_or_tributary_trigger = yes
\t\t\tis_nomad = no
\t\t\tOR = {{
\t\t\t\tai = no
\t\t\t\tAND = {{
\t\t\t\t\tai = yes
\t\t\t\t\tnum_of_cities = 40
\t\t\t\t}}
\t\t\t}}
\t\t\t# No tag test at all. Whichever ruler ends up holding the old imperial
\t\t\t# land may try, so no realm is excluded for being the realm it is.
\t\t\t# The land requirement in allow is the entire test.
\t\t}}

\t\tprovinces_to_highlight = {{
\t\t\tOR = {{
{area_or}
\t\t\t}}
\t\t\tNOT = {{ country_or_non_sovereign_subject_holds = ROOT }}
\t\t}}

\t\tallow = {{
\t\t\tis_at_war = no
\t\t\tis_free_or_tributary_trigger = yes
\t\t\t# One ruler holding every imperial province. There is deliberately no
\t\t\t# "and not one province more" clause, and no requirement that any
\t\t\t# particular realm have died out: both described the five-kingdom
\t\t\t# partition, and neither is a fact about the empire itself.
{held}
\t\t}}

\t\teffect = {{
\t\t\tchange_tag = HLR
\t\t\ton_change_tag_effect = yes
\t\t\tchange_government_to_monarchy = yes
\t\t\tset_country_flag = kar_formed_hre
\t\t\thidden_effect = {{
\t\t\t\tset_government_rank = 3
\t\t\t}}
\t\t\tif = {{
\t\t\t\tlimit = {{ has_dlc = "Domination" }}
\t\t\t\tadd_government_reform = holy_imperial_monarchy_reform
\t\t\t}}
\t\t\tadd_prestige = 25
\t\t\tadd_legitimacy = 10

\t\t\t# claim the rest of the former empire for good
{claims}
\t\t}}
\t}}
}}
"""


def step_hre() -> None:
    """Write decisions/KarolingianHRE.txt from the finished allocation."""
    os.makedirs(os.path.join(MOD, "decisions"), exist_ok=True)
    p = os.path.join(MOD, "decisions", "KarolingianHRE.txt")
    open(p, "w", encoding="utf-8").write(txt)
    print(f"wrote {p}")
    print(f"  imperial provinces    : {len(empire_provs)}")
    print(f"  areas covered         : {len(areas)}")
    print(f"  eligible tags         : any - the requirement is land, not a tag list")

# --------------------------------------------------------------------
# check_start
# --------------------------------------------------------------------



START_DT = (1444, 11, 11)
# The allocation is not re-derived here. It comes from build.build(), which is
# the single specification of who owns what; this file's only job is to replay
# the written province files up to the start date and check the result. An
# earlier version read cache/alloc.json directly, which checked none of the
# eastern transfers because those live in the generator, and a still earlier one
# kept its own copy of the tag list, which drifted.

DATE_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)\s*=\s*\{")
KV_RE = re.compile(r"\b(owner|controller|add_core|remove_core)\s*=\s*([A-Za-z0-9_]+)")
HRE_RE = re.compile(r"\bhre\s*=\s*(\w+)")


def split_header_and_blocks(lines):
    """Yield (date_or_None, block_text) for the header and each dated block."""
    i = 0
    n = len(lines)
    header = []
    while i < n and not DATE_RE.match(lines[i].strip()):
        header.append(lines[i])
        i += 1
    yield None, "\n".join(header)
    while i < n:
        m = DATE_RE.match(lines[i].strip())
        if not m:
            i += 1
            continue
        date = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        depth = lines[i].count("{") - lines[i].count("}")
        body = [lines[i]]
        i += 1
        while i < n and depth > 0:
            depth += lines[i].count("{") - lines[i].count("}")
            body.append(lines[i])
            i += 1
        yield date, "\n".join(body)


def effective(text):
    """Owner/controller/cores as of START_DT."""
    owner = controller = None
    cores = set()
    hre = None
    for date, block in split_header_and_blocks(text.splitlines()):
        if date is not None and date > START_DT:
            continue
        for key, val in KV_RE.findall(block):
            if key == "owner":
                owner = val
            elif key == "controller":
                controller = val
            elif key == "add_core":
                cores.add(val)
            elif key == "remove_core":
                cores.discard(val)
        h = HRE_RE.search(block)
        if h:
            hre = h.group(1)
    return owner, controller, cores, hre


def step_start():
    alloc = build()
    expected = {}
    for t in TAGS:
        for p in alloc.get(t, []):
            expected[int(p)] = t

    bad_owner, bad_ctrl, bad_hre, contested = [], [], [], []
    for fn in sorted(os.listdir(PDIR)):
        pid = int(re.match(r"^(\d+)", fn).group(1))
        text = open(os.path.join(PDIR, fn), encoding="utf-8",
                    errors="surrogateescape").read()
        owner, controller, cores, hre = effective(text)
        want = expected.get(pid)
        if want is None:
            continue
        if owner != want:
            bad_owner.append((pid, fn, want, owner))
        if controller != want:
            bad_ctrl.append((pid, fn, want, controller))
        if hre == "yes":
            bad_hre.append((pid, fn))
        if want in cores:
            contested.append((pid, fn))

    print(f"provinces checked against the {START_DT[0]}.{START_DT[1]}.{START_DT[2]} start: {len(expected)}")
    print(f"  owner    != intended : {len(bad_owner)}")
    print(f"  controller!= intended: {len(bad_ctrl)}")
    print(f"  hre = yes at start   : {len(bad_hre)}")
    for pid, fn, want, got in bad_owner[:20]:
        print(f"     {pid:5} {fn[:30]:30} want {want} got {got}")
    for pid, fn in bad_hre[:10]:
        print(f"     {pid:5} {fn[:30]:30} hre = yes")
    if bad_owner or bad_ctrl or bad_hre:
        print("\nFAIL: pre-1444 vanilla events still win at the start date")
        return 1
    print("\nOK: every intended province is held at the start date")
    return 0


# --------------------------------------------------------------------
# CK3 title map and ruler lookup
# --------------------------------------------------------------------


import os
import re
import sys

GAME_CK3 = "/mnt/data/SteamLibrary/steamapps/common/Crusader Kings III/game"

# CK3's only bookmark, and the date this mod's flavour is taken from. Kept as a
# string because it is also spliced into regexes when scanning dated blocks.
DATE = "867.1.1"

# CK3 supplies each realm's 867 name and dynasty. Which title, and which realms
# are not CK3's to supply, are stated once on the Tag in tagdb.py, as ck3_title
# and no_ck3; this file only reads them. Adding a realm is one line there.
#
# Why: docs/DESIGN.md - How a realm's 867 ruler is found.


# An heir belongs to the ruler's dynasty unless a succession deliberately changed
# it. Listing a tag here opts its heir out of the sync in step_ck3(); there are no
# such cases at the moment, but a realm whose heir starts a new house should say
# so here rather than have --fix quietly overwrite it.
HEIR_DYNASTY_OVERRIDE = {}


# CK3 bug to work around, not a mod choice.
#
# common/dynasty_houses/00_dynasty_houses.txt declares
#     house_abbasid = { name = dynn_Abbasid  dynasty = 7296 }
# but 7296 is declared in common/dynasties as dynn_Hashimid. So the Abbasid
# house points at the Hashimid dynasty, and copying the nested dynasty would give
# al-Mu'tazz - an Abbasid caliph in CK3's own history - a Hashimid dynasty name.
# The house's own name key is correct and is what the mod uses, so a house is
# preferred over the dynasty it nests, and this entry records why.
#
# Note the house declares `name = dynn_Abbasid` WITHOUT quotes, unlike every
# other house in the file. That is why the house parser accepts both quoted and
# bare name values.
HOUSE_NAME_OVERRIDE = {
    "house_abbasid": "dynn_Abbasid",
}


def _date_key(s: str) -> tuple:
    p = [int(x) for x in s.split(".")]
    return tuple(p + [0] * (3 - len(p)))


def _norm(text: str) -> str:
    """Normalise line endings.

    CK3 ships some files with CRLF and some with LF, and the character files are
    mixed. The brace-walking below matches `key = {` at the start of a line, so a
    stray \\r does not break the block boundaries it relies on.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _blocks(text: str):
    """Yield (head, body) for every top-level `key = { ... }` in a Paradox file."""
    for m in re.finditer(r"^([a-zA-Z_0-9]+)\s*=\s*\{", text, re.M):
        i = m.end() - 1
        d = 0
        while i < len(text):
            if text[i] == "{":
                d += 1
            elif text[i] == "}":
                d -= 1
                if d == 0:
                    break
            i += 1
        yield m.group(1), text[m.end():i]


def _inner_blocks(body: str):
    """Yield (key, body) for nested blocks.

    Key charset includes `.` because these are dated history blocks ("867.1.1")
    as well as named ones ("holder"), and the dated ones are the whole point of
    walking history/titles. The leading [ \t]* is load-bearing: every nested block
    inside a title is indented with a tab, so anchoring at "^" with no indent
    allowance matches nothing at all and silently yields zero blocks.
    """
    for m in re.finditer(r"^[ \t]*([a-zA-Z_0-9.]+)\s*=\s*\{", body, re.M):
        i = m.end() - 1
        d = 0
        while i < len(body):
            if body[i] == "{":
                d += 1
            elif body[i] == "}":
                d -= 1
                if d == 0:
                    break
            i += 1
        yield m.group(1), body[m.end():i]


# ---------------------------------------------------------------- CK3 data ---

def load_titles():
    """title id -> list of (date, body) for its dated history blocks."""
    out = {}
    for f in sorted((Path(GAME_CK3) / "history" / "titles").glob("*.txt")):
        text = _norm(f.read_text(errors="replace")).lstrip("\ufeff")
        for tid, body in _blocks(text):
            out.setdefault(tid, []).extend(_inner_blocks(body))
    return out


def holder_at(title, titles):
    """Character id holding `title` on DATE, or None."""
    return holder_at_exact(title, titles)[0]


def holder_at_exact(title, titles):
    """(holder, carried_block_date_or_None) for `title` on DATE.

    CK3 does not write a holder into every title's DATE block. k_egypt's holder
    is set at 866.1.1; k_france, k_italy, k_lotharingia and k_east_francia carry
    their holders forward from 840/843/855/866 with nothing dated 867 at all. That
    is normal - the state is real, it is simply recorded by continuity - so the
    holder is still returned. But the caller is told which block it came from,
    because a naive "last block wins" cannot tell continuity apart from a title
    that simply stopped being updated, and mistaking one for the other would
    report a confident wrong name.
    """
    blocks = titles.get(title)
    if not blocks:
        return None, None
    best = None
    at_date = None
    for head, body in blocks:
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)", head)
        if not m:
            continue
        d = f"{m[1]}.{m[2]}.{m[3]}"
        if _date_key(d) > _date_key(DATE):
            continue
        h = re.search(r"holder\s*=\s*(\d+)", body)
        if not h:
            continue
        if _date_key(d) == _date_key(DATE):
            at_date = h.group(1)
        best = (h.group(1), d)
    if at_date is not None:
        return at_date, None
    return best if best else (None, None)


def load_chars():
    """character id -> body text."""
    out = {}
    for f in sorted((Path(GAME_CK3) / "history" / "characters").glob("*.txt")):
        text = _norm(f.read_text(errors="replace")).lstrip("\ufeff")
        for cid, body in _blocks(text):
            out.setdefault(cid, body)
    return out


def load_dynasties():
    """dynasty key (e.g. dynn_Tulunid) -> name key (dynn_Tulunid)."""
    out = {}
    for f in sorted((Path(GAME_CK3) / "common" / "dynasties").glob("*.txt")):
        for key, body in _blocks(_norm(f.read_text(errors="replace"))):
            n = re.search(r'name\s*=\s*"(dynn_\w+)"', body)
            if n:
                out[key] = n.group(1)
    return out


def load_houses():
    """house key -> (house name key, nested dynasty key or None).

    The name pattern deliberately accepts an unquoted value: house_abbasid is the
    one house in CK3's file that writes `name = dynn_Abbasid` with no quotes, and
    a quoted-only pattern would read that house as having no name at all.
    """
    out = {}
    for f in sorted((Path(GAME_CK3) / "common" / "dynasty_houses").glob("*.txt")):
        for key, body in _blocks(_norm(f.read_text(errors="replace"))):
            n = re.search(r'name\s*=\s*"?\s*(dynn_\w+)\s*"?', body)
            d = re.search(r"^\s*dynasty\s*=\s*(\w+)", body, re.M)
            name_key = n.group(1) if n else None
            out[key] = (HOUSE_NAME_OVERRIDE.get(key, name_key),
                        d.group(1) if d else None)
    return out


_LOC_FILES = None
# The key charset includes `-` and `.` as well as word characters. CK3 mixes key
# styles freely inside one file: names/character_names_l_english.yml has entries
# like ` Al-Mu_tazz:1 "al-Mu'tazz"` alongside plain `Abbasid:0 "Abbasid"`, and a
# `\\w`-only key class silently drops every hyphenated key. That is not cosmetic:
# it is why al-Mu'tazz's name came out as the raw untranslated key "Al-Mu_tazz".
_LOC_RE = re.compile(r'^[ \t]*([\w.\-]+)\s*:\d*\s*"(.*?)"[ \t\r\n]*$', re.M)


def loc(key):
    """English text of a localisation key, searching every English file.

    The whole English tree is scanned once and indexed by key, rather than
    re-walking ~1250 files on every call. The earlier per-key version looked
    correct but was subtly broken: it cached every match it saw while scanning
    for one key, so the first lookup populated the cache with a single entry and
    every later lookup short-circuited on "cache is non-empty" and returned None
    for perfectly valid keys. Indexing the whole tree once cannot have that
    failure mode.

    CRLF is tolerated explicitly. CK3's yml files carry \\r\\n and these lines are
    at end-of-file positions, where a strict $ anchor after the closing quote
    silently fails to match.
    """
    global _LOC_FILES
    if _LOC_FILES is None:
        _LOC_FILES = {}
        for pat in ("localization/english", "localisation/english"):
            root = Path(GAME_CK3) / pat
            if not root.is_dir():
                continue
            for f in sorted(root.rglob("*.yml")):
                try:
                    t = _norm(f.read_text(errors="replace"))
                except OSError:
                    continue
                for k, v in _LOC_RE.findall(t):
                    # First definition wins, so a later file cannot shadow an
                    # earlier one for a key that is genuinely defined twice.
                    _LOC_FILES.setdefault(k, v)
    return _LOC_FILES.get(key)


def resolve_dynasty(body, dyns, houses):
    """Dynasty string for a CK3 character body.

    A character usually names a `dynasty = <id>`. Some name only a
    `dynasty_house = <house>`, and then the house is the authority.

    For the house case the house's OWN name key wins, not the dynasty the house
    nests. house_cantabria declares `dynasty = erwigiana`, but its own name key
    is dynn_Cantabria, and "Cantabria" is what identifies the house the
    character actually sits in. The nested dynasty is only a fallback for a house
    that declares no name at all.

    This distinction is the whole reason ASU is "Cantabria" and not "Erwigiana",
    so it is spelled out here rather than left to a reader to infer.
    """
    m = re.search(r"^\s*dynasty\s*=\s*(\w+)", body, re.M)
    if m:
        return loc(dyns.get(m.group(1), "")) or m.group(1)
    h = re.search(r"^\s*dynasty_house\s*=\s*(\w+)", body, re.M)
    if h:
        house = h.group(1)
        name_key, nested = houses.get(house, (None, None))
        name_key = HOUSE_NAME_OVERRIDE.get(house, name_key)
        if name_key:
            return loc(name_key) or name_key
        if nested:
            return loc(dyns.get(nested, "")) or nested
    return None


def resolve(tag, titles, chars, dyns, houses):
    """{tag: {char, name, dynasty, title, carried}} or {tag: {error: ...}}.

    The character is looked up as the 867 holder of TITLES[tag] rather than stored,
    so the map holds one fact per realm - which title it corresponds to - and
    cannot come to disagree with itself.
    """
    title = TITLES[tag]
    cid, carried = holder_at_exact(title, titles)
    if cid is None:
        return {"error": f"CK3 has no 867 holder for {tag}'s title {title}"}
    body = chars.get(cid)
    if body is None:
        return {"error": f"CK3 has no character {cid} for {tag}"}
    # CK3 writes a character's name three ways, and all three occur in the files
    # this mod reads, so all three have to parse:
    #     name = "Nayih"     quoted
    #     name = Lothaire    bare, unquoted - 698 such lines in CK3's characters,
    #                        including Lothair II, who holds k_lotharingia
    #     name = "Muhammad" # Muhammad (I) ibn Abd al-Rahman, Sultan of Andalusia
    #                        quoted with a trailing comment, which is the most
    #                        common form of all
    # Anchoring to end-of-line would drop the commented form, which is why this
    # matches the value and stops at the comment instead.
    nm = re.search(r'^\s*name\s*=\s*(?:"([^"]*)"|([^\s#"]+))', body, re.M)
    if not nm:
        return {"error": f"character {cid} has no name line"}
    raw = nm.group(1) or nm.group(2)
    # CK3 character names are localisation keys when they need one, e.g.
    # "Al-Mu_tazz" is defined as "al-Mu'tazz". Prefer the localisation so the
    # apostrophe comes out right.
    name = loc(raw) or raw
    dy = resolve_dynasty(body, dyns, houses)
    return {"char": cid, "name": name, "dynasty": dy, "title": title,
            "carried": carried, "no_dynasty": not dy}


# -------------------------------------------------------------- country files -

def land_holders():
    """{tag: n_provinces} for every tag owning land at the mod's start date.

    Read back out of the generated province files rather than from a hand-kept
    list, so the audit follows the mod instead of an intention: if a realm gains
    or loses land, this set changes with it. check_start.effective is the same
    dated-history replay check_start.py uses, so this agrees with it by
    construction - including for provinces whose only owner is set in a dated
    block (Azores and Madeira) or which vanilla leaves unowned.
    """
    from build import effective
    out = {}
    for f in sorted((MOD / "history" / "provinces").glob("*.txt")):
        pid = int(f.name.split("-")[0].strip())
        text = f.read_text(encoding="utf-8", errors="surrogateescape")
        owner, _ctrl, _core, _hre = effective(text)
        if owner:
            out[owner] = out.get(owner, 0) + 1
    return out


def monarch_block(path):
    """(full_text, monarch_body) for the 1444.1.1 monarch block."""
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    m = re.search(r"^1444\.1\.1 = \{\s*\n\tmonarch = \{(.*?)^\t\}", text,
                  re.M | re.S)
    return text, (m.group(1) if m else None)


def current(body):
    """(name, dynasty) as currently written in a monarch body."""
    if body is None:
        return (None, None)
    n = re.search(r'name = "([^"]+)"', body)
    d = re.search(r'dynasty = "([^"]+)"', body)
    return (n.group(1) if n else None, d.group(1) if d else None)


def heir_dynasty(text):
    """Dynasty string on the 1444.1.1 heir, or None if there is no heir.

    Reads the whole 1444.1.1 block rather than the monarch sub-block, because the
    heir sits beside the monarch, not inside it.
    """
    blk = re.search(r"^1444\.1\.1 = \{\n(.*?)^\}", text, re.M | re.S)
    if not blk:
        return None
    heir = re.search(r'heir = \{(.*?)\n\t\}', blk.group(1), re.S)
    if not heir:
        return None
    d = re.search(r'dynasty = "([^"]+)"', heir.group(1))
    return d.group(1) if d else None


def step_ck3(argv):
    fix = "--fix" in argv
    titles, chars = load_titles(), load_chars()
    dyns, houses = load_dynasties(), load_houses()

    bad = []
    unwritten = []

    # Coverage first, so an unclassified realm is reported even if every mapped
    # tag happens to agree. Deriving the set from the province files is what makes
    # this a real gate: a tag added to the mod later shows up here unclassified.
    #
    # A vanilla tag that owns land is not unclassified. Nothing here touched it, so
    # it keeps its vanilla ruler, and listing the whole vanilla roster would only
    # re-type the game data. The gate is for tags the mod has an opinion about: a
    # realm with no CK3 title has to say why in Tag.no_ck3.
    holders = land_holders()
    vanilla = {fn.split(" ")[0] for fn in os.listdir(VANILLA_CDIR)
               if fn.endswith(".txt")}
    kept_vanilla = sorted(t for t in holders
                          if t not in TITLES and t not in NOT_CK3 and t in vanilla)
    unclassified = sorted(t for t in holders
                          if t not in TITLES and t not in NOT_CK3 and t not in vanilla)
    print(f"== {len(holders)} tags own land at the mod start date ==")
    print(f"   CK3-derived (name/dynasty checked): {len(TITLES)}")
    print(f"   classified as not CK3-derived      : {len(NOT_CK3)}")
    print(f"   vanilla, untouched, ruler kept    : {len(kept_vanilla)}")
    for t in unclassified:
        bad.append(f"{t} owns {holders[t]} provinces at the start date but is in "
                   f"neither TITLES nor NOT_CK3, and has no vanilla country file; "
                   f"give it a Tag.no_ck3 reason so it is accounted for")
    if unclassified:
        print(f"   UNCLASSIFIED: {', '.join(unclassified)}")
    stale = [t for t in NOT_CK3 if t not in holders]
    if stale:
        # Not a failure: NOT_CK3 may legitimately carry a tag that no longer owns
        # land. Worth printing, because it usually means an allocation moved.
        print(f"   note: NOT_CK3 lists tags with no land now: {', '.join(sorted(stale))}")

    for tag in sorted(TITLES):
        got = resolve(tag, titles, chars, dyns, houses)
        path = COUNTRY_OUT / f"{tag}.txt"
        if "error" in got:
            bad.append(f"{tag}: {got['error']}")
            continue
        if not path.exists():
            # Mapped but unwritten. The mod can legitimately keep a vanilla
            # history file for a realm it only touches on the map - NAV and PAP
            # are the current examples - and then there is no name/dynasty of ours
            # to check, only a title worth reporting. The coverage gate below still
            # fails if a land-holder is in neither registry, so this cannot become
            # a way to skip a realm silently.
            print(f"  NOTE {tag} {got['title']} / char {got['char']}")
            print(f"        no {path.name}: keeps the vanilla file, nothing to sync")
            if got.get("no_dynasty"):
                print(f"        CK3 867: name={got['name']!r} and NO dynasty - "
                      f"CK3 records neither dynasty nor dynasty_house for this "
                      f"character. Nothing is invented for it: if this tag ever "
                      f"gets a country file, map it to a title whose 867 holder "
                      f"has a dynasty.")
            else:
                print(f"        CK3 867: name={got['name']!r} "
                      f"dynasty={got['dynasty']!r}")
            unwritten.append(tag)
            continue
        text, body = monarch_block(path)
        cn, cd = current(body)
        if got.get("no_dynasty"):
            # Two different situations, and this used to fail both:
            #
            #   * the file DOES carry a dynasty -> the mod invented a house for a
            #     character CK3 gives none. That is a fabrication and stays fatal.
            #   * the file carries NO dynasty -> the mod declined to invent one and
            #     the file agrees with CK3. That is the correct outcome, and it is
            #     what MON (Miroslav of Duklja) and PAP (Nicholas I) both do.
            #
            # Only the first is a failure. The second is the policy working.
            if cd is not None:
                bad.append(f"{tag}: CK3 character {got['char']} ({got['name']}) has "
                           f"neither dynasty nor dynasty_house, but {path.name} "
                           f"declares dynasty={cd!r}. That dynasty is invented - "
                           f"drop it, or map the tag to a CK3 title whose 867 "
                           f"holder has a real one.")
                print(f"  FAIL {tag} {got['title']} / char {got['char']}")
                print(f"        file: name={cn!r} dynasty={cd!r}  <- INVENTED")
                print(f"        CK3 : name={got['name']!r} and NO dynasty")
            else:
                print(f"  OK   {tag} {got['title']} / char {got['char']}")
                print(f"        file: name={cn!r} dynasty={cd!r}")
                print(f"        CK3 : name={got['name']!r} and NO dynasty - the file "
                      f"declares none either, which is the correct handling: CK3 "
                      f"records neither dynasty nor dynasty_house, so nothing is "
                      f"invented to cover the gap.")
            continue
        hd = heir_dynasty(text)
        heir_bad = (hd is not None and hd != got["dynasty"]
                    and tag not in HEIR_DYNASTY_OVERRIDE)
        ok = (cn == got["name"] and cd == got["dynasty"] and not heir_bad)
        mark = "OK " if ok else "DRIFT"
        src = (f"<- {got['title']}"
               + (f" (holder carried from {got['carried']})"
                  if got.get("carried") else ""))
        print(f"  {mark} {tag} {src} / char {got['char']}")
        print(f"        file: name={cn!r} dynasty={cd!r}")
        print(f"        CK3 : name={got['name']!r} dynasty={got['dynasty']!r}")
        if hd is not None:
            print(f"        heir dynasty={hd!r}"
                  + ("  <- should match the ruler's" if heir_bad else ""))
        if not ok:
            if fix:
                # Rewritten inside the whole 1444.1.1 block rather than the monarch
                # sub-block, so the heir's dynasty can be brought along with the
                # ruler's. Only the ruler's NAME is taken from CK3: the heir is a
                # different man whom CK3 does not model here, so his name, stats and
                # dates are left exactly as the mod wrote them.
                blk = re.search(r"^1444\.1\.1 = \{\n(.*?)^\}", text, re.M | re.S)
                new = blk.group(1)
                if cn is not None:
                    new = re.sub(r'name = "[^"]+"', f'name = "{got["name"]}"',
                                 new, count=1)
                if cd is not None:
                    new = re.sub(r'dynasty = "[^"]+"',
                                 f'dynasty = "{got["dynasty"]}"', new, count=1)
                if heir_bad:
                    heir = re.search(r'heir = \{.*?\n\t\}', new, re.S)
                    nb = re.sub(r'dynasty = "[^"]+"',
                                f'dynasty = "{got["dynasty"]}"',
                                heir.group(0), count=1)
                    new = new[:heir.start()] + nb + new[heir.end():]
                text = text[:blk.start(1)] + new + text[blk.end(1):]
                path.write_text(text, encoding="utf-8",
                                errors="surrogateescape")
                print(f"        fixed -> {got['name']} / {got['dynasty']}")
            else:
                if cn != got["name"] or cd != got["dynasty"]:
                    bad.append(f"{tag}: file has {cn!r}/{cd!r}, CK3 has "
                               f"{got['name']!r}/{got['dynasty']!r}")
                if heir_bad:
                    bad.append(f"{tag}: heir dynasty is {hd!r} but the ruler's is "
                               f"{got['dynasty']!r}")

    if bad:
        print("\nFAIL:")
        for b in bad:
            print("  " + b)
        return 1
    checked = len(TITLES) - len(unwritten)
    print(f"\nOK: all {len(holders)} start-date land-holders are accounted for; "
          f"{checked} of {len(TITLES)} CK3-mapped rulers match CK3's 867 bookmark"
          + (f", {len(unwritten)} unwritten ({', '.join(sorted(unwritten))}) "
             f"keep vanilla's file" if unwritten else "")
          + (" (rewritten)" if fix else ""))
    return 0


# --------------------------------------------------------------------
# country files and the empire decision
# --------------------------------------------------------------------





CTRY_DATE = "1444.1.1"
# All five Carolingian realms share one dynasty deliberately. A shared dynasty
# is what unlocks Claim Cushion in EU4 - claiming a neighbour's throne without
# a war - so keeping it unbroken is the point of a divided empire: the five can
# put it back together by marriage instead of conquest. It has to cover the
# heirs as well as the monarchs, or the dynasty breaks the first time one of
# these realms succeeds, which is exactly what Arnulf and Berengar used to do.
DYNASTY = "de Carolingie"
SHIFT = 577


def shifted(y, m=1, d=1):
    return f"{y + SHIFT}.{m}.{d}"


# Capitals and cultures for the realms whose country file is written from scratch.
# Which realms those are is the Tag's `country` field, not a list here: see
# tagdb.HEADER and tagdb.FRESH_REALMS.

# The rank of every realm, its capital, its CK3 title, and the realms that are kept
# but not yet authored - all of it is one Tag object per realm in tagdb.py, which
# is also where every rank's justification lives. These four names are the same
# data seen from this script's side of the fence.
#
# A rank is argued from a realm's own 867 standing and never from which group a
# tag was filed under. The old rule here was "the five are peers at 2, Lusatia
# sits below them", which made the ranks a statement about the partition rather
# than about the realms.

# Vanilla tags this mod touches. They keep their own vanilla history - none of
# them is a realm of ours, they all sit outside the Karolingian sphere and are
# absent from the HRE decision - so this only ever corrects a capital and/or
# installs an 867 ruler. Nothing else in the vanilla file is touched.
VANILLA = {
    # Silesia: its vanilla seat is Ratibor (263), which now belongs to Great
    # Moravia, so SIL would own land but not its own seat. Breslau (264) is the
    # historical capital of the duchy - Ratibor was an appanage seat - and lies
    # inside the set SIL actually holds. It also gets its own 867 ruler.
    "SIL": {"capital": 264, "ruler": "SIL"},
    # Bohemia: an 867 ruler, no capital change (Praha 266 is still its own).
    "BOH": {"ruler": "BOH"},
    # Great Moravia: an 867 ruler, no capital change (Olomouc 4237 is its own).
    "GMA": {"ruler": "GMA"},
    # Navarre: the mod takes Vizcaya and Pirineo from France, and Pamplona (210)
    # is already vanilla's own NAV capital, so the capital is left alone.
    "NAV": {"ruler": "CK3"},
    # Montenegro: Zeta (138) and Kotor (4754) are the Dioclean core, and Zeta is
    # already vanilla's MON capital.
    "MON": {"ruler": "CK3"},
    # West Francia: every line of vanilla's French history survives - the 987
    # accession, the 1308 papal removal, all of it - and only the 1444 ruler and
    # the rank are overridden. It used to be patched by its own bespoke function
    # that skipped the rank step entirely, which left FRA with no government_rank
    # at all and the largest realm in the mod playing as a duchy.
    #
    # The ruler is the hand-written block, not ck3_block(): CK3 dates Charles
    # 823.1.14 - 877.6.10, which is a placeholder next to the 13 August 823 and
    # 6 October 877 every chronicle gives. ck3_sync still lifts his name and
    # dynasty from CK3; only the dates stay written here, as they do for every
    # other realm in this mod.
    "FRA": {"ruler": "FRA"},
    # Sardinia: no province changes hands and no capital changes - vanilla already
    # seats SAR at 127, which is one of its own three. The rank is set so that it
    # comes from the same argument as every other realm here rather than from EU4's
    # default of 1 by accident.
    #
    # The ruler comes from c_arborea rather than d_sardinia. CK3 leaves the Sardinian
    # duchies vacant at 867 - both d_sardinia and k_sardinia resolve to holder 0 or
    # nothing at all - so the only Sardinian of that date in the game is Gublenu,
    # who holds c_arborea and c_cagliari. Sardinia is a duchy in EU4 and a county is
    # where its 867 man happens to sit; that is the mod's business, not CK3's.
    "SAR": {"ruler": "CK3"},

    # Crete: an emir, and CK3 already has one. d_krete is held in 867 by Shuayb, Abu
    # Hafs' father, who lost the island to his own son in 870 - ten years before
    # this scenario's date, so the mod's own 867 is the year the old emir is still
    # on it. k_krete is unheld, so the duchy seat is the only one to read.
    #
    # This entry used to be a hand-written CRT.txt with no ruler from anywhere, on
    # the stated ground that CK3 models no Crete at all. That was wrong: the title
    # is d_krete, spelled the Greek way, and an earlier search for "crete" missed
    # it. The hand-written file had Abu Hafs Umar, who was born in 838 and
    # conquered Crete in 869 - not its emir in 867. Vanilla's CRT - Crete.txt has
    # no dated blocks at all and a header this mod was copying verbatim, so letting
    # the build own the file costs nothing and removes the invention.
    "CRT": {"ruler": "CK3"},
}

# 867 rulers for the vanilla tags above. Dates are CK3's own, taken from
# game/history/characters/, and are shifted by SHIFT like every ruler here.
#
# GMA  Rostislav (Rastislav), CK3 slovien.txt id 187002: birth 815.1.1, death
#      869.1.1. He is the Moravian ruler in 867. Svatopluk was only Prince of
#      Nitra until 870 and then succeeds him, which is why Svatopluk - not a
#      son - is the heir.
# BOH  Borivoj I, the first historically documented Premyslid, the year 867 being
#      the dynasty's own founding date. Sources put his birth at c. 852/53
#      (MedLands) or c. 870 (Wikipedia); 852 is used, which makes him 15 in 1444.
#      Both his sons were born after 867 - Spytihnev 875, Vratislav 888 - so the
#      heir is an infant either way and he carries regent = yes. That regency is
#      an artefact of the age shift, not a fact about 867.
# SIL  Gardomir, CK3 polish.txt id 82293: birth 844.1.1, death 912.1.1 - so 23 in
#      867, which is the age the user asked for. He is one of the semi-legendary
#      Silesian dukes of the Legenda memorabilis, the 13th-century Polish
#      hagiography CK3 also draws Sliezan (id 82291, b 805.1.1, d 864.1.1) and
#      his wife Gniewosadka (82292) from. Sliezan died in 864, so by 867 Gardomir
#      is the line's incumbent - a real succession, but a legendary one, which is
#      why it is sourced to CK3 rather than to the chronicles. Eldest son
#      Uniedrog (82297, b 863.1.1, d 942.1.1) is heir; his brother Swietopelk
#      (82298) is the best-attested of the three, but not the eldest.
#      EU4 1.37 has no nickname field in a monarch block - nickname is absent
#      from all 8416 vanilla name keys' blocks - so "Slezan" is part of the name.
VANILLA_RULERS = {
    "GMA": f"""
{CTRY_DATE} = {{
	monarch = {{
		name = "Rostislav"
		dynasty = "of Rostislav"
		birth_date = {shifted(815, 1, 1)}
		death_date = {shifted(869, 1, 1)}
		adm = 3
		dip = 4
		mil = 3
	}}
	heir = {{
		name = "Svatopluk"
		monarch_name = "Svatopluk"
		dynasty = "of Rostislav"
		birth_date = {shifted(840, 1, 1)}
		death_date = {shifted(894, 1, 1)}
		claim = 90
		adm = 4
		dip = 4
		mil = 4
	}}
}}
""",
    "BOH": f"""
{CTRY_DATE} = {{
	monarch = {{
		name = "Borivoj"
		dynasty = "of Premyslid"
		regent = yes
		birth_date = {shifted(852, 1, 1)}
		death_date = {shifted(889, 1, 1)}
		adm = 1
		dip = 2
		mil = 1
	}}
	heir = {{
		name = "Spytihnev"
		monarch_name = "Spytihnev"
		dynasty = "of Premyslid"
		birth_date = {shifted(875, 1, 1)}
		death_date = {shifted(915, 1, 1)}
		claim = 85
		adm = 2
		dip = 1
		mil = 2
	}}
}}
""",
    "SIL": f"""
{CTRY_DATE} = {{
	monarch = {{
		name = "Gardomir Slezan"
		dynasty = "Slezan"
		birth_date = {shifted(844, 1, 1)}
		death_date = {shifted(912, 1, 1)}
		adm = 2
		dip = 2
		mil = 3
	}}
	heir = {{
		name = "Uniedrog"
		monarch_name = "Uniedrog"
		dynasty = "Slezan"
		birth_date = {shifted(863, 1, 1)}
		death_date = {shifted(942, 1, 1)}
		claim = 80
		adm = 2
		dip = 2
		mil = 3
	}}
}}
""",
}

RULERS = {
    "FRA": f"""
{CTRY_DATE} = {{
	monarch = {{
		name = "Charles the Bald"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(823, 8, 13)}
		death_date = {shifted(877, 10, 6)}
		adm = 3
		dip = 3
		mil = 3
	}}
	heir = {{
		name = "Louis"
		monarch_name = "Louis the Stammerer"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(837, 9, 27)}
		death_date = {shifted(879, 8, 10)}
		claim = 95
		adm = 3
		dip = 2
		mil = 3
	}}
}}
""",
    "LOT": f"""
# Lothair II died childless in 869, which is why Lotharingia came apart. He is
# deliberately left without an heir so the scripted fragmentation still works.
{CTRY_DATE} = {{
	monarch = {{
		name = "Lothair II"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(835)}
		death_date = {shifted(869)}
		adm = 2
		dip = 2
		mil = 2
	}}
}}
""",
    "GER": f"""
{CTRY_DATE} = {{
	monarch = {{
		name = "Louis the German"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(817, 8, 27)}
		death_date = {shifted(876, 9, 5)}
		adm = 4
		dip = 3
		mil = 4
	}}
	heir = {{
		name = "Charles"
		monarch_name = "Charles the Fat"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(839)}
		death_date = {shifted(888, 12, 13)}
		claim = 95
		adm = 3
		dip = 3
		mil = 4
	}}
}}
""",
    "BAV": f"""
{CTRY_DATE} = {{
	monarch = {{
		name = "Carloman"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(817)}
		death_date = {shifted(880)}
		adm = 3
		dip = 3
		mil = 2
	}}
	heir = {{
		name = "Arnulf"
		monarch_name = "Arnulf"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(850)}
		death_date = {shifted(907, 12, 14)}
		claim = 95
		adm = 3
		dip = 3
		mil = 3
	}}
}}
""",
    "ITA": f"""
{CTRY_DATE} = {{
	monarch = {{
		name = "Louis II"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(826)}
		death_date = {shifted(875, 8, 13)}
		adm = 3
		dip = 3
		mil = 3
	}}
	heir = {{
		name = "Berengar"
		monarch_name = "Berengar"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(845)}
		death_date = {shifted(924, 10, 17)}
		claim = 95
		adm = 3
		dip = 3
		mil = 3
	}}
}}
""",
    # Lusatia is a free Sorbian principality with no 867 Carolingian monarch,
    # so it gets its own dynasty and native 1444 dates instead of a shifted 867
    # one. Mstivoj is an attested West Slavic name form (cf. Mstivoj of
    # Kladsko), which suits the Sorbian heartland around Zwickau and Leipzig.
    "SOR": f"""
{CTRY_DATE} = {{
	monarch = {{
		name = "Mstivoj"
		dynasty = "of Lusatia"
		birth_date = 1395.3.2
		death_date = 1449.11.8
		adm = 2
		dip = 1
		mil = 2
	}}
	heir = {{
		name = "Mstivoj"
		monarch_name = "Mstivoj"
		dynasty = "of Lusatia"
		birth_date = 1425.6.14
		death_date = 1470.1.1
		claim = 80
		adm = 2
		dip = 2
		mil = 2
	}}
}}
""",
}


# Provenance comments, one per CK3-sourced realm, emitted into the generated
# file directly above its 1444.1.1 block. These used to be pasted into the output
# by hand, which meant the next run of this script deleted them - the comments
# were the one thing in the country files with no source behind them.
#
# They live here because that is where everything else about the ruler lives.

PROVENANCE = {
    "FRA": """\
# Ruler lifted verbatim from CK3 by build.py: CK3's holder of k_france
# at 867.1.1 is character 90104, "Charles", of dynasty 25061 "Karling". CK3 gives
# him no epithet, so the earlier hand-written "Charles the Bald" is gone; that is
# what verbatim means here. Do not hand-edit name or dynasty - run
# `python3 tools/build.py --fix` instead, and validate.py will fail if the file
# and CK3 disagree.
""",
    "LOT": """\
# Ruler lifted verbatim from CK3 by build.py: CK3's holder of
# k_lotharingia at 867.1.1 is character 144998, "Lothaire", of dynasty 25061
# "Karling". Note CK3 writes that name unquoted, with no epithet; the earlier
# hand-written "Lothair II" is gone. Do not hand-edit name or dynasty - run
# `python3 tools/build.py --fix` instead.
""",
    "GER": """\
# Ruler lifted verbatim from CK3 by build.py: CK3's holder of
# k_east_francia at 867.1.1 is character 90107, "Ludwig", of dynasty 25061
# "Karling". CK3 gives him no epithet, so the earlier hand-written "Louis the
# German" is gone; that is what verbatim means here. Do not hand-edit name or
# dynasty - run `python3 tools/build.py --fix` instead.
""",
    "BAV": """\
# Ruler lifted verbatim from CK3 by build.py: CK3's holder of
# d_bavaria at 867.1.1 is character 42018, "Karlmann", of dynasty 25061
# "Karling".
#
# The duchy is deliberate, and the reason is in build.py: CK3 has no
# independent Bavaria in 867. Its k_bavaria is held by Ludwig (90107) - the same
# man as k_east_francia - continuously from 826.1.1 until 876.1.1, and Carloman
# only takes it in 876. Since this mod does split Bavaria off as its own realm,
# d_bavaria is the title whose 867 holder is him. Mapping to k_bavaria would have
# made this a second "Ludwig"/"Karling" and erased the realm.
#
# Do not hand-edit name or dynasty - run `python3 tools/build.py --fix` instead.
""",
    "ITA": """\
# Ruler lifted verbatim from CK3 by build.py: CK3's holder of k_italy
# at 867.1.1 is character 30228, "Louis", of dynasty 25061 "Karling". CK3 gives
# him no regnal number, so the earlier hand-written "Louis II" is gone. Do not
# hand-edit name or dynasty - run `python3 tools/build.py --fix` instead.
""",
    "SOR": """\
# Ruler lifted verbatim from CK3 by build.py: CK3's holder of
# d_lausitz at 867.1.1 is character 184007, "Radomil", of the Milczanow dynasty.
#
# CK3 models no Sorbian title at all - k_sorbs and d_sorbs both have no holder -
# so d_lausitz is the nearest title with an actual 867 ruler. That replaces the
# hand-written "Mstivoj"/"of Lusatia". Mstivoj is historically the better-known
# Lusatian ruler of the period and survives as the heir below; CK3's choice is
# followed because it is what the rest of this mod's western Slavic realms do.
#
# Do not hand-edit name or dynasty - run `python3 tools/build.py --fix` instead.
""",
    "GMA": """\
# Ruler lifted verbatim from CK3 by build.py: CK3's holder of k_moravia
# at 867.1.1 is character 187002, "Rostislav", of the Mojmird dynasty.
#
# This realm holds the two Moravian provinces (Brno 265, Olomouc 4237) as well as
# Galicia, and its ruler was already Rostislav, so k_moravia is the title whose 867
# holder the mod was reaching for. The hand-written dynasty "of Rostislav" was
# invented; CK3 calls the house Mojmird. Do not hand-edit name or dynasty - run
# `python3 tools/build.py --fix` instead.
""",
    "SIL": """\
# Ruler lifted verbatim from CK3 by build.py: CK3's holder of
# d_lower_silesia at 867.1.1 is character 82293, "Gardomir", of the dynasty
# CK3 spells "Slezan" with diacritics. The hand-written "Gardomir Slezan"/"Slezan"
# was already a guess at exactly this, so only the spelling is new. Do not
# hand-edit name or dynasty - run `python3 tools/build.py --fix` instead.
""",
}

# ---------------------------------------------------------------- CK3 rulers --

def with_provenance(tag, text):
    """Insert this tag's provenance comment above its 1444.1.1 block."""
    note = PROVENANCE.get(tag)
    if not note or "1444.1.1 = {" not in text or note.strip() in text:
        return text
    return text.replace("1444.1.1 = {", note + "1444.1.1 = {", 1)


# Every name and dynasty written below used to be typed in by hand, which meant
# this script and ck3ruler.py each held their own copy of the same fact - and
# running this script silently reverted all fifteen CK3-sourced rulers to the
# pre-lift strings ("Charles the Bald", "of Rostislav", Mstivoj/"of Lusatia").
#
# So this script no longer decides those two fields. It writes the ruler's stats,
# dates and heir exactly as before, then asks build.resolve what CK3's 867 holder's
# name and dynasty are. One source of truth, and regenerating is idempotent
# instead of destructive.
#
# Only name and dynasty are taken. Stats and dates stay hand-written because they
# are judgement calls: CK3's 1-25 skill scale is not EU4's 1-6, and CK3 has no
# 1444 to be alive in.
_CK3_CACHE: dict = {}


def ck3_ruler(tag):
    """CK3's 867 name/dynasty for `tag`, or None if CK3 is not the authority."""
    if tag not in _CK3_CACHE:
        try:
            _c = sys.modules[__name__]
        except ImportError:
            _CK3_CACHE[tag] = None
            return None
        if tag not in _c.TITLES:
            _CK3_CACHE[tag] = None
            return None
        got = _c.resolve(tag, _c.load_titles(), _c.load_chars(),
                         _c.load_dynasties(), _c.load_houses())
        # A CK3 character with no dynasty (the Pope) yields None here rather than
        # a half-answer, so the mod's own string is left alone instead of being
        # blanked or invented.
        _CK3_CACHE[tag] = None if got.get("error") or not got.get("dynasty") else got
    return _CK3_CACHE[tag]


def ck3_sync(tag, text):
    """Rewrite the ruler's name and every dynasty line from CK3."""
    got = ck3_ruler(tag)
    if got is None:
        return text
    blk = re.search(r"^1444\.1\.1 = \{\n(.*?)^\}", text, re.M | re.S)
    if not blk:
        return text
    new = re.sub(r'name = "[^"]+"', f'name = "{got["name"]}"',
                 blk.group(1), count=1)
    new = re.sub(r'dynasty = "[^"]+"', f'dynasty = "{got["dynasty"]}"', new)
    return text[:blk.start(1)] + new + text[blk.end(1):]



# --------------------------------------------------------------------------------------
# Rulers derived from CK3
# --------------------------------------------------------------------------------------
# SIL, GMA and BOH above have hand-written ruler blocks, because each one needed a
# judgement CK3 cannot make for us: which son was the heir, and why a regency is an
# artefact of the age shift rather than a fact about 867. NAV and MON need no such
# judgement, so their blocks are derived from CK3 instead of transcribed. A
# transcription is a snapshot of CK3 that silently rots; this is CK3's own entry,
# read at build time, which is the authority the hand-written blocks cite anyway.
#
# One conversion is applied, and it is applied to every ruler: CK3 rates skills
# roughly 1-20, EU4 rates monarch stats 0-6, so EU4 = CK3 / 3, clamped to 1-6. CK3
# records no skills at all for some characters (Miroslav of Duklja is one), and for
# those the mod uses a neutral 2/2/2 rather than inventing a reputation.
def _eu4_skill(ck3_value):
    if ck3_value is None:
        return 2, None
    return max(1, min(6, round(int(ck3_value) / 3))), int(ck3_value)


def _ck3_dates_and_skills(cid, chars):
    """(birth, death, adm, dip, mil) for a CK3 character id, or None if not found."""
    body = chars.get(cid)
    if body is None:
        return None
    birth = death = None
    # CK3 stores a life event as a dated block whose key IS the date and whose
    # body is `birth = yes` / `death = yes`, e.g. `844.1.1 = { birth = "844.1.1" }`.
    for date, block in re.findall(r"(\d+\.\d+\.\d+)\s*=\s*\{(.*?)\n\t\}", body, re.S):
        if re.search(r"^\s*birth\s*=", block, re.M):
            birth = date
        if re.search(r"^\s*death\s*=", block, re.M):
            death = date
    def skill(key):
        m = re.search(r"^\s*" + key + r"\s*=\s*(\d+)", body, re.M)
        return m.group(1) if m else None
    adm, _ = _eu4_skill(skill("stewardship"))
    dip, _ = _eu4_skill(skill("diplomacy"))
    mil, _ = _eu4_skill(skill("martial"))
    return birth, death, adm, dip, mil


def _ck3_name(cid, chars, loc):
    m = re.search(r'^\s*name\s*=\s*(?:"([^"]*)"|([^\s#"]+))', chars[cid], re.M)
    if not m:
        return None
    return loc(m.group(1) or m.group(2)) or (m.group(1) or m.group(2))


def ck3_block(tag):
    """A 867 monarch (and heir where CK3 records one) derived from CK3."""
    c = sys.modules[__name__]

    titles, chars = c.load_titles(), c.load_chars()
    dyns, houses = c.load_dynasties(), c.load_houses()
    got = c.resolve(tag, titles, chars, dyns, houses)
    if "error" in got:
        raise SystemExit(f"{tag}: {got['error']}")
    cid = got["char"]
    facts = _ck3_dates_and_skills(cid, chars)
    if facts is None:
        raise SystemExit(f"{tag}: CK3 character {cid} has no readable entry")
    birth, death, adm, dip, mil = facts
    if not birth or not death:
        raise SystemExit(f"{tag}: CK3 character {cid} has no birth or death date")
    name = _ck3_name(cid, chars, c.loc)
    dynasty = got["dynasty"]

    def person(cid_, claim=None):
        nonlocal chars
        nm = _ck3_name(cid_, chars, c.loc)
        b, d, a, dp, ml = _ck3_dates_and_skills(cid_, chars)
        dy = c.resolve_dynasty(chars[cid_], dyns, houses)
        out = [f'\t\tname = "{nm}"']
        if claim is not None:
            out.append(f'\t\tmonarch_name = "{nm}"')
        if dy:
            out.append(f'\t\tdynasty = "{dy}"')
        for label, d_ in (("birth_date", b), ("death_date", d)):
            if not d_:
                raise SystemExit(f"{tag}: CK3 character {cid_} has no {label}")
            y, m, dd = (int(x) for x in d_.split("."))
            out.append(f"\t\t{label} = {shifted(y, m, dd)}")
        if claim is not None:
            out.append(f"\t\tclaim = {claim}")
        out += [f"\t\tadm = {a}", f"\t\tdip = {dp}", f"\t\tmil = {ml}"]
        return "\n".join(out)

    lines = [f"{CTRY_DATE} = {{", "\tmonarch = {", person(cid), "\t}"]
    # The heir is the eldest son CK3 records. CK3 has no gender key on these
    # characters, so a child is used only where the name is not a daughter's; where
    # CK3 records no children at all (Miroslav) no heir is written, and the game
    # generates one, which is honest about the gap instead of inventing a son.
    kids = [k for k, b in chars.items()
            if re.search(rf"^\s*father\s*=\s*{cid}\b", b, re.M)]
    kids.sort(key=lambda k: _ck3_dates_and_skills(k, chars)[0] or "9999.9.9")
    if kids:
        lines += ["\their = {", person(kids[0], claim=90), "\t}"]
    lines += ["}", ""]
    if not dynasty:
        lines.insert(0, f"# {name} has no dynasty in CK3, so none is written here.")
        lines.insert(0, "# Inventing a house to fill the gap would be a fabrication.")
    return "\n".join(lines)


def find_vanilla(tag):
    for fn in os.listdir(VANILLA_CDIR):
        if fn.split(" ")[0] == tag and fn.endswith(".txt"):
            return os.path.join(VANILLA_CDIR, fn), fn
    raise SystemExit(f"no vanilla history file for {tag}")


def fresh(tag):
    cap, culture = HEADER[tag]
    return f"""government = monarchy
add_government_reform = feudalism_reform
government_rank = {RANK[tag]}
technology_group = western
primary_culture = {culture}
religion = catholic
capital = {cap}
{RULERS[tag]}"""


# --------------------------------------------------------------------------------------
# Disbanding the Holy Roman Empire
# --------------------------------------------------------------------------------------
# There is no empire switch to flip. A country is an elector purely because its own
# history says `elector = yes` - common/empire/electors.txt ships empty, and
# DESIRED_NUM_OF_ELECTORS in defines.lua only sizes how many the emperor would LIKE,
# not who is one. Dissolving the empire therefore means dissolving its electorate.
#
# Vanilla does exactly this, and says so in its own comments. Seven country files
# carry `1806.7.12 = { elector = no }` - the Reichsdeputationshauptschluss, the real
# abolition of the HRE - and REG's reads `1806.7.12 = { elector = no } # the HRE is
# dissolved`. That dated block is why a 1821 start date has no Holy Roman Empire:
# the history is read up to 1821, every elector has been set to `no`, and there is
# nobody left to elect an emperor. A 1444 start simply never reaches those dates.
#
# So to get that same end state at 1444 we write the dissolution ourselves, one
# state at a time instead of one dated block per country: the top-level
# `elector = yes` of each 1444 electorate member becomes `elector = no`, which is
# vanilla's own syntax for the empire's end. No on_action, no defines override.
#
# Only these seven, because only these seven have a TOP-LEVEL `elector = yes`.
# That qualifier matters: Regensburg and Hessen also have `elector = yes`, but
# only inside dated blocks from 1803, when the Reichsdeputationshauptschluss gave
# them electoral dignity. At 1444 they hold no vote at all, so they need no
# override and their 1803-1806 history is left untouched.
#
# Bohemia matters twice over: it is one of the seven, and it is also the one this
# mod keeps land and an 867 ruler for, so its copy is patched below along with its
# capital and ruler. The other six are copied verbatim with only that one line
# changed.
IMPERIAL_ELECTORS = ["BOH", "BRA", "KOL", "MAI", "PAL", "SAX", "TRI"]


def patch_vanilla(tag, capital=None, ruler=None, strip_elector=False, rank=None):
    """Copy a vanilla history file, changing only a capital, the government rank,
    the 1444 ruler and whether the country is an imperial elector.

    Everything else in the vanilla file is preserved verbatim, so a vanilla tag
    keeps its whole later history - Zizka and the defenestration of Prague for
    Bohemia, the Piast line for Silesia - and only its 867 start is replaced.
    """
    path, fn = find_vanilla(tag)
    text = open(path, encoding="utf-8", errors="surrogateescape").read()
    if strip_elector:
        # `^` with no leading-whitespace class on purpose: only a TOP-LEVEL
        # `elector = yes` is a vote in 1444. The same key indented inside a dated
        # block is a later state (Regensburg's 1803 one) and must survive, so
        # matching `\s*` here would silently rewrite 1803-1806 history.
        text, n = re.subn(r"^elector\s*=\s*yes[^\n]*$",
                          "elector = no # mod: the HRE is dissolved, "
                          "see the 1806.7.12 entry in vanilla's own files",
                          text, count=1, flags=re.M)
        assert n == 1, f"{tag}: no top-level 'elector = yes' to dissolve in {fn}"
    if capital is not None:
        # Top-level only, for the same reason as the elector line below: the same
        # key indented inside a dated block is a later state of that key, and
        # count=1 would rewrite whichever came first in the file. Vanilla France
        # has `government_rank` inside its 1792 revolution block, so a pattern
        # that allowed leading whitespace silently rewrote the Revolution's rank
        # instead of setting the kingdom's.
        text, n = re.subn(r"^(capital\s*=\s*)\d+.*$", rf"\g<1>{capital}", text,
                          count=1, flags=re.M)
        assert n == 1, f"{tag}: no top-level capital line to patch in {fn}"
    if rank is not None:
        # Eight of the twenty realms have no government_rank in vanilla at all,
        # so they silently fall to EU4's default of 1. That is how the Tulunids
        # ended up ranked level with Silesia: not a decision, an omission. Set
        # every one of them from RANK so the tier is always deliberate.
        text, n = re.subn(r"^(government_rank\s*=\s*)\d+.*$", rf"\g<1>{rank}", text,
                          count=1, flags=re.M)
        if n == 0:
            # No line to patch: add one beside the other government keys, so the
            # header stays readable rather than gaining a stray line at the end.
            anchor = re.search(r"^\s*government\s*=\s*\w+.*$", text, re.M)
            assert anchor, f"{tag}: no government line to anchor a rank to in {fn}"
            text = text[:anchor.end()] + f"\ngovernment_rank = {rank}" + text[anchor.end():]
    if ruler is not None:
        lines = text.splitlines()
        # insert before the first dated block at or after the start date, so
        # chronological order holds; default to the end of the file
        ins = len(lines)
        for i, ln in enumerate(lines):
            m = re.match(r"^(\d+)\.(\d+)\.(\d+)\s*=", ln.strip())
            if m and (int(m.group(1)), int(m.group(2)),
                      int(m.group(3))) >= (1444, 1, 1):
                ins = i
                break
        block = ruler.strip("\n").splitlines()
        lines = lines[:ins] + block + [""] + lines[ins:]
        text = "\n".join(lines) + "\n"
    return text


def step_countries():
    os.makedirs(COUNTRY_OUT, exist_ok=True)
    for tag in ["LOT", "GER", "BAV", "ITA", "SOR"]:
        open(os.path.join(COUNTRY_OUT, f"{tag}.txt"), "w", encoding="utf-8").write(
            with_provenance(tag, ck3_sync(tag, fresh(tag))))
        print(f"wrote {tag}.txt")
    for tag, spec in VANILLA.items():
        want = spec.get("ruler")
        ruler = (ck3_block(tag) if want == "CK3"
                 else {**RULERS, **VANILLA_RULERS}.get(want))
        was_elector = tag in IMPERIAL_ELECTORS
        open(os.path.join(COUNTRY_OUT, f"{tag}.txt"), "w", encoding="utf-8",
             errors="surrogateescape").write(
            with_provenance(tag, ck3_sync(tag, patch_vanilla(
                tag, spec.get("capital"), ruler, was_elector, RANK.get(tag)))))
        what = []
        if spec.get("capital"):
            what.append(f"capital -> {spec['capital']}")
        if ruler:
            nm = re.search(r'name = "([^"]+)"', ruler)
            what.append(f"867 ruler {nm.group(1) if nm else want}"
                        + (" (from CK3)" if want == "CK3" else ""))
        if was_elector:
            what.append("electorate removed")
        if tag in RANK:
            what.append(f"rank {RANK[tag]}")
        print(f"wrote {tag}.txt (vanilla history preserved"
              + (", " + ", ".join(what) if what else "") + ")")
    # The remaining electors, so the empire is left with nobody to elect as
    # emperor. Verbatim vanilla apart from the single dissolved vote.
    for tag in IMPERIAL_ELECTORS:
        if tag in VANILLA:
            continue
        # Build first, write second. `open(..., "w")` truncates before its
        # argument is evaluated, so writing patch_vanilla(...) inline left a
        # 0-byte country file behind whenever the assert fired - and an empty
        # file looks clean to every grep-based check.
        text = patch_vanilla(tag, strip_elector=True)
        with open(os.path.join(COUNTRY_OUT, f"{tag}.txt"), "w", encoding="utf-8",
                  errors="surrogateescape") as fh:
            fh.write(text)
        print(f"wrote {tag}.txt (vanilla history preserved, "
              f"electorate dissolved)")



def main() -> int:
    """Run the whole build. Returns 0 only if every check passed."""
    started = time.time()
    print(f"The Karolingians - full build\n{'=' * 60}")

    phases = [
        ("check the Tag database", selfcheck),
        ("generate province files", step_provinces, []),
        ("generate country files", step_countries),
        ("generate the empire decision", step_hre),
        ("check CK3 rulers", step_ck3, []),
        ("check start-date ownership", step_start),
    ]

    def step(label, fn, *args):
        print(f"\n\033[1m==> {label}\033[0m", flush=True)
        try:
            return fn(*args) or 0
        except SystemExit as exc:
            return int(exc.code or 0)

    for phase in phases:
        label, fn, *rest = phase
        try:
            rc = step(label, fn, *rest)
        except Exception:
            import traceback
            traceback.print_exc()
            print(f"\n\033[31mBUILD FAILED\033[0m with an exception in {label}")
            return 1
        if rc:
            print(f"\n\033[31mBUILD FAILED\033[0m at {label}")
            return 1

    print(f"\n{'=' * 60}\n\033[32mBUILD OK\033[0m in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
