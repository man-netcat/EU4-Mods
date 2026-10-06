#!/usr/bin/env python3

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

VDIR = VANILLA_PDIR = Path(GAME) / "history" / "provinces"
VANILLA_CDIR = Path(GAME) / "history" / "countries"
PDIR = PROV_OUT = MOD / "history" / "provinces"
COUNTRY_OUT = MOD / "history" / "countries"

from tagdb import *  # noqa: F401,F403


def vanilla_is_newer() -> bool:

    if not PROVDATA.exists():
        return True
    try:
        return (
            max(p.stat().st_mtime for p in VANILLA_HISTORY.rglob("*.txt"))
            > PROVDATA.stat().st_mtime
        )
    except OSError:
        return False


def parse(path):

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


import re  # noqa: E402

os.makedirs(CACHE, exist_ok=True)

PROV_DIR = os.path.join(GAME, "history", "provinces")
AREA = os.path.join(GAME, "map", "area.txt")
REGION = os.path.join(GAME, "map", "region.txt")


def parse_block_file(path):

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

            if re.match(r"^(color|provinces)\s*=", s):
                continue
            ids += [int(x) for x in re.findall(r"\d+", s)]
        areas[key] = sorted(set(ids))
    return areas


def load_region_areas():

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
        d = {
            "id": pid,
            "name": pname,
            "file": fn,
            "cores": [],
            "owner": None,
            "controller": None,
            "culture": None,
            "religion": None,
            "hre": False,
            "capital": False,
            "sea": False,
        }

        for ln in text.splitlines():
            s = ln.strip()
            if re.match(r"^\d+\.\d+\.\d+\s*=", s):
                break
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

    data = {
        "provs": provs,
        "areas": areas,
        "area_of": area_of,
        "region_of_area": region_of_area,
    }
    with open(str(CACHE / "provdata.json"), "w") as f:
        json.dump(data, f)

    print(f"provinces: {len(provs)}  areas: {len(areas)}")
    print(f"hre=yes: {sum(1 for p in provs.values() if p['hre'])}")

    hre_owners = defaultdict(list)
    for p in provs.values():
        if p["hre"]:
            hre_owners[p["owner"]].append(p["id"])
    print(f"\ndistinct owners inside HRE boundary: {len(hre_owners)}")
    for t, ids in sorted(hre_owners.items(), key=lambda x: -len(x[1]))[:40]:
        print(f"  {t:5} {len(ids):3}")


if vanilla_is_newer():
    print("\n\033[1m==> probe vanilla province history\033[0m", flush=True)
    step_probe()
else:
    print("\n\033[1m==> probe\033[0m\n    cache is current, skipping")

_PROVDATA = json.load(open(str(CACHE / "provdata.json")))

provs = _PROVDATA["provs"]
AREAS = _PROVDATA["areas"]

_AREA_OF = _PROVDATA["area_of"]
_REGION_OF_AREA = _PROVDATA["region_of_area"]


def _owned(tag, region=None, exclude_regions=()):

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

    return _REGION_OF_AREA.get(_AREA_OF.get(str(pid)))


def _area(*areas):

    out = set()
    for area in areas:
        out |= {int(pid) for pid in _PROVDATA["areas"].get(area, ())}
    return sorted(out)


UNTRACKED_OWNERS = {
    112: "VEN",
}

PROVINCE_OWNERS = {**UNTRACKED_OWNERS, **PROVINCE_OWNERS}

CAPITAL = {t.tag: t.capital for t in BY_TAG.values() if t.in_alloc and t.capital}
NAME = {tag: BY_TAG[tag].name for tag in AREA_OWNERS}

CULTURE_GONE_867 = {"turkish": "greek", "pontic_greek": "greek"}

CONQUERED_BY_THE_ARABS = {327, 332, 2303, 4298, 4310}

MUSLIM_RELIGIONS_867 = ("sunni", "shiite")


def apply_867_culture(text, pid):

    m = re.search(r"^(\s*)culture\s*=\s*(\w+)", text, re.M)
    if not m:
        return text
    culture = CULTURE_GONE_867.get(m.group(2))
    if not culture:
        return text
    text = text[: m.start()] + f"{m.group(1)}culture = {culture}" + text[m.end() :]
    if pid not in CONQUERED_BY_THE_ARABS:
        text = re.sub(
            rf"^(\s*religion\s*=\s*)({'|'.join(MUSLIM_RELIGIONS_867)})\b",
            r"\1orthodox",
            text,
            flags=re.M,
        )
    return text


LAYER2_MOVES: list = []


def build(verbose=False):

    LAYER2_MOVES.clear()
    alloc: dict = {}
    owner_of: dict = {}
    overlaps = []

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
            + ", ".join(f"{p} ({a} and {b})" for p, a, b in overlaps)
        )

    for pid, tag in PROVINCE_OWNERS.items():
        prev = owner_of.get(pid)
        owner_of[pid] = tag
        if prev in alloc:
            alloc[prev] = [p for p in alloc[prev] if p != pid]
        alloc.setdefault(tag, [])
        if pid not in alloc[tag]:
            alloc[tag] = sorted(alloc[tag] + [pid])
        LAYER2_MOVES.append((pid, provs[str(pid)]["name"], prev, tag))

    for tag, extra in TRANSFERS:
        claimed = set(alloc.get(tag, ()))
        for other in alloc:
            if other != tag:
                claimed |= set(alloc[other])
        alloc[tag] = sorted(
            set(alloc.get(tag, [])) | {p for p in extra if p not in claimed}
        )

    if verbose:
        for pid, name, prev, tag in LAYER2_MOVES:
            print(f"  override: province {pid} {name} {prev} -> {tag}")
    return {t: sorted(alloc[t]) for t in ALL_TAGS if t in alloc and alloc[t]}


def owner_map(alloc=None):

    alloc = build() if alloc is None else alloc
    return {p: t for t, ps in alloc.items() for p in ps}


EMPIRE_CORE_AREAS = (
    "alsace_area",
    "austria_proper_area",
    "bourgogne_area",
    "brabant_area",
    "braunschweig_area",
    "carinthia_area",
    "catalonia_area",
    "central_italy_area",
    "champagne_area",
    "corsica_sardinia_area",
    "east_bavaria_area",
    "emilia_romagna_area",
    "flanders_area",
    "franconia_area",
    "frisia_area",
    "guyenne_area",
    "hesse_area",
    "holland_area",
    "ile_de_france_area",
    "inner_austria_area",
    "languedoc_area",
    "lazio_area",
    "liguria_area",
    "loire_area",
    "lombardy_area",
    "lorraine_area",
    "lower_bavaria_area",
    "lower_rhineland_area",
    "lower_saxony_area",
    "lower_swabia_area",
    "massif_central_area",
    "normandy_area",
    "north_brabant_area",
    "north_rhine_area",
    "north_westphalia_area",
    "northern_saxony_area",
    "orleans_area",
    "palatinate_area",
    "picardy_area",
    "piedmont_area",
    "po_valley_area",
    "poitou_area",
    "provence_area",
    "pyrenees_area",
    "romandie_area",
    "savoy_dauphine_area",
    "south_saxony_area",
    "switzerland_area",
    "thuringia_area",
    "tirol_area",
    "tuscany_area",
    "upper_bavaria_area",
    "upper_franconia_area",
    "upper_rhineland_area",
    "upper_swabia_area",
    "venetia_area",
    "wallonia_area",
    "weser_area",
    "west_burgundy_area",
    "westphalia_area",
)

NOT_IMPERIAL_867 = {
    59,
    61,
    112,
    118,
    120,
    127,
    2965,
    2986,
    2988,
    4735,
    4744,
}


def empire_core():

    core = set()
    for area in EMPIRE_CORE_AREAS:
        for pid in AREAS.get(area, ()):
            if pid not in NOT_IMPERIAL_867 and provs.get(str(pid), {}).get("owner"):
                core.add(pid)
    return sorted(core)


def dev(pid):

    for fn in os.listdir(VANILLA_PDIR):
        if re.match(rf"^{pid}\s*-", fn):
            txt = open(
                os.path.join(VANILLA_PDIR, fn), encoding="utf-8", errors="replace"
            ).read()
            ta = re.search(r"base_tax\s*=\s*([\d.]+)", txt)
            pr = re.search(r"base_production\s*=\s*([\d.]+)", txt)
            return (float(ta.group(1)) if ta else 0.0) + (
                float(pr.group(1)) if pr else 0.0
            )
    return 0.0


PROV_DATE = "1444.11.11"


def force_block(new_owner):

    return (
        f"\n{PROV_DATE} = {{\towner = {new_owner}\n"
        f"\tcontroller = {new_owner}\n"
        f"\tadd_core = {new_owner}\n"
        f"\thre = no\n"
        f"}}\n"
    )


def unown(text):

    lines = text.splitlines()
    dated_start = len(lines)
    for idx, ln in enumerate(lines):
        if re.match(r"^\d+\.\d+\.\d+\s*=", ln.strip()):
            dated_start = idx
            break
    out = [
        ln
        for idx, ln in enumerate(lines)
        if idx >= dated_start or not re.match(r"^(owner|controller)\s*=", ln.strip())
    ]
    return "\n".join(out) + "\n"


def patch(text, new_owner):

    out, i, n = [], 0, len(text.splitlines())
    lines = text.splitlines()

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

        if re.match(r"^hre\s*=", s):
            out.append(re.sub(r"hre\s*=\s*\w+", "hre = no", ln))
            continue

        m = re.match(r"^(owner|controller)\s*=\s*", s)
        if m:
            indent = ln[: len(ln) - len(ln.lstrip())]
            out.append(f"{indent}{m.group(1)} = {new_owner}")
            continue

        out.append(ln)

    have_core = any(
        re.match(rf"^\s*add_core\s*=\s*{re.escape(new_owner)}\s*$", lines[idx])
        for idx in range(dated_start)
    )
    core_line = f"add_core = {new_owner}"
    if have_core:
        return "\n".join(out) + "\n" + force_block(new_owner)

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

    owner_of = {p: t for t, ps in alloc.items() for p in ps}

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
            open(src, encoding="utf-8", errors="surrogateescape").read(), pid
        )
        tag = owner_of.get(pid)
        if pid in BALATON_RESERVED:
            new = unown(text)
        else:
            new = patch(text, tag) if tag else text

        new = re.sub(r"(\bhre\s*=\s*)yes\b", r"\1no", new)
        open(
            os.path.join(PROV_OUT, os.path.basename(src)),
            "w",
            encoding="utf-8",
            errors="surrogateescape",
        ).write(new)
        written += 1

    print(f"wrote {written} province files")
    for tag, ps in sorted(alloc.items(), key=lambda kv: -len(kv[1])):
        print(f"  {tag:4} {len(ps):3}")
    print(f"  hre=yes stripped : {len(hre_yes)}")
    print(f"  total            : {len(todo)}")


def report(alloc):

    owner_of = owner_map(alloc)
    caps = {}
    for fn in os.listdir(VANILLA_CDIR):
        if not fn.endswith(".txt"):
            continue
        tag = fn.split(" ")[0].split("-")[0].strip()
        m = re.search(
            r"^\s*capital\s*=\s*(\d+)",
            open(
                os.path.join(VANILLA_CDIR, fn), encoding="utf-8", errors="replace"
            ).read(),
            re.M,
        )
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
        print(
            f"{tag} {NAME.get(tag, tag):13} n={len(ids):3} dev={sum(dev(p) for p in ids):6.0f}"
            + (f" cap={cap}({provs[str(cap)]['name']})" if cap else "")
            + f" hre={hre}"
        )
        print(
            "     from: "
            + " ".join(f"{k}:{v}" for k, v in sorted(olds.items(), key=lambda x: -x[1]))
        )
        total += len(ids)
    print("=" * 78)
    print(f"{len(owner_of)} provinces reassigned")


d = json.load(open(str(CACHE / "provdata.json")))
area_of = d["area_of"]

empire_provs = empire_core()
areas = sorted({area_of[str(p)] for p in empire_provs})

all_areas = set(
    re.findall(
        r"^\t*([a-z_]+) = \{",
        open(f"{GAME}/map/area.txt", encoding="utf-8", errors="replace").read(),
        re.M,
    )
)
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
    f"{T*3}}}"
    for a in areas
)

held = "\n".join(
    f"{T*4}NOT = {{ {p} = {{ country_or_non_sovereign_subject_holds = ROOT }} }}"
    for p in empire_provs
)

txt = f"""country_decisions = {{

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
{claims}
\t\t}}
\t}}
}}
"""


def step_hre() -> None:

    os.makedirs(os.path.join(MOD, "decisions"), exist_ok=True)
    p = os.path.join(MOD, "decisions", "KarolingianHRE.txt")
    open(p, "w", encoding="utf-8").write(txt)
    print(f"wrote {p}")
    print(f"  imperial provinces    : {len(empire_provs)}")
    print(f"  areas covered         : {len(areas)}")
    print(f"  eligible tags         : any - the requirement is land, not a tag list")


START_DT = (1444, 11, 11)

DATE_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)\s*=\s*\{")
KV_RE = re.compile(r"\b(owner|controller|add_core|remove_core)\s*=\s*([A-Za-z0-9_]+)")
HRE_RE = re.compile(r"\bhre\s*=\s*(\w+)")


def split_header_and_blocks(lines):

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

    for t in TITLES:
        for p in alloc.get(t, []):
            expected[int(p)] = t

    bad_owner, bad_ctrl, bad_hre, contested = [], [], [], []
    for fn in sorted(os.listdir(PDIR)):
        pid = int(re.match(r"^(\d+)", fn).group(1))
        text = open(
            os.path.join(PDIR, fn), encoding="utf-8", errors="surrogateescape"
        ).read()
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

    print(
        f"provinces checked against the {START_DT[0]}.{START_DT[1]}.{START_DT[2]} start: {len(expected)}"
    )
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


import os
import re
import sys

GAME_CK3 = "/mnt/data/SteamLibrary/steamapps/common/Crusader Kings III/game"

DATE = "867.1.1"

HOUSE_NAME_OVERRIDE = {
    "house_abbasid": "dynn_Abbasid",
}


def _date_key(s: str) -> tuple:
    p = [int(x) for x in s.split(".")]
    return tuple(p + [0] * (3 - len(p)))


def _norm(text: str) -> str:

    return text.replace("\r\n", "\n").replace("\r", "\n")


def _blocks(text: str):

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
        yield m.group(1), text[m.end() : i]


def _inner_blocks(body: str):

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
        yield m.group(1), body[m.end() : i]


def load_titles():

    out = {}
    for f in sorted((Path(GAME_CK3) / "history" / "titles").glob("*.txt")):
        text = _norm(f.read_text(errors="replace")).lstrip("\ufeff")
        for tid, body in _blocks(text):
            out.setdefault(tid, []).extend(_inner_blocks(body))
    return out


def holder_at(title, titles):

    return holder_at_exact(title, titles)[0]


def holder_at_exact(title, titles):

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

    out = {}
    for f in sorted((Path(GAME_CK3) / "history" / "characters").glob("*.txt")):
        text = _norm(f.read_text(errors="replace")).lstrip("\ufeff")
        for cid, body in _blocks(text):
            out.setdefault(cid, body)
    return out


def load_dynasties():

    out = {}
    for f in sorted((Path(GAME_CK3) / "common" / "dynasties").glob("*.txt")):
        for key, body in _blocks(_norm(f.read_text(errors="replace"))):
            n = re.search(r'name\s*=\s*"(dynn_\w+)"', body)
            if n:
                out[key] = n.group(1)
    return out


def load_houses():

    out = {}
    for f in sorted((Path(GAME_CK3) / "common" / "dynasty_houses").glob("*.txt")):
        for key, body in _blocks(_norm(f.read_text(errors="replace"))):
            n = re.search(r'name\s*=\s*"?\s*(dynn_\w+)\s*"?', body)
            d = re.search(r"^\s*dynasty\s*=\s*(\w+)", body, re.M)
            name_key = n.group(1) if n else None
            out[key] = (
                HOUSE_NAME_OVERRIDE.get(key, name_key),
                d.group(1) if d else None,
            )
    return out


_LOC_FILES = None

_LOC_RE = re.compile(r'^[ \t]*([\w.\-]+)\s*:\d*\s*"(.*?)"[ \t\r\n]*$', re.M)


def loc(key):

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

                    _LOC_FILES.setdefault(k, v)
    return _LOC_FILES.get(key)


def resolve_dynasty(body, dyns, houses):

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

    title = TITLES[tag]

    ruler_title = RULER_TITLES.get(tag, title)
    cid, carried = holder_at_exact(ruler_title, titles)
    if cid is None:
        where = (
            f"CK3 has no 867 holder for {tag}'s title {title}"
            if ruler_title == title
            else f"CK3 has no 867 holder for {tag}'s ruler title {ruler_title} "
            f"(bound to {title})"
        )
        return {"error": where}
    body = chars.get(cid)
    if body is None:
        return {"error": f"CK3 has no character {cid} for {tag}"}

    nm = re.search(r'^\s*name\s*=\s*(?:"([^"]*)"|([^\s#"]+))', body, re.M)
    if not nm:
        return {"error": f"character {cid} has no name line"}
    raw = nm.group(1) or nm.group(2)

    name = loc(raw) or raw
    dy = resolve_dynasty(body, dyns, houses)
    return {
        "char": cid,
        "name": name,
        "dynasty": dy,
        "title": title,
        "ruler_title": ruler_title,
        "carried": carried,
        "no_dynasty": not dy,
    }


def land_holders():

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

    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    m = re.search(r"^1444\.1\.1 = \{\s*\n\tmonarch = \{(.*?)^\t\}", text, re.M | re.S)
    return text, (m.group(1) if m else None)


def current(body):

    if body is None:
        return (None, None)
    n = re.search(r'name = "([^"]+)"', body)
    d = re.search(r'dynasty = "([^"]+)"', body)
    return (n.group(1) if n else None, d.group(1) if d else None)


def heir_dynasty(text):

    blk = re.search(r"^1444\.1\.1 = \{\n(.*?)^\}", text, re.M | re.S)
    if not blk:
        return None
    heir = re.search(r"heir = \{(.*?)\n\t\}", blk.group(1), re.S)
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

    holders = land_holders()
    vanilla = {
        fn.split(" ")[0] for fn in os.listdir(VANILLA_CDIR) if fn.endswith(".txt")
    }
    kept_vanilla = sorted(
        t for t in holders if t not in TITLES and t not in NOT_CK3 and t in vanilla
    )
    unclassified = sorted(
        t for t in holders if t not in TITLES and t not in NOT_CK3 and t not in vanilla
    )
    print(f"== {len(holders)} tags own land at the mod start date ==")
    print(f"   CK3-derived (name/dynasty checked): {len(TITLES)}")
    print(f"   classified as not CK3-derived      : {len(NOT_CK3)}")
    print(f"   vanilla, untouched, ruler kept    : {len(kept_vanilla)}")
    for t in unclassified:
        bad.append(
            f"{t} owns {holders[t]} provinces at the start date but is in "
            f"neither TITLES nor NOT_CK3, and has no vanilla country file; "
            f"give it a Tag.no_ck3 reason so it is accounted for"
        )
    if unclassified:
        print(f"   UNCLASSIFIED: {', '.join(unclassified)}")
    stale = [t for t in NOT_CK3 if t not in holders]
    if stale:

        print(
            f"   note: NOT_CK3 lists tags with no land now: {', '.join(sorted(stale))}"
        )

    for tag in sorted(TITLES):
        got = resolve(tag, titles, chars, dyns, houses)
        path = COUNTRY_OUT / f"{tag}.txt"
        if "error" in got:
            bad.append(f"{tag}: {got['error']}")
            continue
        if not path.exists():

            print(f"  NOTE {tag} {got['title']} / char {got['char']}")
            print(f"        no {path.name}: keeps the vanilla file, nothing to sync")
            if got.get("no_dynasty"):
                print(
                    f"        CK3 867: name={got['name']!r} and NO dynasty - "
                    f"CK3 records neither dynasty nor dynasty_house for this "
                    f"character. Nothing is invented for it: if this tag ever "
                    f"gets a country file, map it to a title whose 867 holder "
                    f"has a dynasty."
                )
            else:
                print(
                    f"        CK3 867: name={got['name']!r} "
                    f"dynasty={got['dynasty']!r}"
                )
            unwritten.append(tag)
            continue
        text, body = monarch_block(path)
        cn, cd = current(body)
        if got.get("no_dynasty"):

            if cd is not None:
                bad.append(
                    f"{tag}: CK3 character {got['char']} ({got['name']}) has "
                    f"neither dynasty nor dynasty_house, but {path.name} "
                    f"declares dynasty={cd!r}. That dynasty is invented - "
                    f"drop it, or map the tag to a CK3 title whose 867 "
                    f"holder has a real one."
                )
                print(f"  FAIL {tag} {got['title']} / char {got['char']}")
                print(f"        file: name={cn!r} dynasty={cd!r}  <- INVENTED")
                print(f"        CK3 : name={got['name']!r} and NO dynasty")
            else:
                print(f"  OK   {tag} {got['title']} / char {got['char']}")
                print(f"        file: name={cn!r} dynasty={cd!r}")
                print(
                    f"        CK3 : name={got['name']!r} and NO dynasty - the file "
                    f"declares none either, which is the correct handling: CK3 "
                    f"records neither dynasty nor dynasty_house, so nothing is "
                    f"invented to cover the gap."
                )
            continue
        hd = heir_dynasty(text)
        heir_bad = (
            hd is not None and hd != got["dynasty"] and not BY_TAG[tag].no_heir_sync
        )
        ok = cn == got["name"] and cd == got["dynasty"] and not heir_bad
        mark = "OK " if ok else "DRIFT"
        src = (
            f"<- {got['title']}"
            + (
                f" (ruler from {got['ruler_title']})"
                if got.get("ruler_title", got["title"]) != got["title"]
                else ""
            )
            + (f" (holder carried from {got['carried']})" if got.get("carried") else "")
        )
        print(f"  {mark} {tag} {src} / char {got['char']}")
        print(f"        file: name={cn!r} dynasty={cd!r}")
        print(f"        CK3 : name={got['name']!r} dynasty={got['dynasty']!r}")
        if hd is not None:
            print(
                f"        heir dynasty={hd!r}"
                + ("  <- should match the ruler's" if heir_bad else "")
            )
        if not ok:
            if fix:

                blk = re.search(r"^1444\.1\.1 = \{\n(.*?)^\}", text, re.M | re.S)
                new = blk.group(1)
                if cn is not None:
                    new = re.sub(
                        r'name = "[^"]+"', f'name = "{got["name"]}"', new, count=1
                    )
                if cd is not None:
                    new = re.sub(
                        r'dynasty = "[^"]+"',
                        f'dynasty = "{got["dynasty"]}"',
                        new,
                        count=1,
                    )
                if heir_bad:
                    heir = re.search(r"heir = \{.*?\n\t\}", new, re.S)
                    nb = re.sub(
                        r'dynasty = "[^"]+"',
                        f'dynasty = "{got["dynasty"]}"',
                        heir.group(0),
                        count=1,
                    )
                    new = new[: heir.start()] + nb + new[heir.end() :]
                text = text[: blk.start(1)] + new + text[blk.end(1) :]
                path.write_text(text, encoding="utf-8", errors="surrogateescape")
                print(f"        fixed -> {got['name']} / {got['dynasty']}")
            else:
                if cn != got["name"] or cd != got["dynasty"]:
                    bad.append(
                        f"{tag}: file has {cn!r}/{cd!r}, CK3 has "
                        f"{got['name']!r}/{got['dynasty']!r}"
                    )
                if heir_bad:
                    bad.append(
                        f"{tag}: heir dynasty is {hd!r} but the ruler's is "
                        f"{got['dynasty']!r}"
                    )

    if bad:
        print("\nFAIL:")
        for b in bad:
            print("  " + b)
        return 1
    checked = len(TITLES) - len(unwritten)
    print(
        f"\nOK: all {len(holders)} start-date land-holders are accounted for; "
        f"{checked} of {len(TITLES)} CK3-mapped rulers match CK3's 867 bookmark"
        + (
            f", {len(unwritten)} unwritten ({', '.join(sorted(unwritten))}) "
            f"keep vanilla's file"
            if unwritten
            else ""
        )
        + (" (rewritten)" if fix else "")
    )
    return 0


_CK3_CACHE: dict = {}


def ck3_ruler(tag):

    if tag not in _CK3_CACHE:
        try:
            _c = sys.modules[__name__]
        except ImportError:
            _CK3_CACHE[tag] = None
            return None
        if tag not in _c.TITLES:
            _CK3_CACHE[tag] = None
            return None
        got = _c.resolve(
            tag,
            _c.load_titles(),
            _c.load_chars(),
            _c.load_dynasties(),
            _c.load_houses(),
        )

        _CK3_CACHE[tag] = None if got.get("error") or not got.get("dynasty") else got
    return _CK3_CACHE[tag]


def ck3_sync(tag, text):

    got = ck3_ruler(tag)
    if got is None:
        return text
    blk = re.search(r"^1444\.1\.1 = \{\n(.*?)^\}", text, re.M | re.S)
    if not blk:
        return text
    new = re.sub(r'name = "[^"]+"', f'name = "{got["name"]}"', blk.group(1), count=1)
    new = re.sub(r'dynasty = "[^"]+"', f'dynasty = "{got["dynasty"]}"', new)
    return text[: blk.start(1)] + new + text[blk.end(1) :]


def _eu4_skill(ck3_value):
    if ck3_value is None:
        return 2, None
    return max(1, min(6, round(int(ck3_value) / 3))), int(ck3_value)


def _ck3_dates_and_skills(cid, chars):

    body = chars.get(cid)
    if body is None:
        return None
    birth = death = None

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

    kids = [
        k for k, b in chars.items() if re.search(rf"^\s*father\s*=\s*{cid}\b", b, re.M)
    ]
    kids.sort(key=lambda k: _ck3_dates_and_skills(k, chars)[0] or "9999.9.9")
    if kids:
        lines += ["\their = {", person(kids[0], claim=90), "\t}"]
    lines += ["}", ""]
    return "\n".join(lines)


def find_vanilla(tag):
    for fn in os.listdir(VANILLA_CDIR):
        if fn.split(" ")[0] == tag and fn.endswith(".txt"):
            return os.path.join(VANILLA_CDIR, fn), fn
    raise SystemExit(f"no vanilla history file for {tag}")


def fresh(tag):
    t = BY_TAG[tag]
    cap, culture = t.capital, t.culture
    return f"""government = monarchy
add_government_reform = feudalism_reform
government_rank = {RANK[tag]}
technology_group = western
primary_culture = {culture}
religion = catholic
capital = {cap}
{t.ruler_block}"""


def patch_vanilla(tag, capital=None, ruler=None, strip_elector=False, rank=None):

    path, fn = find_vanilla(tag)
    text = open(path, encoding="utf-8", errors="surrogateescape").read()
    if strip_elector:

        text, n = re.subn(
            r"^elector\s*=\s*yes[^\n]*$", "elector = no", text, count=1, flags=re.M
        )
        assert n == 1, f"{tag}: no top-level 'elector = yes' to dissolve in {fn}"
    if capital is not None:

        m = re.search(r"^capital\s*=\s*(\d+)", text, flags=re.M)
        assert m, f"{tag}: no top-level capital line in {fn}"
        if int(m.group(1)) != capital:

            text, n = re.subn(
                r"^capital\s*=\s*\d+.*$",
                f"capital = {capital}",
                text,
                count=1,
                flags=re.M,
            )
            assert n == 1, f"{tag}: failed to patch capital in {fn}"
    if rank is not None:

        m = re.search(r"^government_rank\s*=\s*(\d+)", text, flags=re.M)
        if m and int(m.group(1)) != rank:
            text, n = re.subn(
                r"^government_rank\s*=\s*\d+.*$",
                f"government_rank = {rank}",
                text,
                count=1,
                flags=re.M,
            )
            assert n == 1, f"{tag}: failed to patch government_rank in {fn}"
        elif m is None:

            anchor = re.search(r"^\s*government\s*=\s*\w+.*$", text, re.M)
            assert anchor, f"{tag}: no government line to anchor a rank to in {fn}"
            text = (
                text[: anchor.end()]
                + f"\ngovernment_rank = {rank}"
                + text[anchor.end() :]
            )
    if ruler is not None:
        lines = text.splitlines()

        ins = len(lines)
        for i, ln in enumerate(lines):
            m = re.match(r"^(\d+)\.(\d+)\.(\d+)\s*=", ln.strip())
            if m and (int(m.group(1)), int(m.group(2)), int(m.group(3))) >= (
                1444,
                1,
                1,
            ):
                ins = i
                break
        block = ruler.strip("\n").splitlines()
        lines = lines[:ins] + block + [""] + lines[ins:]
        text = "\n".join(lines) + "\n"
    return text


def ruler_for(t):

    if t.ruler_block:
        return t.ruler_block
    if t.ck3_title:
        return ck3_block(t.tag)
    return None


def step_countries():

    os.makedirs(COUNTRY_OUT, exist_ok=True)
    for t in TAGS:
        if t.country == "written":
            continue
        if t.country == "none":
            continue
        if t.country == "fresh":
            text = ck3_sync(t.tag, fresh(t.tag))
            print(
                f"wrote {t.tag}.txt (from scratch, rank {t.rank}, "
                f"capital {t.capital})"
            )
        elif t.country == "vanilla":
            ruler = ruler_for(t)
            was_elector = t.tag in IMPERIAL_ELECTORS
            text = ck3_sync(
                t.tag, patch_vanilla(t.tag, t.capital, ruler, was_elector, t.rank)
            )
            what = []
            if t.capital:
                what.append(f"capital -> {t.capital}")
            if ruler:
                nm = re.search(r'name = "([^"]+)"', ruler)
                what.append(
                    f"867 ruler {nm.group(1) if nm else '?'}"
                    + (" (from CK3)" if not t.ruler_block else "")
                )
            if was_elector:
                what.append("electorate removed")
            what.append(f"rank {t.rank}")
            print(
                f"wrote {t.tag}.txt (vanilla history preserved, "
                + ", ".join(what)
                + ")"
            )
        else:
            text = patch_vanilla(t.tag, strip_elector=True)
            print(
                f"wrote {t.tag}.txt (vanilla history preserved, "
                f"electorate dissolved)"
            )

        with open(
            os.path.join(COUNTRY_OUT, f"{t.tag}.txt"),
            "w",
            encoding="utf-8",
            errors="surrogateescape",
        ) as fh:
            fh.write(text)


def main() -> int:

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
