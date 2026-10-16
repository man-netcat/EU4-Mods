#!/usr/bin/env python3

import json, os, re, shutil
from functools import lru_cache
from pathlib import Path

from ck3 import (
    ck3_sync,
    load_chars,
    load_dynasties,
    load_houses,
    load_title_colors,
    load_titles,
    resolve,
)
from db import core_deny_map
from histgen import (
    area_claim_lines,
    country_definition,
    country_history,
    formation_capital_trigger_block,
    formation_decision,
    formation_trigger_block,
    requirement_provinces,
)
from tagdb import (
    AREA_OWNERS,
    BY_FORMABLE,
    BY_TAG,
    CTRY_DATE,
    DIPLOMACY,
    FORMABLES,
    PROVINCES,
    PROVINCE_OWNERS,
    SEED_CORES,
    TAGS,
    TITLES,
    WARS,
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

CAPITAL = {t.tag: t.capital for t in BY_TAG.values() if t.capital}

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


def build() -> dict:
    data = _pd()
    provs, AREAS = data["provs"], data["areas"]

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

    for tag in alloc:
        alloc[tag] = sorted(set(alloc[tag]))

    return {s.tag: sorted(alloc[s.tag]) for s in TAGS if alloc.get(s.tag)}


def karling_realms():
    """(start dynasty, karling tags) lifted from CK3: the dynasty that the
    CK3-synced start holders share, and every CK3-synced tag whose start
    holder carries it."""
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


#: Decisions with no formables row that still need province triggers:
#: decision key -> requirement areas. Finland crowns in place through its
#: custom kingdom file (like Denmark/Norway/Sweden it wants the capital
#: in the homeland), so its land lives here instead of the database.
CUSTOM_TRIGGERS = {
    "kar_form_finland": ("finland_area", "bothnia_area"),
}


_VANILLA_PROV_FILES: dict = {}


def vanilla_prov_file(pid):
    # pid -> vanilla history/provinces path, via one directory scan: the
    # per-pid listdir this replaces was the slowest loop in the province step.
    if not _VANILLA_PROV_FILES:
        for fn in os.listdir(VANILLA_PDIR):
            m = re.match(r"^(\d+)\s*-.*\.txt$", fn)
            if m:
                _VANILLA_PROV_FILES.setdefault(int(m.group(1)), fn)
    fn = _VANILLA_PROV_FILES.get(pid)
    return os.path.join(VANILLA_PDIR, fn) if fn else None


def vanilla_prov_ids():
    # Every province id with a vanilla history file.
    if not _VANILLA_PROV_FILES:
        vanilla_prov_file(0)
    return sorted(_VANILLA_PROV_FILES)


def _vanilla_id_set(path, section, flags=0):
    # Province ids from a vanilla map section (sea_starts, impassable,
    # lakes): grey/water land we never own, only restore visibility for.
    txt = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(section + r"\s*=\s*\{(.*?)\}", txt, re.S | flags)
    return sorted({int(x) for x in re.findall(r"\d+", m.group(1))})


def sea_ids():
    # The engine's own sea list: every water province whose visibility we
    # restore verbatim from vanilla (sea files carry only discovered_by).
    return _vanilla_id_set(os.path.join(GAME, "map", "default.map"), r"sea_starts")


def waste_ids():
    # The engine's own wasteland list: every province in the impassable
    # section of vanilla map/climate.txt renders grey and always-visible.
    # We ship no map files, so the set is vanilla's; like sea tiles these
    # files carry only discovered_by and keep their tech-group lines.
    return _vanilla_id_set(os.path.join(GAME, "map", "climate.txt"), r"impassable")


def lake_ids():
    # The engine's own lake list from vanilla map/default.map: water that
    # is neither sea nor land. Same treatment as sea and wasteland.
    return _vanilla_id_set(os.path.join(GAME, "map", "default.map"), r"^lakes", re.M)


START_DT = tuple(int(x) for x in CTRY_DATE.split("."))


def force_block(new_owner, claims=()):
    lines = [
        f"\n{CTRY_DATE} = {{",
        f"\towner = {new_owner}",
        f"\tcontroller = {new_owner}",
        f"\tadd_core = {new_owner}",
    ] + [f"\tadd_claim = {c}" for c in claims] + [
        "}",
        "",
    ]
    return "\n".join(lines)


#: EU4 areas of Iberia: Andalusi-held land here carries the Reconquista.
IBERIA_AREAS = frozenset(
    "alentejo_area aragon_area asturias_area baleares_area basque_country "
    "beieras_area castille_area catalonia_area extremadura_area galicia_area "
    "leon_area lower_andalucia_area toledo_area upper_andalucia_area "
    "valencia_area".split()
)


#: HUN requirement land: whoever holds it carries Magyar migration claims
#: (CK3 hungarian_migration_cb, translated as claims + the existing HUN
#: path — no timer, no custom CB).
HUN_AREAS = frozenset(
    "alfold_area southern_transylvania_area transdanubia_area "
    "transylvania_area".split()
)

#: Who carries conquest claims, and on whose land: exact (owner, areas)
#: matches. Whoever holds the Hungarian basin answers MGY instead (CK3's
#: migration CB as claims); MGY itself never claims its own cradle.
CLAIM_RULES = (
    # Andalusi Iberia feeds the Reconquista (ASU/NAV claims).
    ("ADU", IBERIA_AREAS, ("ASU", "NAV")),
    # Vimara's 868 targets (CK3 war_867_Vimara_conquest_Portucale).
    ("PRT", frozenset({"beieras_area"}), ("ASU",)),
)


PROV_FIELD_ORDER = (
    "owner",
    "controller",
    "add_core",
    "capital",
    "culture",
    "religion",
    "hre",
    "base_tax",
    "base_production",
    "trade_goods",
    "base_manpower",
    "is_city",
    "fort_15th",
    "center_of_trade",
)


def tidy_province(text):
    # Canonical layout for owned-province files: title comment, identity
    # and economy fields in a fixed order, discovery lines, dated blocks
    # last. Unknown keys keep their relative order after the known fields;
    # comments stay glued to the line they precede. No data is dropped.
    rank = {k: i for i, k in enumerate(PROV_FIELD_ORDER)}
    header, fields, found, blocks = [], [], [], []
    pending, cur, depth = [], None, 0
    seen_content = False
    it = iter(text.splitlines())
    for ln in it:
        s = ln.strip()
        if not seen_content:
            if not s or s.startswith("#"):
                if s:
                    header.append(ln.rstrip())
                continue
            seen_content = True
        if cur is not None:
            cur.append(ln.rstrip())
            code = ln.split("#", 1)[0]
            depth += code.count("{") - code.count("}")
            if depth <= 0:
                blocks.append(cur)
                cur = None
            continue
        if not s:
            continue
        if s.startswith("#"):
            pending.append(ln.rstrip())
            continue
        if re.match(r"^\d+\.\d+\.\d+\s*=", s):
            cur = pending + [ln.rstrip()]
            pending = []
            code = ln.split("#", 1)[0]
            depth = code.count("{") - code.count("}")
            if depth <= 0:
                blocks.append(cur)
                cur = None
            continue
        m = re.match(r"^([A-Za-z_]+)\s*=", s)
        key = m.group(1) if m else ""
        unit = pending + [ln.rstrip()]
        pending = []
        code = ln.split("#", 1)[0]
        bal = code.count("{") - code.count("}")
        while bal > 0:
            nxt = next(it, None)
            if nxt is None:
                break
            unit.append(nxt.rstrip())
            c2 = nxt.split("#", 1)[0]
            bal += c2.count("{") - c2.count("}")
        if key == "discovered_by" and len(unit) == 1:
            found.extend(unit)
        else:
            fields.append((rank.get(key, len(rank)), len(fields), unit))
    if pending:
        fields.append((len(rank), len(fields), pending))
    fields = [ln for _, _, ls in sorted(fields) for ln in ls]
    out = header + [""] + fields if header else fields
    if found:
        out += [""] + found
    for b in blocks:
        out += [""] + b
    return "\n".join(out).strip("\n") + "\n"


def patch(text, new_owner, pid=None):
    out, i, n = [], 0, len(text.splitlines())
    lines = text.splitlines()

    dated_start = len(lines)
    for idx, ln in enumerate(lines):
        s = ln.strip()
        if re.match(r"^\d+\.\d+\.\d+\s*=", s):
            dated_start = idx
            break

    old_owner = None
    for idx in range(dated_start):
        m = re.match(r"^\s*owner\s*=\s*([A-Z]{3})\s*$", lines[idx])
        if m:
            old_owner = m.group(1)
            break
    # HLR is formable-only (no landed row), so without the exception its
    # cores would be stripped as dead; the formation and its neutralized
    # history need them.
    live = {s.tag for s in TAGS} | {"HLR"}
    drop_cores = (
        old_owner
        if old_owner and old_owner != new_owner and old_owner in live
        else None
    )

    head = []
    if pid is not None and not any(
        re.match(r"^\s*owner\s*=", lines[idx]) for idx in range(dated_start)
    ):
        # Vanilla-empty province (no top-level fields): seed the header from
        # the DB. Economy default mirrors the empty northern belt (fur, 1/1/1).
        info = PROVINCES.get(pid)
        head = [
            f"owner = {new_owner}",
            f"controller = {new_owner}",
            f"add_core = {new_owner}",
            f"culture = {info.culture if info else 'nomad'}",
            f"religion = {info.religion if info else 'animism'}",
            "hre = no",
            "base_tax = 1",
            "base_production = 1",
            "trade_goods = fur",
            "base_manpower = 1",
            "is_city = yes",
            "",
        ]

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

        if drop_cores and re.match(
            rf"^\s*add_core\s*=\s*{re.escape(drop_cores)}\s*$", s
        ):
            continue

        out.append(ln)

    have_core = any(
        re.match(rf"^\s*add_core\s*=\s*{re.escape(new_owner)}\s*$", lines[idx])
        for idx in range(dated_start)
    )
    core_line = f"add_core = {new_owner}"
    claims = []
    if pid is not None:
        area = _pd()["area_of"].get(str(pid))
        match = next(
            (
                claimants
                for owner, areas, claimants in CLAIM_RULES
                if new_owner == owner and area in areas
            ),
            (),
        )
        claims = list(match)
        if not claims and new_owner != "MGY" and area in HUN_AREAS:
            claims = ["MGY"]
    if not have_core:
        last_core = None
        for idx in range(dated_start):
            if re.match(r"^\s*add_core\s*=", lines[idx]):
                last_core = idx
        if last_core is not None:
            out.insert(last_core + 1, core_line)
        elif not head:
            out.insert(dated_start, core_line)

    return "\n".join(head + out) + "\n" + force_block(new_owner, claims)


def strip_fort(text):
    # Drop the vanilla fortress: only provinces flagged in the database
    # keep (or gain) one, everything else goes.
    out = []
    for ln in text.splitlines():
        if re.match(r"^\s*fort_15th\s*=", ln):
            continue
        out.append(ln)
    return "\n".join(out) + "\n"


def ensure_fort(text, want):
    has = bool(re.search(r"(?m)^\s*fort_15th\s*=", text))
    if want and not has:
        text, n = re.subn(
            r"(?m)^(\s*is_city\s*=.*)$", r"\1\nfort_15th = yes", text, count=1
        )
        if not n:
            text = text.rstrip("\n") + "\nfort_15th = yes"
    elif has and not want:
        text = strip_fort(text)
    return text


def strip_dead_cores(text, keep):
    # Cores are respawn vectors: any tag cored here can come back via rebels
    # or release, so only living tags keep cores.
    out = []
    for ln in text.splitlines():
        m = re.match(r"^\s*add_core\s*=\s*([A-Z]{3})\b", ln)
        if m and m.group(1) not in keep:
            continue
        out.append(ln)
    return "\n".join(out) + "\n"


def strip_denied_cores(text, owner, denied):
    # Dormant claims judged dead by hand live in core_deny(holder, owner):
    # a living holder keeps no cores on that owner's land. The map is
    # preloaded once per build (db.core_deny_map) - never per province.
    if not owner:
        return text
    gone = denied.get(owner)
    if not gone:
        return text
    out = []
    for ln in text.splitlines():
        m = re.match(r"^\s*add_core\s*=\s*([A-Z]{3})\b", ln)
        if m and m.group(1) in gone:
            continue
        out.append(ln)
    return "\n".join(out) + "\n"


def take_group_visibility(text):
    # Visibility everywhere: keep only tech-group discovered_by lines.
    # No tag-specific discoveries: dead tags spam the log, and living tags
    # see their land and surroundings through simple group vision anyway.
    out = []
    for ln in text.splitlines():
        m = re.match(r"^\s*discovered_by\s*=\s*([A-Za-z_]+)\s*$", ln)
        if m and re.match(r"^[A-Z]{3}$", m.group(1)):
            continue
        out.append(ln)
    return "\n".join(out) + "\n"


def undated_group_visibility(full):
    # Tech-group discovered_by at depth 0 anywhere in the file. Vanilla
    # sometimes parks them between dated blocks (Bearn 176); strip_dated
    # only sees the head, so harvest here to keep visibility identical.
    out, depth = [], 0
    for ln in full.splitlines():
        if depth == 0:
            m = re.match(r"^\s*discovered_by\s*=\s*([A-Za-z_]+)\s*$", ln)
            if (
                m
                and not re.match(r"^[A-Z]{3}$", m.group(1))
                and ln not in out
            ):
                out.append(ln)
        code = ln.split("#", 1)[0]
        depth += code.count("{") - code.count("}")
    return out


def write_out(path, text, encoding="cp1252", errors="pdx"):
    """Write one generated file: cp1252 with the pdx handler like every
    generated game file (the events/decisions vendoring passes utf-8)."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    open(path, "w", encoding=encoding, errors=errors).write(text)


def step_provinces():
    alloc = build()

    owner_of = {p: t for t, ps in alloc.items() for p in ps}
    # HLR as above: its cores survive the dead-core strip.
    keep = {s.tag for s in TAGS} | {"HLR"}

    data = _pd()
    provs = data["provs"]
    todo = sorted(owner_of)

    if os.path.isdir(PROV_OUT):
        shutil.rmtree(PROV_OUT)
    os.makedirs(PROV_OUT, exist_ok=True)

    written = 0
    missing = set(todo) - set(PROVINCES)
    if missing:
        raise SystemExit(f"provinces not in the database: {sorted(missing)}")
    denied = core_deny_map()
    for pid in todo:
        src = vanilla_prov_file(pid)
        if not src:
            print(f"!! no vanilla file for province {pid}")
            continue
        src_text = open(src, encoding="utf-8", errors="surrogateescape").read()
        text = strip_dated(src_text)
        text = apply_db_culture_religion(text, pid)
        tag = owner_of.get(pid)
        new = patch(text, tag, pid) if tag else text
        new = ensure_fort(new, PROVINCES[pid].fort)
        for st in SEED_CORES.get(pid, ()):
            new += f"add_core = {st}\n"
        new = take_group_visibility(new)
        for ln in undated_group_visibility(src_text):
            if ln not in new.splitlines():
                new += ln + "\n"
        new = strip_dead_cores(new, keep)
        new = strip_denied_cores(new, tag, denied)
        new = tidy_province(new)

        write_out(os.path.join(PROV_OUT, os.path.basename(src)), new)
        written += 1

    sea = sea_ids()
    clashes = [p for p in sea if p in owner_of]
    assert not clashes, f"sea ids overlap our land: {clashes}"
    copied = 0
    for pid in sea:
        src = vanilla_prov_file(pid)
        if src:
            text = strip_dated(
                open(src, encoding="utf-8", errors="surrogateescape").read()
            )
            write_out(os.path.join(PROV_OUT, os.path.basename(src)), text)
            copied += 1
    print(f"copied {copied} vanilla sea files (undated head only)")

    waste = waste_ids()
    wclash = [p for p in waste if p in owner_of]
    assert not wclash, f"impassable ids overlap our land: {wclash}"
    wcopied = 0
    for pid in waste:
        if pid in sea:
            continue
        src = vanilla_prov_file(pid)
        if src:
            text = open(src, encoding="utf-8", errors="surrogateescape").read()
            write_out(
                os.path.join(PROV_OUT, os.path.basename(src)),
                take_group_visibility(strip_dated(text)),
            )
            wcopied += 1
    print(f"restored {wcopied} vanilla wasteland files (tech groups only)")

    lakes = lake_ids()
    lclash = [p for p in lakes if p in owner_of]
    assert not lclash, f"lake ids overlap our land: {lclash}"
    lcopied = 0
    for pid in lakes:
        if pid in sea:
            continue
        src = vanilla_prov_file(pid)
        if src:
            text = open(src, encoding="utf-8", errors="surrogateescape").read()
            write_out(
                os.path.join(PROV_OUT, os.path.basename(src)),
                take_group_visibility(strip_dated(text)),
            )
            lcopied += 1
    print(f"restored {lcopied} vanilla lake files (tech groups only)")

    have = set(todo) | set(sea) | set(waste) | set(lakes)
    rest = sorted(p for p in vanilla_prov_ids() if p not in have)
    vcopied = 0
    for pid in rest:
        src = os.path.join(VANILLA_PDIR, _VANILLA_PROV_FILES[pid])
        text = strip_dated(
            open(src, encoding="utf-8", errors="surrogateescape").read()
        )
        lines = text.splitlines()
        title = next((ln for ln in lines if ln.strip().startswith("#")), f"#{pid}")
        seen = [
            ln
            for ln in undated_group_visibility(
                open(src, encoding="utf-8", errors="surrogateescape").read()
            )
        ]
        body = take_group_visibility("\n".join(seen) + "\n") if seen else ""
        write_out(os.path.join(PROV_OUT, _VANILLA_PROV_FILES[pid]), f"{title}\n\n{body}")
        vcopied += 1
    print(f"wrote {vcopied} visibility-only files for unowned provinces")

    print(f"wrote {written} province files")
    for tag, ps in sorted(alloc.items(), key=lambda kv: -len(kv[1])):
        print(f"  {tag:4} {len(ps):3}")
    print(f"  total            : {len(todo)}")


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

    claims = "\n".join(area_claim_lines(areas))
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
\t\t\tset_in_empire = no
\t\t\tset_country_flag = kar_formed_hre
\t\t\thidden_effect = {{
\t\t\t\tset_government_rank = 4
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
    write_out(p, txt)
    print(f"wrote {p}")
    print(f"  imperial provinces    : {len(empire_provs)}")
    print(f"  areas covered         : {len(areas)}")
    print(
        f"  karling dynasty (ck3): {dynasty} (tags: {', '.join(ktags)}), then the land"
    )


def step_diplomacy() -> None:
    lines = [
        "# Starting subjects and guarantees of the Carolingian world.",
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
        elif rel.relation == "guarantee":
            lines += [
                "guarantee = {",
                "\tfirst = " + rel.liege,
                "\tsecond = " + rel.subject,
                "}",
            ]
        elif rel.relation == "union":
            lines += [
                "union = {",
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
    lines += [
        "867.1.1 = { celestial_emperor = TNG }",
    ]
    write_out(path, "\n".join(lines) + "\n")
    pairs = ", ".join(f"{d.subject} under {d.liege}" for d in DIPLOMACY)
    print(f"wrote {path}  ({pairs})")


def step_wars() -> None:
    wdir = os.path.join(MOD, "history", "wars")
    os.makedirs(wdir, exist_ok=True)
    for w in WARS:
        sides = "\n".join(
            [f"\tadd_attacker = {t}" for t in w.attackers]
            + [f"\tadd_defender = {t}" for t in w.defenders]
        )
        objective = (
            f"\tprovince = {w.goal_province}"
            if w.goal_province
            else f"\ttag = {w.goal_tag}"
        )
        txt = (
            f'name = "{w.title}"\n'
            f"war_goal = {{\n"
            f"\ttype = {w.goal}\n"
            f"\tcasus_belli = {w.cb}\n"
            f"{objective}\n"
            f"}}\n\n"
            f"{w.date} = {{\n{sides}\n}}\n"
        )
        p = os.path.join(wdir, f"{w.slug}.txt")
        write_out(p, txt)
        print(f"wrote {p}  ({w.title})")


@lru_cache(maxsize=1)
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
    colors = load_title_colors()
    vanilla = load_vanilla_countries()
    os.makedirs(os.path.join(MOD, "common", "countries"), exist_ok=True)
    written = 0
    pairs = [(t.tag, t.ck3_title) for t in TAGS]
    pairs += [(fb.tag, fb.ck3_title) for fb in FORMABLES]
    for code, title in pairs:
        want = colors.get(title) if title else None
        base = vanilla.get(code)
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
            print(f"  {code}: {title} colour {want} already {fn}?")
        p = os.path.join(MOD, "common", "countries", fn)
        write_out(p, body)
        print(f"wrote {p}  (colour from {title} = {want})")
        written += 1
    print(f" {written} vanilla realm definitions rewritten under the mod")


VANILLA_FORMATION_FILES = {
    # Vanilla decision file -> formation keys we neutralize there.
    "IrishNation.txt": ["irish_nation"],
    "EnglishNation.txt": ["english_nation"],
    "HungarianNation.txt": ["hungarian_nation"],
    "PolishNation.txt": ["polish_nation"],
    "BritishNation.txt": ["british_nation", "british_nation_diplomatically"],
    "MiscCountryFormations.txt": ["icelandic_nation"],
    "HRE_FormableNations.txt": ["pomerania_nation"],
    "ScandinavianNation.txt": ["scandinavian_nation"],
    "RestoreRomanEmpire.txt": ["restore_roman_empire"],
}


def all_known_tags():
    """Every 3-letter tag vanilla can name. Ours are irrelevant here: we
    want vanilla's tag-specific content invalid, whatever names it uses."""
    found = set()
    vd = os.path.join(GAME, "common", "country_tags")
    for fn in os.listdir(vd):
        if fn.endswith(".txt"):
            found.update(
                re.findall(r"^([A-Z]{3})\s*=",
                           open(os.path.join(vd, fn), encoding="cp1252",
                                errors="replace").read(), re.M))
    return found


def event_mentions_tag(block, tagset):
    """True when an event block names any tag (comments stripped first, so
    prose like '# England wins' never counts)."""
    for ln in block.splitlines():
        code = ln.split("#", 1)[0]
        for tok in re.findall(r"\b([A-Z]{3})\b", code):
            if tok in tagset:
                return True
    return False


def split_event_blocks(text):
    """Yield (kind, lines) with kind 'event' for country_/province_event
    blocks and 'other' for everything else (namespace, headers, blanks)."""
    out, cur, depth = [], None, 0
    for ln in text.splitlines():
        s = ln.strip()
        if cur is None:
            if re.match(r"^(country_event|province_event)\s*=\s*\{", s):
                cur = [ln]
                code = ln.split("#", 1)[0]
                depth = code.count("{") - code.count("}")
                if depth <= 0:
                    out.append(("event", cur))
                    cur = None
            else:
                out.append(("other", [ln]))
        else:
            cur.append(ln)
            code = ln.split("#", 1)[0]
            depth += code.count("{") - code.count("}")
            if depth <= 0:
                out.append(("event", cur))
                cur = None
    if cur is not None:
        out.append(("event", cur))
    return out


def step_events() -> None:
    """Vendor vanilla events with tag-specific events cut out: any event
    naming a tag goes (it belongs to another century or a dead realm),
    everything generic stays byte-identical. Our own files (non-vanilla
    names) are never touched."""
    tagset = all_known_tags()
    vdir = os.path.join(GAME, "events")
    edir = os.path.join(MOD, "events")
    os.makedirs(edir, exist_ok=True)
    vanilla = {fn for fn in os.listdir(vdir) if fn.endswith(".txt")}
    kept_files, kept_events, dropped = 0, 0, 0
    for fn in sorted(vanilla):
        text = open(os.path.join(vdir, fn), encoding="utf-8",
                    errors="replace").read()
        segs = split_event_blocks(text)
        keep = []
        for kind, lines in segs:
            if kind == "event" and event_mentions_tag("\n".join(lines), tagset):
                dropped += 1
                continue
            keep.append(lines)
            if kind == "event":
                kept_events += 1
        body = ["\n".join(ls) for ls in keep]
        while len(body) > 1 and not body[-1].strip():
            body.pop()
        out = "\n".join(body)
        if not out.endswith("\n"):
            out += "\n"
        dest = os.path.join(edir, fn)
        old = None
        if os.path.exists(dest):
            old = open(dest, encoding="utf-8", errors="replace").read()
        if old != out:
            write_out(dest, out, encoding="utf-8", errors="strict")
        kept_files += 1
    print(f"events: {kept_files} files, {kept_events} generic events kept, "
          f"{dropped} tag-specific dropped")


def split_decision_blocks(text):
    """Yield (kind, key, lines): 'decision' for named blocks at the top
    level or directly inside the *_decisions wrappers, 'other' for
    wrappers, comments and blanks."""
    out, cur, key, base, depth = [], None, None, 0, 0
    for ln in text.splitlines():
        s = ln.strip()
        code = ln.split("#", 1)[0]
        opens = code.count("{") - code.count("}")
        if cur is None:
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", s)
            if (
                m
                and m.group(1) not in ("if", "else", "else_if")
                and not m.group(1).endswith("_decisions")
                and depth <= 1
            ):
                cur, key, base = [ln], m.group(1), depth
                depth += opens
                if depth <= base:
                    out.append(("decision", key, cur))
                    cur, key = None, None
                continue
            depth += opens
            out.append(("other", None, [ln]))
        else:
            cur.append(ln)
            depth += opens
            if depth <= base:
                out.append(("decision", key, cur))
                cur, key = None, None
    if cur is not None:
        out.append(("decision", key, cur))
    return out


def step_filter_decisions() -> None:
    """Vendor vanilla decisions minus tag-specific ones: same-filename
    files win whole, so dropped keys stay dead. Files already curated by
    hand (VANILLA_FORMATION_FILES) are left alone, as are our own
    decisions (non-vanilla names)."""
    tagset = all_known_tags()
    vdir = os.path.join(GAME, "decisions")
    ddir = os.path.join(MOD, "decisions")
    os.makedirs(ddir, exist_ok=True)
    vanilla = {fn for fn in os.listdir(vdir) if fn.endswith(".txt")}
    kept_files, kept_decisions, dropped = 0, 0, []
    for fn in sorted(vanilla):
        if fn in VANILLA_FORMATION_FILES:
            continue
        text = open(os.path.join(vdir, fn), encoding="utf-8",
                    errors="replace").read()
        segs = split_decision_blocks(text)
        body = []
        for kind, key, lines in segs:
            if kind == "decision" and event_mentions_tag("\n".join(lines), tagset):
                dropped.append(f"{fn}:{key}")
                continue
            body.append(lines)
            if kind == "decision":
                kept_decisions += 1
        out = "\n".join("\n".join(ls) for ls in body)
        if not out.endswith("\n"):
            out += "\n"
        dest = os.path.join(ddir, fn)
        old = None
        if os.path.exists(dest):
            old = open(dest, encoding="utf-8", errors="replace").read()
        if old != out:
            write_out(dest, out, encoding="utf-8", errors="strict")
        kept_files += 1
    print(f"decisions: {kept_files} files, {kept_decisions} kept, "
          f"{len(dropped)} tag-specific dropped")


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
        write_out(cfile, country_definition(t))
        print(f"wrote {cfile}")

        if t.flag_source or t.flag_from:
            flag = t.flag_source or os.path.join(GAME, "gfx", "flags", f"{t.flag_from}.tga")
            assert os.path.exists(flag), f"no flag for {t.tag} at {flag}"
            dest = os.path.join(MOD, "gfx", "flags", f"{t.tag}.tga")
            if os.path.exists(dest):
                print(f"kept gfx/flags/{t.tag}.tga (custom, not overwritten)")
            else:
                shutil.copy2(flag, dest)
                print(f"copied gfx/flags/{t.tag}.tga")
        else:
            print(f"no flag for {t.tag} (needs one)")

        if not t.forms:
            print(f"  {t.tag} has no formable tag")
            continue

    by_formable: dict[str, list] = {}
    for t in TAGS:
        if t.forms:
            by_formable.setdefault(t.forms, []).append(t)
    for fcode, starters in sorted(by_formable.items()):
        if fcode == "ROM":
            # Rome restores via decisions/FormROM.txt (handwritten, vanilla
            # behaviour); nothing to generate here.
            continue
        fb = BY_FORMABLE[fcode]
        req = requirement_provinces(fcode)
        txt = formation_decision(fcode, starters)
        os.makedirs(os.path.join(MOD, "decisions"), exist_ok=True)
        p = os.path.join(MOD, "decisions", f"Form{fcode}.txt")
        write_out(p, txt)
        print(f"wrote {p}")
        print(
            f"  formed tag            : {', '.join(s.tag for s in starters)}"
            f" -> {fcode}, rank {fb.rank}"
        )
        print(f"  required provinces    : {len(req)}")
        print(f"  areas covered         : {', '.join(fb.areas) or 'none'}")
        print(
            "  suppressed decisions  : "
            + ", ".join(sorted({k for s in starters for k in s.suppress}))
        )

    # Vanilla formation decisions are neutralized by same-filename dummy
    # files: duplicate keys coexist across files, so stubs in our own files
    # never win. Each dummy carries only the always-no stubs.
    stubbed = sorted({k for t in TAGS if t.forms for k in t.suppress})
    for fn, keys in VANILLA_FORMATION_FILES.items():
        kill = [k for k in keys if k in stubbed]
        if not kill:
            continue
        stubs = "\n".join(
            f"\t{k} = {{\n"
            f"\t\tpotential = {{\n"
            f"\t\t\talways = no\n"
            f"\t\t}}\n"
            f"\t\tallow = {{\n"
            f"\t\t}}\n"
            f"\t\teffect = {{\n"
            f"\t\t}}\n"
            f"\t}}"
            for k in kill
        )
        sp = os.path.join(MOD, "decisions", fn)
        write_out(
            sp,
            f"# dummy: vanilla formations neutralized, use our kar_form_* instead\n"
            f"country_decisions = {{\n{stubs}\n}}\n",
        )
        print(f"wrote {sp} (dummy, neutralized {len(kill)})")

    write_out(reg, "\n".join(reg_lines) + "\n")
    print(f"wrote {reg}")


def step_formation_triggers() -> None:
    specs = [("kar_form_hre", empire_core(), False)]
    done = set()
    for t in TAGS:
        if t.forms and t.forms not in done:
            done.add(t.forms)
            req = requirement_provinces(t.forms)
            specs.append((t.decision, req, BY_FORMABLE[t.forms].home_capital))
    for decision, areas in CUSTOM_TRIGGERS.items():
        req = sorted({int(p) for a in areas for p in _pd()["areas"].get(a, ())})
        specs.append((decision, req, True))

    body = "\n\n".join(
        formation_trigger_block(f"{k}_provinces_trigger", p) for k, p, _ in specs
    )
    if any(cap for _, _, cap in specs):
        body += "\n\n" + "\n\n".join(
            formation_capital_trigger_block(f"{k}_capital_trigger", p)
            for k, p, cap in specs
            if cap
        )
    sdir = os.path.join(MOD, "common", "scripted_triggers")
    os.makedirs(sdir, exist_ok=True)
    spath = os.path.join(sdir, "KarolingianFormations.txt")
    write_out(spath, "# province triggers backing the formation decisions\n" + body + "\n")
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


def strip_non_867(text):
    # Drop every dated block but 867.1.1: no history besides the start date.
    # Top-level fields stay (they describe the start); only dated entries go.
    out, cur, keep, depth = [], None, False, 0
    for ln in text.splitlines():
        s = ln.strip()
        if cur is None:
            m = re.match(r"^(\d+\.\d+\.\d+)\s*=", s)
            if m:
                keep = m.group(1) == CTRY_DATE
                code = ln.split("#", 1)[0]
                depth = code.count("{") - code.count("}")
                cur = [ln] if keep else []
                if depth <= 0:
                    if keep:
                        out.extend(cur)
                    cur = None
                continue
            out.append(ln)
        else:
            if keep:
                cur.append(ln)
            code = ln.split("#", 1)[0]
            depth += code.count("{") - code.count("}")
            if depth <= 0:
                if keep:
                    out.extend(cur)
                cur = None
    return "\n".join(out).strip("\n") + "\n"


_VANILLA_CTRY_FILES: dict = {}


def hist_name(t) -> str:
    # Name our file exactly like vanilla's when one exists for this tag, so
    # the engine skips the vanilla file instead of merging its OTL history
    # (rulers, idea groups, HRE/elector state, dated rank changes) into ours.
    if not _VANILLA_CTRY_FILES:
        for fn in os.listdir(VANILLA_CDIR):
            if fn.endswith(".txt"):
                _VANILLA_CTRY_FILES.setdefault(fn.split(" - ")[0], fn)
    hit = _VANILLA_CTRY_FILES.get(t.tag)
    if hit:
        return hit
    base = t.country_file or t.tag
    if base.endswith(".txt"):
        base = base[:-4]
    return f"{t.tag} - {base}.txt"


def step_countries():
    os.makedirs(COUNTRY_OUT, exist_ok=True)
    for t in TAGS:
        text = ck3_sync(t.tag, country_history(t))
        text = strip_non_867(text)
        name = hist_name(t)
        write_out(os.path.join(COUNTRY_OUT, name), text)
        stale = os.path.join(COUNTRY_OUT, f"{t.tag}.txt")
        if stale != os.path.join(COUNTRY_OUT, name) and os.path.exists(stale):
            os.remove(stale)
        print(f"wrote {name} (rank {t.rank}, capital {t.capital})")
    # HLR is formed in-game by kar_form_hre; neutralize vanilla's OTL file
    # (rank 3, Vienna capital, austrian/catholic defaults) so it never applies.
    # A comment alone does not register as a history file, so carry the same
    # neutral defaults the formation produces anyway (history is not
    # re-applied on change_tag).
    write_out(
        os.path.join(COUNTRY_OUT, "HLR - Holy Roman Empire.txt"),
        "# formed in-game by kar_form_hre; vanilla OTL history neutralized\n"
        "government = monarchy\n"
        "technology_group = western\n",
    )
    print("wrote HLR - Holy Roman Empire.txt (neutralized)")


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


@lru_cache(maxsize=None)
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
        scalars, cores, _ = parse(path)

        def tok(key, cls):
            # First token in the old character class only: vanilla parks
            # two keys on one line (culture = ge discovered_by = ...) and
            # quotes some values (religion = "hinduism") - neither counted.
            v = scalars.get(key)
            if not v:
                return None
            first = v.split()[0]
            return first if re.fullmatch(cls, first) else None

        provs[pid] = {
            "id": pid,
            "name": pname,
            "file": fn,
            "cores": [
                c.split()[0]
                for c in cores
                if re.fullmatch(r"[A-Z0-9_]+", c.split()[0])
            ],
            "owner": tok("owner", r"[A-Z0-9_]+"),
            "controller": tok("controller", r"[A-Z0-9_]+"),
            "culture": tok("culture", r"[a-z0-9_]+"),
            "religion": tok("religion", r"[a-z0-9_]+"),
            "capital": "capital" in scalars,
            "is_city": scalars.get("is_city") == "yes",
            "sea": False,
        }
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
        f"provinces checked against the {CTRY_DATE} start: {len(expected)}"
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
