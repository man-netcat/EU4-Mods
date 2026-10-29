#!/usr/bin/env python3
"""Province history: ownership at the start, wasteland, the New World, cores, forts and untouched neighbours."""

import os
import re
from checks.report import note
from checks.context import CAPS, DORMANT, GAME, HERE, KEPT_REALMS, PDIR, PROVINCES, TAGS, parse, province_files
from steps.allocation import build
from steps.provdata import lake_ids, sea_ids, vanilla_prov_file, vanilla_prov_ids, waste_ids


def province_ownership() -> None:
    """Province ownership."""
    files = province_files()

    print("\n== province ownership ==")
    note(
        len(files) == len(os.listdir(PDIR)),
        f"no duplicate province files ({len(files)} unique)",
    )


def no_province_is_in_vanilla_hre() -> None:
    """No province is in the vanilla HRE."""
    files = province_files()

    print("\n== no province is in the vanilla HRE ==")
    # 867 knows no Holy Roman Empire: vanilla heads ship `hre = yes` on the
    # whole former empire's land, and one leaking line puts a whole realm
    # (whatever sits on that capital) inside the vanilla HRE.
    hre_dirty = []
    for fn in sorted(os.listdir(PDIR)):
        if fn.endswith(".txt") and re.search(
            r"^hre\s*=\s*yes",
            open(os.path.join(PDIR, fn), encoding="utf-8", errors="replace").read(),
            re.M,
        ):
            hre_dirty.append(fn)
    note(not hre_dirty, f"no hre = yes in {len(files)} province files ({len(hre_dirty)} dirty)")
    for b in hre_dirty[:10]:
        print("        " + b)

    for label, ids in (("wasteland", waste_ids()), ("lake", lake_ids())):
        wfiles = [p for p in ids if vanilla_prov_file(p)]
        wmiss = sorted(p for p in wfiles if p not in files)
        note(not wmiss, f"every vanilla {label} province has a file ({len(wmiss)} missing)")
        for b in wmiss[:8]:
            print("        " + str(b))
        wowned = sorted(
            p for p in wfiles if p in files and parse(files[p])[0].get("owner") is not None
        )
        note(not wowned, f"no owner on {label} provinces ({len(wowned)} problems)")
        for b in wowned[:8]:
            print("        " + str(b))


def unownable_land_is_unowned_in_database() -> None:
    """Unownable land is unowned in the database."""
    print("\n== unownable land is unowned in the database ==")
    # The database is the source of truth: catch a grey/water claim in a
    # tag row before any file is generated. The build asserts the merged
    # output; this checks the claims themselves - wastelands, lakes and
    # sea tiles alike can have no landlord.
    unownable = set(waste_ids()) | set(lake_ids()) | set(sea_ids())
    claimed = sorted(
        {p for _tag, ps in build().items() for p in ps if p in unownable}
    )
    note(
        not claimed,
        f"no database tag claims grey or water ({len(claimed)} problems)",
    )
    for b in claimed[:8]:
        print("        " + str(b))


def the_new_world_and_australia_stay_uncolonised() -> None:
    """The New World and Australia stay uncolonised."""
    files = province_files()

    print("\n== the New World and Australia stay uncolonised ==")
    # Unsupported by this mod: every land province of the American
    # superregions and of Australia must stay empty - no owner, controller,
    # core, population or database row, and no tag sitting there.
    def _block(text, name):
        m = re.search(r"(?m)^" + re.escape(name) + r"\s*=\s*\{", text)
        if not m:
            return ""
        depth, k = 0, text.index("{", m.start())
        for i in range(k, len(text)):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            if depth == 0:
                return text[k + 1:i]
        return ""

    _map = lambda f: open(os.path.join(GAME, "map", f), encoding="utf-8", errors="replace").read()
    _sup, _reg, _area = _map("superregion.txt"), _map("region.txt"), _map("area.txt")
    _regions = {"australia_region"}
    for sr in ("north_america_superregion", "south_america_superregion", "andes_superregion",
               "central_america_superregion", "new_world_superregion"):
        _regions |= set(re.findall(r"(\w+_region)\b", _block(_sup, sr)))
    _newworld = set()
    for rg in _regions:
        for ar in re.findall(r"(\w+_area)\b", _block(_reg, rg)):
            _newworld |= {int(x) for x in re.findall(r"\b(\d+)\b",
                          re.sub(r"color\s*=\s*\{[^}]*\}", "", re.sub(r"#[^\n]*", "", _block(_area, ar))))}
    _newworld -= set(sea_ids()) | set(lake_ids())
    note(len(_newworld) > 500, f"{len(_newworld)} New World and Australian provinces identified")
    _owned = sorted({p for _t, ps in build().items() for p in ps if p in _newworld})
    note(not _owned, f"no tag owns New World or Australian land ({len(_owned)} problems)")
    for b in _owned[:8]:
        print("        " + str(b))
    import sqlite3 as _sq
    _db = _sq.connect(str(HERE / "tags.db"))
    _rows = sorted(r[0] for r in _db.execute("select pid from provinces") if r[0] in _newworld)
    _caps = sorted(r[0] for r in _db.execute("select tag from tags where capital in (%s)" % ",".join(map(str, _newworld))))
    _db.close()
    note(not _rows, f"no database province row in the New World or Australia ({len(_rows)} problems)")
    for b in _rows[:8]:
        print("        " + str(b))
    note(not _caps, f"no tag has a New World or Australian capital ({len(_caps)} problems)")
    _dirty = []
    for p in sorted(_newworld):
        if p not in files:
            continue
        sc, c0, ca = parse(files[p])
        if c0 or ca or any(k in sc for k in ("owner", "controller", "culture", "religion",
                                              "base_tax", "base_production", "base_manpower")):
            _dirty.append(p)
    note(not _dirty, f"New World and Australian province files carry no owner, core or population ({len(_dirty)} problems)")
    for b in _dirty[:8]:
        print("        " + str(b))

    vmiss = sorted(p for p in vanilla_prov_ids() if p not in files)
    note(not vmiss, f"every vanilla province has a file ({len(vmiss)} missing)")
    for b in vmiss[:8]:
        print("        " + str(b))
    seaset = set(sea_ids())  # sea tiles stay undated, tags and all
    vtags = sorted(
        p
        for p in files
        if p not in seaset
        and re.search(
            r"(?m)^\s*discovered_by\s*=\s*([A-Z]{3})\s*$",
            open(files[p], encoding="utf-8", errors="surrogateescape").read(),
        )
    )
    note(not vtags, f"no tag-specific discovery on land ({len(vtags)} problems)")
    for b in vtags[:8]:
        print("        " + str(b))


def capitals_inside_own_realm() -> None:
    """Capitals inside own realm."""
    files = province_files()

    print("\n== capitals inside own realm ==")
    for t in TAGS:
        if t in DORMANT:
            continue
        s, _, _ = parse(files[CAPS[t]])
        note(
            s.get("owner") == t,
            f"{t} capital {CAPS[t]} ({s.get('capital')}) owned by {s.get('owner')}",
        )


def new_core_on_owned_province() -> None:
    """New core on every owned province."""
    files = province_files()

    print("\n== new core on every owned province ==")
    for t in TAGS:
        owned = [pid for pid, p in files.items() if parse(p)[0].get("owner") == t]
        missing = [pid for pid in owned if t not in parse(files[pid])[1]]
        note(
            not missing, f"{t}: core on all {len(owned)} owned ({len(missing)} missing)"
        )

    print()


def no_dead_cores() -> None:
    files = province_files()

    print('== no dead cores ==')
    alive = KEPT_REALMS | {'HLR'}
    dead = []
    for pid, path in files.items():
        for c in parse(path)[1]:
            if c not in alive:
                dead.append(f'{pid}: core for {c}')
    note(not dead, f'every core belongs to a living tag ({len(dead)} dead)')
    for d in dead[:10]:
        print('        ' + d)


def forts_only_where_database_says_so() -> None:
    files = province_files()

    print('\n== forts only where the database says so ==')
    kept = {pid for pid, p in PROVINCES.items() if p.fort}
    fort_bad = []
    for pid, path in files.items():
        text = open(path, encoding="utf-8", errors="surrogateescape").read()
        has = bool(re.search(r"(?m)^\s*fort_15th\s*=", text))
        if pid in kept and not has:
            fort_bad.append(f"{pid}: keep-flagged but unfortified")
        elif pid not in kept and has:
            fort_bad.append(f"{pid}: fortified without a flag")
    note(not fort_bad, f"forts match the database ({len(fort_bad)} bad)")
    for b in fort_bad[:10]:
        print('        ' + b)


def untouched_neighbours_intact() -> None:
    """Untouched neighbours intact."""
    files = province_files()

    print("\n== untouched neighbours intact ==")

    reassigned = {pid for pid, p in files.items() if parse(p)[0].get("owner") in TAGS}
    for t in [
        "SARD",
        "SWE",
        "NOR",
        "ENG",
        "CAS",
        "POR",
        "MKL",
        "POM",
    ]:
        owned = [pid for pid in reassigned if parse(files[pid])[0].get("owner") == t]
        note(not owned, f"{t} owns none of the {len(reassigned)} reassigned provinces")


def run() -> None:
    province_ownership()
    no_province_is_in_vanilla_hre()
    unownable_land_is_unowned_in_database()
    the_new_world_and_australia_stay_uncolonised()
    capitals_inside_own_realm()
    new_core_on_owned_province()
    no_dead_cores()
    forts_only_where_database_says_so()
    untouched_neighbours_intact()
