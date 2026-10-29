#!/usr/bin/env python3
"""Province history files: tidy the vanilla files and write the owner, controller, cores, forts and claims."""

import os
import re
import shutil
from db import core_deny_map
from tagdb import CTRY_DATE, PROVINCES, SEED_CORES, TAGS
from steps.allocation import CLAIM_RULES, HUN_AREAS, apply_db_culture_religion, build
from steps.layout import PROV_OUT, VANILLA_PDIR
from steps.output import write_out
from steps.parsing import strip_dated
from steps.provdata import _VANILLA_PROV_FILES, _pd, lake_ids, sea_ids, vanilla_prov_file, vanilla_prov_ids, waste_ids


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

        # 867 knows no Holy Roman Empire: never let vanilla membership leak
        # (hre = no heads stay verbatim; only membership lines are dropped)
        if re.match(r"^hre\s*=\s*yes", s):
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
