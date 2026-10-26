#!/usr/bin/env python3
"""Move a tag onto the vanilla EU4 tag it stands for (BEL -> BNG, Bengal).

    python3 tools/retag.py OLD NEW [OLD NEW ...]

NEW must be a base-game tag the mod does not use yet; OLD a tags.db tag. Every
table that names the tag, the localisation pair, the tag-gated title blocks and
the VANILLA_REUSE guard in validate.py follow, and the tag takes over the base
game's country file name (the build then replaces the vanilla definition and
history under their own file names).
"""
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
MOD = os.path.join(HERE, "..")
LOC = os.path.join(MOD, "localisation", "replace", "countries_l_english.yml")
ZZ = os.path.join(MOD, "common", "government_names", "zz_kar_government_names.txt")
VALIDATE = os.path.join(HERE, "validate.py")

TABLES = [("tags", "tag"), ("tag_areas", "tag"), ("tag_provinces", "tag"), ("tag_reforms", "tag"),
          ("tag_suppress", "tag"), ("diplomacy", "liege"), ("diplomacy", "subject"),
          ("formables", "tag"), ("formable_renames", "tag"), ("core_deny", "holder"),
          ("core_deny", "owner"), ("rivalries", "tag"), ("friendships", "tag"),
          ("wars", "goal_tag"), ("war_sides", "tag"), ("seed_cores", "tag")]


def retag(con, old, new, vfiles):
    if con.execute("select 1 from tags where tag=?", (new,)).fetchone():
        sys.exit(f"{new} is already a tag in tags.db")
    if not con.execute("select 1 from tags where tag=?", (old,)).fetchone():
        sys.exit(f"{old} is no tag in tags.db")
    if new not in vfiles:
        sys.exit(f"{new} is no base-game tag")
    for table, col in TABLES:
        con.execute(f"update {table} set {col}=? where {col}=?", (new, old))
    con.execute("update tags set country_file=? where tag=?", (vfiles[new], new))
    loc = open(LOC, encoding="utf-8-sig").read()
    for suffix in ("", "_ADJ"):
        loc, n = re.subn(rf"(?m)^ {old}{suffix}:", f" {new}{suffix}:", loc)
        if suffix == "" and n != 1:
            sys.exit(f"{old}: no loc line")
    open(LOC, "w", encoding="utf-8-sig", newline="").write(loc)
    zz = open(ZZ, encoding="cp1252", newline="").read()
    zz = re.sub(rf"(\btag = ){old}\b", rf"\g<1>{new}", zz)
    open(ZZ, "w", encoding="cp1252", newline="").write(zz)
    flag = os.path.join(MOD, "gfx", "flags", f"{old}.tga")
    if os.path.exists(flag):
        sys.exit(f"{old} has a flag ({flag}): rename it by hand, flags are yours")
    v = open(VALIDATE, encoding="utf-8").read()
    # append to the reuse list: the last string of the frozenset
    i = v.index("VANILLA_REUSE = frozenset(")
    j = v.index('.split()', i)
    k = v.rindex('"', i, j)
    v = v[:k] + f" {new}" + v[k:]
    open(VALIDATE, "w", encoding="utf-8", newline="").write(v)
    print(f"  {old} -> {new} ({vfiles[new]})")


if __name__ == "__main__":
    import eu4

    args = sys.argv[1:]
    if not args or len(args) % 2:
        sys.exit(__doc__)
    vfiles = {t: fn for t, (fn, _x) in eu4.load_vanilla_countries().items()}
    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    for old, new in zip(args[::2], args[1::2]):
        retag(con, old, new, vfiles)
    con.commit()
