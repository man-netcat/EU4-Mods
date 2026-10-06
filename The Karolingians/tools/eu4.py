#!/usr/bin/env python3

import json, os, re, shutil
from collections import defaultdict
from pathlib import Path

from ck3 import ck3_block, ck3_sync
from tagdb import (
    ALL_TAGS,
    AREA_OWNERS,
    BALATON_RESERVED,
    BY_TAG,
    IMPERIAL_ELECTORS,
    EMPIRE_KINGDOMS,
    PROVINCE_OWNERS,
    RANK,
    TAGS,
    TITLES,
    TRANSFERS,
)

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

UNTRACKED_OWNERS = {
    112: "VEN",
}

PROVINCE_OWNERS = {**UNTRACKED_OWNERS, **PROVINCE_OWNERS}

CAPITAL = {t.tag: t.capital for t in BY_TAG.values() if t.in_alloc and t.capital}
NAME = {tag: BY_TAG[tag].name for tag in AREA_OWNERS}

CULTURE_GONE_867 = {"turkish": "greek", "pontic_greek": "greek"}

CONQUERED_BY_THE_ARABS = {327, 332, 2303, 4298, 4310}

MUSLIM_RELIGIONS_867 = ("sunni", "shiite")

_PROVDATA = None


def _pd():
    global _PROVDATA
    if _PROVDATA is None:
        _PROVDATA = json.load(open(str(PROVDATA)))
    return _PROVDATA


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


def _owned(tag, region=None, exclude_regions=()):
    data = _pd()
    _AREA_OF, _REGION_OF_AREA = data["area_of"], data["region_of_area"]

    if isinstance(exclude_regions, str):
        exclude_regions = (exclude_regions,)
    out = []
    for pid, pr in data["provs"].items():
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
    data = _pd()
    return data["region_of_area"].get(data["area_of"].get(str(pid)))


def _area(*areas):
    data = _pd()
    out = set()
    for area in areas:
        out |= {int(pid) for pid in data["areas"].get(area, ())}
    return sorted(out)


def build(verbose=False):
    data = _pd()
    provs, AREAS = data["provs"], data["areas"]

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


def empire_core():
    alloc = build()
    return sorted({p for t in EMPIRE_KINGDOMS for p in alloc.get(t, ())})


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

    data = _pd()
    provs = data["provs"]
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
    data = _pd()
    provs = data["provs"]

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


T = "\t"


def step_hre() -> None:
    data = _pd()
    area_of = data["area_of"]

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
    kingdoms_or = "\n".join(f"{T*4}tag = {t}" for t in EMPIRE_KINGDOMS)

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
{kingdoms_or}
\t\t\t}}
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

    os.makedirs(os.path.join(MOD, "decisions"), exist_ok=True)
    p = os.path.join(MOD, "decisions", "KarolingianHRE.txt")
    open(p, "w", encoding="utf-8").write(txt)
    print(f"wrote {p}")
    print(f"  imperial provinces    : {len(empire_provs)}")
    print(f"  areas covered         : {len(areas)}")
    print(
        f"  eligible tags         : the five kingdoms only ({', '.join(EMPIRE_KINGDOMS)}), then the land"
    )


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


AREA = os.path.join(GAME, "map", "area.txt")
REGION = os.path.join(GAME, "map", "region.txt")


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
    for fn in os.listdir(VANILLA_PDIR):
        if not fn.endswith(".txt"):
            continue
        path = os.path.join(VANILLA_PDIR, fn)
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
    with open(str(PROVDATA), "w") as f:
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
