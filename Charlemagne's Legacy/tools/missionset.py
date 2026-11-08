#!/usr/bin/env python3
"""Work with the mission trees without opening the data files.

    python3 tools/missionset.py which TAG [TAG ...]    # what the mission screen shows a realm: the grid, column by column
    python3 tools/missionset.py list                   # every series (generated and hand-written) with its realm, column, size
    python3 tools/missionset.py lint                   # the data checks the build runs (exit 1 on a problem)
    python3 tools/missionset.py owned TAG              # the provinces a realm holds at the start, by area, with their names
    python3 tools/missionset.py area NAME [NAME ...]   # an area's provinces with their names and who holds them at the start
    python3 tools/missionset.py region NAME            # a region's areas with the realms that hold them at the start
    python3 tools/missionset.py dev TAG [TAG ...]      # a realm's number of provinces and development at the start (subjects included)
    python3 tools/missionset.py icons                  # the mission icons a mission may use
    python3 tools/missionset.py new SLUG --slot N --tags A,B [--file 10_x.missions]   # append an empty series to fill in

Needs EU4_GAME and CK3_GAME like the build, and a built mod (province history) for the owners."""
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from steps import missions as M  # noqa: E402
from steps import provdata  # noqa: E402

MOD = M.MOD


def owners_and_names():
    """({province: who it counts for}, {province: name}); a province of a vassal or theme counts for its liege."""
    lieges = M.liege_map()
    owners, names = {}, {}
    folder = os.path.join(MOD, "history", "provinces")
    for fn in os.listdir(folder):
        m = re.match(r"^(\d+)\s*-\s*(.+)\.txt$", fn)
        if not m:
            continue
        head = re.split(r"(?m)^\d+\.\d+\.\d+", open(os.path.join(folder, fn), encoding="cp1252", errors="replace").read(), maxsplit=1)[0]
        o = re.search(r"(?m)^owner\s*=\s*([A-Z0-9]{3})", head)
        names[int(m.group(1))] = m.group(2)
        if o:
            owners[int(m.group(1))] = M.holder_of(o.group(1), lieges)
    return owners, names


def grid(tag):
    scripts = M.load_scripts()
    cells, series = {}, [s for s in scripts.values() if tag in s["tags"]]
    for s in series:
        for mid, m in s["missions"].items():
            cells[(s["slot"], m["row"])] = mid.replace("kar_", "", 1)
    if not series:
        print(f"{tag}: no mission series")
        return
    rows = max(r for _c, r in cells)
    print(f"{tag}: {len(series)} series " + ", ".join(f"{s['key']} (column {s['slot']}, {len(s['missions'])} missions)" for s in series))
    width = 22
    print("      " + "".join(f"{'column ' + str(c):<{width}}" for c in M.SLOTS))
    for r in range(1, rows + 1):
        print(f"row {r:<2}" + "".join(f"{cells.get((c, r), '.')[:width - 2]:<{width}}" for c in M.SLOTS))
    print("arrows:")
    place = {mid: (s["slot"], m["row"]) for s in series for mid, m in s["missions"].items()}
    for s in series:
        for mid, m in s["missions"].items():
            for need in m["needs"]:
                pc, pr = place.get(need, (None, None))
                kind = "missing" if pc is None else ("down" if pc == s["slot"] and pr == m["row"] - 1 else
                                                     "skip tier" if pc == s["slot"] else "branch" if abs(pc - s["slot"]) == 1 and pr == m["row"] - 1 else
                                                     "branch+skip" if abs(pc - s["slot"]) == 1 else "skip slot")
                print(f"   {need.replace('kar_', '', 1)} -> {mid.replace('kar_', '', 1)}  ({kind})")


def main(argv):
    if not argv:
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "which" and rest:
        for tag in rest:
            grid(tag)
    elif cmd == "list":
        for s in sorted(M.load_scripts().values(), key=lambda s: (s["file"], s["slot"] or 0)):
            print(f"{s['key']:<40} column {s['slot']}  {len(s['missions'])} missions  {','.join(s['tags']):<14} {s['file']}")
    elif cmd == "lint":
        series, problems = M.parse()
        problems += M.check_data(series)
        if not problems:
            problems += M.check_flow(series)
        print("\n".join(problems) or f"{len(series)} series, no problems")
        return 1 if problems else 0
    elif cmd == "owned" and rest:
        owners, names = owners_and_names()
        areas = provdata.load_areas()
        mine = {p for p, o in owners.items() if o == rest[0]}
        for a, ids in sorted(areas.items()):
            have = [p for p in ids if p in mine]
            if have:
                print(f"{a}: " + ", ".join(f"{p} {names.get(p, '?')}" for p in have) + ("" if len(have) == len(ids) else f"   ({len(have)}/{len(ids)})"))
    elif cmd == "area" and rest:
        owners, names = owners_and_names()
        areas = provdata.load_areas()
        for a in rest:
            print(f"{a}:" + ("" if a in areas else "  no such area"))
            for p in areas.get(a, []):
                print(f"   {p:>5} {names.get(p, '?'):<24} {owners.get(p, '-')}")
    elif cmd == "region" and rest:
        owners, _names = owners_and_names()
        areas = provdata.load_areas()
        reg = provdata.load_region_areas().get(rest[0])
        if reg is None:
            print("no such region")
            return 1
        for a in reg:
            held = collections.Counter(owners.get(p, "-") for p in areas.get(a, []))
            print(f"{a:<34} {len(areas.get(a, [])):>2} provinces  " + ", ".join(f"{t} {n}" for t, n in held.most_common(4)))
    elif cmd == "dev" and rest:
        owners, _names = owners_and_names()
        folder = os.path.join(MOD, "history", "provinces")
        total = collections.Counter()
        count = collections.Counter()
        for fn in os.listdir(folder):
            m = re.match(r"^(\d+)\s*-", fn)
            if not m or int(m.group(1)) not in owners:
                continue
            head = re.split(r"(?m)^\d+\.\d+\.\d+", open(os.path.join(folder, fn), encoding="cp1252", errors="replace").read(), maxsplit=1)[0]
            dev = sum(int(x) for x in re.findall(r"(?m)^base_(?:tax|production|manpower)\s*=\s*(\d+)", head))
            total[owners[int(m.group(1))]] += dev
            count[owners[int(m.group(1))]] += 1
        for tag in rest:
            print(f"{tag}: {count[tag]} provinces, development {total[tag]} (its subjects' lands included)")
    elif cmd == "icons":
        print("\n".join(sorted(M.base_icons())))
    elif cmd == "new" and rest:
        slug = rest[0]
        opts = dict(zip(rest[1::2], rest[2::2]))
        if "--slot" not in opts or "--tags" not in opts:
            print("new SLUG needs --slot and --tags")
            return 2
        fn = opts.get("--file", "90_new.missions")
        block = (f"\n[{slug}]\nslot = {opts['--slot']}\ntags = {opts['--tags']}\nshield = yes\n"
                 + "".join(f"\nmission = m{i} | TODO | TODO\nrow = {i}\nneeds = {'m' + str(i - 1) if i > 1 else ''}\nicon = TODO\nwhen = TODO\nreward = TODO\n"
                           for i in range(1, 4)))
        with open(os.path.join(M.DATA, fn), "a", encoding="utf-8") as fh:
            fh.write(block)
        print(f"appended [{slug}] to tools/data/missions/{fn}; fill it in, then `missionset.py lint`")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
