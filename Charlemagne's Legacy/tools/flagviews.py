#!/usr/bin/env python3
"""Browsable copies of the mod's flags: one folder per geographical region, each flag a symlink to gfx/flags/<TAG>.tga.

    python3 tools/flagviews.py [OUT]       # default OUT: /home/rick/Paradox/flag-views

A flag's region is the EU4 region of its tag's capital (a formable's own or home capital). Layout:
OUT/<group>/<region>/<TAG> <name>.tga, e.g. "Europe/British Isles/ENG England.tga". The mod is never touched; the script only
creates or removes symlinks (and the folders around them) under OUT, so run it again after the flags change.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import development as dev  # noqa: E402
from paths import EU4_GAME  # noqa: E402
from steps.layout import MOD  # noqa: E402
from tagdb import BY_TAG, FORMABLES  # noqa: E402

GROUP_NAMES = {"europe": "Europe", "anatolia": "Anatolia and Caucasus", "middle_east": "Middle East and North Africa",
               "steppe": "Steppe and Siberia", "india": "India", "east_asia": "East Asia", "southeast_asia": "Southeast Asia",
               "africa": "Africa"}
DEFAULT_OUT = "/home/rick/Paradox/flag-views"
OVERRIDE = {"HLR": "south_german_region"}  # the Karolingian Empire's title has no province of its own to read


def region_names():
    """{EU4 province id: region key} from the base game's areas and regions (region.txt's own names)."""
    areas = {}
    for name, body in dev._blocks(dev._strip(open(os.path.join(EU4_GAME, "map", "area.txt"), encoding="latin-1").read())):
        areas[name] = [int(x) for x in re.findall(r"\b\d+\b", re.sub(r"color\s*=\s*\{[^}]*\}", "", body))]
    out = {}
    for name, body in dev._blocks(dev._strip(open(os.path.join(EU4_GAME, "map", "region.txt"), encoding="latin-1").read())):
        m = re.search(r"areas = \{(.*?)\}", body, re.S)
        for a in (m.group(1).split() if m else []):
            for p in areas.get(a, []):
                out[p] = name
    return out


def pretty(region):
    return re.sub(r"_region$", "", region).replace("_", " ").title()


def area_provinces():
    out = {}
    for name, body in dev._blocks(dev._strip(open(os.path.join(EU4_GAME, "map", "area.txt"), encoding="latin-1").read())):
        out[name] = [int(x) for x in re.findall(r"\b\d+\b", re.sub(r"color\s*=\s*\{[^}]*\}", "", body))]
    return out


def names():
    """{tag: display name} from the mod's own country localisation (tag names lifted from CK3)."""
    out = {}
    root = os.path.join(MOD, "localisation")
    for dp, _d, fns in os.walk(root):
        for fn in fns:
            if fn.endswith("_l_english.yml"):
                for m in re.finditer(r'(?m)^ ([A-Z]{3}):\d*\s+"(.*)"', open(os.path.join(dp, fn), encoding="utf-8-sig", errors="replace").read()):
                    out.setdefault(m.group(1), m.group(2))
    for f in FORMABLES:  # formables may have no tag name of their own in the country localisation
        out.setdefault(f.tag, f.name)
    for t, r in BY_TAG.items():
        out.setdefault(t, r.name)
    return out


def provinces_of(tag, areas):
    """The provinces to read a tag's region from: its capital first, then what it owns or (a formable) lists."""
    ps = []
    if tag in BY_TAG and BY_TAG[tag].capital:
        ps.append(BY_TAG[tag].capital)
    import sqlite3
    con = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tags.db"))
    ps += [p for (p,) in con.execute("select pid from tag_provinces where tag=? union select pid from seed_cores where tag=?", (tag, tag))]
    con.close()
    for f in FORMABLES:
        if f.tag == tag:
            ps += [x for x in (f.capital, f.home_capital) if x]
            ps += list(f.provinces or [])
            for ar in f.areas or []:
                ps += areas.get(ar, []) or areas.get(ar + "_area", [])
    return ps


def main(out_dir=DEFAULT_OUT):
    flags = os.path.join(MOD, "gfx", "flags")
    region_of = region_names()
    areas = area_provinces()
    label_of = names()
    if os.path.isdir(out_dir):  # only symlinks (and emptied folders) are ever removed
        for root, dirs, files in os.walk(out_dir, topdown=False):
            for fn in files:
                path = os.path.join(root, fn)
                if os.path.islink(path):
                    os.unlink(path)
            if root != out_dir and not os.listdir(root):
                os.rmdir(root)
    n, per = 0, {}
    for fn in sorted(os.listdir(flags)):
        if not fn.lower().endswith(".tga"):
            continue
        tag = fn[:-4]
        name = label_of.get(tag, "")
        regs = [region_of[p] for p in provinces_of(tag, areas) if p in region_of]
        reg = OVERRIDE.get(tag) or (regs[0] if regs else None)  # the capital's region when it has one
        group = GROUP_NAMES.get(dev.GROUP.get(reg), "Other") if reg else "Other"
        folder = os.path.join(out_dir, group, pretty(reg) if reg else ("Not used by any tag" if tag not in label_of and tag not in BY_TAG else "Unsorted"))
        os.makedirs(folder, exist_ok=True)
        label = re.sub(r'[\\/:*?"<>|]', "", f"{tag} {name}".strip())
        os.symlink(os.path.join(flags, fn), os.path.join(folder, label + ".tga"))
        per[(group, pretty(reg) if reg else ("Not used by any tag" if tag not in label_of and tag not in BY_TAG else "Unsorted"))] = per.get((group, pretty(reg) if reg else ("Not used by any tag" if tag not in label_of and tag not in BY_TAG else "Unsorted")), 0) + 1
        n += 1
    print(f"{n} flags in {len(per)} folders under {out_dir}")
    for (g, r), c in sorted(per.items()):
        print(f"  {g} / {r}: {c}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
