#!/usr/bin/env python3

import json, os, re, shutil
from collections import defaultdict
from pathlib import Path

from ck3 import ck3_sync
from histgen import (
    basin_provinces,
    country_definition,
    country_history,
    formation_decision,
    formation_trigger_block,
)
from tagdb import (
    AREA_OWNERS,
    BALATON_RESERVED,
    BY_TAG,
    DIPLOMACY,
    PROVINCES,
    PROVINCE_OWNERS,
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

CAPITAL = {t.tag: t.capital for t in BY_TAG.values() if t.capital}
NAME = {tag: BY_TAG[tag].name for tag in AREA_OWNERS}

_PROVDATA = None


def _pd():
    global _PROVDATA
    if _PROVDATA is None:
        _PROVDATA = json.load(open(str(PROVDATA)))
    return _PROVDATA


def apply_db_culture_religion(text, pid):
    """Write the province's 867 culture and religion from the database,
    leaving a line alone when the file already agrees (quoting included)."""
    p = PROVINCES[pid]
    for key, want in (("culture", p.culture), ("religion", p.religion)):
        if not want:
            continue
        m = re.search(rf'^(\s*){key}\s*=\s*"?(\w+)"?', text, re.M)
        if m and m.group(2) != want:
            text = text[: m.start()] + f"{m.group(1)}{key} = {want}" + text[m.end() :]
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

    for tag in alloc:
        alloc[tag] = sorted(set(alloc[tag]))

    if verbose:
        for pid, name, prev, tag in LAYER2_MOVES:
            print(f"  override: province {pid} {name} {prev} -> {tag}")
    return {s.tag: sorted(alloc[s.tag]) for s in TAGS if alloc.get(s.tag)}


def owner_map(alloc=None):
    alloc = build() if alloc is None else alloc
    return {p: t for t, ps in alloc.items() for p in ps}


def karling_realms():
    """(start dynasty, karling tags) lifted from CK3: the dynasty that the
    CK3-synced start holders share, and every CK3-synced tag whose start
    holder carries it."""
    from ck3 import load_chars, load_dynasties, load_houses, load_titles, resolve

    titles, chars = load_titles(), load_chars()
    dyns, houses = load_dynasties(), load_houses()
    dyn_of = {
        tag: resolve(tag, titles, chars, dyns, houses).get("dynasty")
        for tag in sorted(TITLES)
    }
    counts = {}
    for d in dyn_of.values():
        if d:
            counts[d] = counts.get(d, 0) + 1
    dynasty = max(counts, key=counts.get)
    ktags = sorted(t for t, d in dyn_of.items() if d == dynasty)
    return dynasty, ktags


def empire_core():
    alloc = build()
    _, ktags = karling_realms()
    tags = set(ktags)
    tags |= {d.subject for d in DIPLOMACY if d.liege in tags}
    return sorted({p for t in tags for p in alloc.get(t, ())})


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


PROV_DATE = "867.1.1"


def force_block(new_owner):
    return (
        f"\n{PROV_DATE} = {{\towner = {new_owner}\n"
        f"\tcontroller = {new_owner}\n"
        f"\tadd_core = {new_owner}\n"
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
    todo = sorted(set(owner_of) | set(BALATON_RESERVED))

    if os.path.isdir(PROV_OUT):
        shutil.rmtree(PROV_OUT)
    os.makedirs(PROV_OUT, exist_ok=True)

    written = 0
    missing = set(todo) - set(PROVINCES)
    if missing:
        raise SystemExit(f"provinces not in the database: {sorted(missing)}")
    for pid in todo:
        src = None
        for fn in os.listdir(VANILLA_PDIR):
            if re.match(rf"^{pid}\s*-.*\.txt$", fn):
                src = os.path.join(VANILLA_PDIR, fn)
                break
        if not src:
            print(f"!! no vanilla file for province {pid}")
            continue
        text = strip_dated(open(src, encoding="utf-8", errors="surrogateescape").read())
        text = apply_db_culture_religion(text, pid)
        tag = owner_of.get(pid)
        if pid in BALATON_RESERVED:
            new = unown(text)
        else:
            new = patch(text, tag) if tag else text

        open(
            os.path.join(PROV_OUT, os.path.basename(src)),
            "w",
            encoding="cp1252",
            errors="pdx",
        ).write(new)
        written += 1

    print(f"wrote {written} province files")
    for tag, ps in sorted(alloc.items(), key=lambda kv: -len(kv[1])):
        print(f"  {tag:4} {len(ps):3}")
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
        print(
            f"{tag} {NAME.get(tag, tag):13} n={len(ids):3} dev={sum(dev(p) for p in ids):6.0f}"
            + (f" cap={cap}({provs[str(cap)]['name']})" if cap else "")
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

    dynasty, ktags = karling_realms()
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
    dynasty_line = f'{T*3}dynasty = "{dynasty}"'

    txt = f"""country_decisions = {{

\tkar_form_hre = {{
\t\tmajor = yes

\t\tpotential = {{
\t\t\tNOT = {{ tag = HLR }}
{dynasty_line}
\t\t}}

\t\tprovinces_to_highlight = {{
\t\t\tkar_form_hre_provinces_trigger = yes
\t\t\tNOT = {{ owned_by = ROOT }}
\t\t}}

\t\tallow = {{
\t\t\tnum_of_owned_provinces_with = {{
\t\t\t\tcustom_trigger_tooltip = {{
\t\t\t\t\ttooltip = kar_form_hre_provinces_tooltip
\t\t\t\t\tkar_form_hre_provinces_trigger = yes
\t\t\t\t}}
\t\t\t\tvalue = {len(empire_provs)}
\t\t\t}}
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
    open(p, "w", encoding="cp1252", errors="pdx").write(txt)
    print(f"wrote {p}")
    print(f"  imperial provinces    : {len(empire_provs)}")
    print(f"  areas covered         : {len(areas)}")
    print(
        f"  karling dynasty (ck3): {dynasty} (tags: {', '.join(ktags)}), then the land"
    )


def step_diplomacy() -> None:
    lines = [
        "# Starting vassals of the Carolingian world.",
        "# No start_date: each holds from the mod's start.",
    ]
    for rel in DIPLOMACY:
        if rel.relation == "vassal":
            lines += [
                "vassal = {",
                "\tfirst = " + rel.liege,
                "\tsecond = " + rel.subject,
                "}",
            ]
        else:
            lines += [
                "dependency = {",
                "\tsubject_type = " + rel.relation,
                "\tfirst = " + rel.liege,
                "\tsecond = " + rel.subject,
                "}",
            ]
    path = os.path.join(MOD, "history", "diplomacy", "karolingian_vassals.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="cp1252", errors="pdx").write("\n".join(lines) + "\n")
    pairs = ", ".join(f"{d.subject} under {d.liege}" for d in DIPLOMACY)
    print(f"wrote {path}  ({pairs})")


def load_vanilla_countries() -> dict[str, tuple[str, str]]:
    """{tag: (filename, text)} for every vanilla country definition."""
    out = {}
    cd = os.path.join(GAME, "common", "countries")
    for fn in os.listdir(os.path.join(GAME, "common", "country_tags")):
        if not fn.endswith(".txt"):
            continue
        text = open(
            os.path.join(GAME, "common", "country_tags", fn),
            encoding="cp1252",
            errors="replace",
        ).read()
        for m in re.finditer(r'^([A-Z]{3})\s*=\s*"countries/([^"]+)"', text, re.M):
            p = os.path.join(cd, m.group(2))
            if os.path.exists(p):
                base = open(p, encoding="cp1252", errors="replace").read()
                out.setdefault(m.group(1), (m.group(2), base))
    return out


def step_vanilla_countries() -> None:
    """Rewrite the vanilla realms' country definitions under the mod, copying
    the vanilla data verbatim and swapping in the colour lifted from CK3, so
    every tag covered by the mod matches its CK3 title's map colour."""
    from ck3 import load_title_colors

    colors = load_title_colors()
    vanilla = load_vanilla_countries()
    os.makedirs(os.path.join(MOD, "common", "countries"), exist_ok=True)
    written = 0
    for t in TAGS:
        want = colors.get(t.ck3_title) if t.ck3_title else None
        base = vanilla.get(t.tag)
        if not want or not base:
            continue
        fn, text = base
        body = re.sub(
            r"(?m)^color = \{.*?\}",
            f"color = {{ {want[0]}  {want[1]}  {want[2]} }}",
            text,
            count=1,
        )
        if body == text:
            print(f"  {t.tag}: {t.ck3_title} colour {want} already {fn}?")
        p = os.path.join(MOD, "common", "countries", fn)
        open(p, "w", encoding="cp1252", errors="pdx").write(body)
        print(f"wrote {p}  (colour from {t.ck3_title} = {want})")
        written += 1
    print(f" {written} vanilla realm definitions rewritten under the mod")


def step_custom() -> None:
    vanilla = load_vanilla_countries()
    customs = [t for t in TAGS if t.tag not in vanilla]
    if not customs:
        return

    os.makedirs(os.path.join(MOD, "common", "country_tags"), exist_ok=True)
    os.makedirs(os.path.join(MOD, "common", "countries"), exist_ok=True)
    os.makedirs(os.path.join(MOD, "gfx", "flags"), exist_ok=True)

    reg = os.path.join(MOD, "common", "country_tags", "00_karolingian_custom.txt")
    reg_lines = []

    for t in customs:
        cname = t.country_file or f"{t.name}.txt"
        reg_lines.append(f'{t.tag} = "countries/{cname}"')

        cfile = os.path.join(MOD, "common", "countries", cname)
        open(cfile, "w", encoding="cp1252", errors="pdx").write(country_definition(t))
        print(f"wrote {cfile}")

        flag = t.flag_source or os.path.join(GAME, "gfx", "flags", f"{t.flag_from}.tga")
        assert os.path.exists(flag), f"no flag for {t.tag} at {flag}"
        dest = os.path.join(MOD, "gfx", "flags", f"{t.tag}.tga")
        if os.path.exists(dest):
            print(f"kept gfx/flags/{t.tag}.tga (custom, not overwritten)")
        else:
            shutil.copy2(flag, dest)
            print(f"copied gfx/flags/{t.tag}.tga")

        if not t.forms:
            print(f"  {t.tag} has no formable tag")
            continue

        basin = basin_provinces(t)
        txt = formation_decision(t)
        os.makedirs(os.path.join(MOD, "decisions"), exist_ok=True)
        p = os.path.join(MOD, "decisions", f"Form{t.forms}.txt")
        open(p, "w", encoding="cp1252", errors="pdx").write(txt)
        print(f"wrote {p}")
        print(
            f"  formed tag            : {t.tag} -> {t.forms}, rank {t.form_rank or 2}"
        )
        print(f"  basin provinces       : {len(basin)}")
        print(f"  areas covered         : {', '.join(t.form_areas)}")
        print(f"  suppressed decisions  : {', '.join(t.suppress)}")

    open(reg, "w", encoding="cp1252", errors="pdx").write("\n".join(reg_lines) + "\n")
    print(f"wrote {reg}")


def step_formation_triggers() -> None:
    specs = [("kar_form_hre", empire_core())]
    for t in TAGS:
        if t.forms:
            specs.append((t.decision, basin_provinces(t)))

    body = "\n\n".join(
        formation_trigger_block(f"{k}_provinces_trigger", p) for k, p in specs
    )
    sdir = os.path.join(MOD, "common", "scripted_triggers")
    os.makedirs(sdir, exist_ok=True)
    spath = os.path.join(sdir, "KarolingianFormations.txt")
    open(spath, "w", encoding="cp1252", errors="pdx").write(
        "# province triggers backing the formation decisions\n" + body + "\n"
    )
    print(f"wrote {spath}  ({len(specs)} triggers)")

    old = os.path.join(
        MOD, "common", "trigger_localisation", "KarolingianFormations_l_english.yml"
    )
    if os.path.exists(old):
        os.remove(old)


def strip_dated(text):
    out, depth = [], 0
    for ln in text.splitlines():
        if re.match(r"^\s*\d+\.\d+\.\d+\s*=", ln):
            break
        out.append(ln)
        code = ln.split("#", 1)[0]
        depth += code.count("{") - code.count("}")
    while out and not out[-1].strip():
        out.pop()
    while depth > 0:
        out.append("}")
        depth -= 1
    return "\n".join(out) + "\n"


def step_countries():
    os.makedirs(COUNTRY_OUT, exist_ok=True)
    for t in TAGS:
        text = ck3_sync(t.tag, country_history(t))
        with open(
            os.path.join(COUNTRY_OUT, f"{t.tag}.txt"),
            "w",
            encoding="cp1252",
            errors="pdx",
        ) as fh:
            fh.write(text)
        print(f"wrote {t.tag}.txt (rank {t.rank}, capital {t.capital})")


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
        depth += opens - closes
        if depth < 0:
            depth = 0
    return scalars, cores0, cores_all


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


if vanilla_is_newer():
    print("\n\033[1m==> probe vanilla province history\033[0m", flush=True)
    step_probe()
else:
    print("\n\033[1m==> probe\033[0m\n    cache is current, skipping")

START_DT = (867, 1, 1)

DATE_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)\s*=\s*\{")
KV_RE = re.compile(r"\b(owner|controller|add_core|remove_core)\s*=\s*([A-Za-z0-9_]+)")


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
    return owner, controller, cores


def step_start():
    alloc = build()
    expected = {}

    for t in TITLES:
        for p in alloc.get(t, []):
            expected[int(p)] = t

    bad_owner, bad_ctrl, contested = [], [], []
    for fn in sorted(os.listdir(PDIR)):
        pid = int(re.match(r"^(\d+)", fn).group(1))
        text = open(
            os.path.join(PDIR, fn), encoding="utf-8", errors="surrogateescape"
        ).read()
        owner, controller, cores = effective(text)
        want = expected.get(pid)
        if want is None:
            continue
        if owner != want:
            bad_owner.append((pid, fn, want, owner))
        if controller != want:
            bad_ctrl.append((pid, fn, want, controller))
        if want in cores:
            contested.append((pid, fn))

    print(
        f"provinces checked against the {START_DT[0]}.{START_DT[1]}.{START_DT[2]} start: {len(expected)}"
    )
    print(f"  owner    != intended : {len(bad_owner)}")
    print(f"  controller!= intended: {len(bad_ctrl)}")
    for pid, fn, want, got in bad_owner[:20]:
        print(f"     {pid:5} {fn[:30]:30} want {want} got {got}")
    if bad_owner or bad_ctrl:
        print("\nFAIL: vanilla events still win at the start date")
        return 1
    print("\nOK: every intended province is held at the start date")
    return 0
