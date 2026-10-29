#!/usr/bin/env python3
"""Cultures: group depth, tech-group visibility, and the title ladders tags reach."""

import os
import re
from checks.report import note
from checks.context import GAME, MOD, PDIR
from tagdb import TAGS as _tagrows


def culture_blocks_sit_at_group_depth() -> None:
    """Culture blocks sit at group depth."""
    print("\n== culture blocks sit at group depth ==")
    # A culture block nested inside another culture silently does nothing
    # in game (the carantanian bug): the engine reads cultures only at
    # group depth. Every culture the mod actually uses must own exactly
    # one depth-1 block. Same-name groups and cultures (frankish,
    # maghrebi) are the mod's own split-group pattern and are fine.
    from db import session as db_session
    from models import Culture as DbCulture

    _s2 = db_session()
    # every row keyed on a culture column, in any table
    used_cultures = set()
    for _tbl in [
        r[0]
        for r in _s2.execute(
            __import__("sqlalchemy").text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        )
    ]:
        _tabs = [
            r[1]
            for r in _s2.execute(
                __import__("sqlalchemy").text(f"PRAGMA table_info({_tbl})")
            )
        ]
        if "culture" in _tabs:
            used_cultures |= {
                c  # formables.culture may list several cultures
                for r in _s2.execute(
                    __import__("sqlalchemy").text(
                        f"SELECT DISTINCT culture FROM {_tbl} WHERE culture IS NOT NULL"
                    )
                )
                for c in r[0].split()
            }
    _s2.close()
    for fn in sorted(os.listdir(PDIR)):
        if fn.endswith(".txt"):
            for c in re.findall(
                r"(?m)^\s*culture\s*=\s*([a-z_0-9]+)",
                open(os.path.join(PDIR, fn), encoding="utf-8", errors="replace").read(),
            ):
                used_cultures.add(c)
    cpath = os.path.join(MOD, "common", "cultures", "00_cultures.txt")
    openers = []  # (key, depth) for every block opener, comments stripped
    _depth = 0
    for ln in open(cpath, encoding="utf-8", errors="replace").read().splitlines():
        code = ln.split("#", 1)[0]
        m = re.match(r"\s*([A-Za-z_0-9]+)\s*=\s*\{", code)
        if m:
            openers.append((m.group(1), _depth))
        _depth += code.count("{") - code.count("}")
    # name lists and vanilla's country/province interaction blocks are
    # fields, never cultures
    FIELD_BLOCKS = frozenset(
        {"male_names", "female_names", "dynasty_names", "unit_names", "ship_names",
         "army_names", "fleet_names", "names_from_culture", "country", "province"}
    )
    bad_cult = [f"{k} nests at depth {d}" for k, d in openers
                if k not in FIELD_BLOCKS and d >= 2]
    for k in sorted(used_cultures):
        ds = [d for key, d in openers if key == k and d >= 1]
        if ds.count(1) != 1:
            bad_cult.append(
                f"{k} appears {len(ds)}x as a culture block (need exactly one depth-1 block)"
            )
    note(
        not bad_cult,
        f"all {len(used_cultures)} used cultures own exactly one depth-1 block"
        + ("" if not bad_cult else f" ({len(bad_cult)} bad)"),
    )
    for b in bad_cult[:12]:
        print("        " + b)


def vanilla_tech_group_visibility_survives_everywher() -> None:
    """Vanilla tech-group visibility survives everywhere."""
    print("\n== vanilla tech-group visibility survives everywhere ==")
    from steps.provinces import undated_group_visibility

    vis_bad = []
    for fn in sorted(os.listdir(PDIR)):
        if not fn.endswith(".txt"):
            continue
        m = re.match(r"^(\d+)", fn)
        if not m:
            continue
        ours = {
            ln.strip()
            for ln in open(
                os.path.join(PDIR, fn), encoding="utf-8", errors="surrogateescape"
            )
            if ln.strip().startswith("discovered_by")
        }
        for vfn in os.listdir(os.path.join(GAME, "history", "provinces")):
            if vfn == fn:
                want = undated_group_visibility(
                    open(
                        os.path.join(GAME, "history", "provinces", vfn),
                        encoding="utf-8",
                        errors="replace",
                    ).read()
                )
                missing = [ln for ln in want if ln.strip() not in ours]
                if missing:
                    vis_bad.append(f"{m.group(1)} drops {len(missing)}")
                break
    note(not vis_bad, f"no dropped tech-group discovery ({len(vis_bad)} bad)")
    for b in vis_bad[:8]:
        print("        " + b)


def tags_reach_their_culture_s_title_ladder() -> None:
    """Tags reach their culture's title ladder (tools/govnames.py)."""
    print("\n== tags reach their culture's title ladder (tools/govnames.py) ==")
    import govnames

    gn_miss = govnames.misses([(t.tag, t.culture) for t in _tagrows])
    note(not gn_miss, f"every tag passes the gate of its culture's government_names block ({len(gn_miss)} fall through)")
    for t, c, b in gn_miss[:20]:
        print(f"        {t}: culture {c} has a dedicated block but the tag lands on {b} "
              f"(run tools/culturetitles.py {t} to add a block gated on its government)")

    import culturalnames
    import tagloc

    tl_drift = tagloc.drift()
    note(not tl_drift, f"every tag's name and adjective is what tools/tagloc.py lifts from CK3 ({len(tl_drift)} stale - run the build)")
    for t, have, want in tl_drift[:20]:
        print(f"        {t}: {have} but CK3 gives {want}")

    ppl = culturalnames.people_drift([(t.tag, t.ck3_title, t.rank) for t in _tagrows if t.ck3_title])
    note(not ppl, f"steppe counties carry their people's name ({len(ppl)} missing)")
    for tg_, have, want in ppl[:20]:
        print(f"        {tg_}: {have!r} should be {want!r} (python3 tools/culturalnames.py peoples)")


def run() -> None:
    culture_blocks_sit_at_group_depth()
    vanilla_tech_group_visibility_survives_everywher()
    tags_reach_their_culture_s_title_ladder()
