#!/usr/bin/env python3
"""Move a tag onto another code: the vanilla EU4 tag it stands for (BEL -> BNG, Bengal) or any free code (PMS -> BHM).

    python3 tools/retag.py OLD NEW [OLD NEW ...]

NEW must be a code the mod does not use yet (a base-game tag, or a code no base-game tag has; a base-game tag is
reused deliberately, anything else is a plain rename); OLD a tags.db tag. Every
table that names the tag, the localisation pair, the tag-gated title blocks and
the VANILLA_REUSE guard in checks/tags.py follow (a flag file is renamed, never
overwritten), and the tag takes over the base
game's country file name (the build then replaces the vanilla definition and
history under their own file names).
"""
import glob
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
MOD = os.path.join(HERE, "..")
LOC = os.path.join(MOD, "localisation", "replace", "countries_l_english.yml")
ZZ = os.path.join(MOD, "common", "government_names", "zz_kar_government_names.txt")
VALIDATE = os.path.join(HERE, "checks", "tags.py")

TABLES = [("tags", "tag"), ("tag_areas", "tag"), ("tag_provinces", "tag"), ("tag_reforms", "tag"),
          ("tag_suppress", "tag"), ("diplomacy", "liege"), ("diplomacy", "subject"),
          ("formables", "tag"), ("formable_renames", "tag"), ("core_deny", "holder"),
          ("core_deny", "owner"), ("rivalries", "tag"), ("friendships", "tag"),
          ("wars", "goal_tag"), ("war_sides", "tag"), ("seed_cores", "tag"), ("releasables", "tag")]


def retag(con, old, new, vfiles):
    if con.execute("select 1 from tags where tag=?", (new,)).fetchone():
        sys.exit(f"{new} is already a tag in tags.db")
    if not con.execute("select 1 from tags where tag=?", (old,)).fetchone():
        sys.exit(f"{old} is no tag in tags.db")
    if not re.fullmatch(r"[A-Z]{3}", new):
        sys.exit(f"{new} is no tag code")
    custom = new not in vfiles
    if custom:
        if new in vanilla_codes():
            sys.exit(f"{new} is a base-game tag with no country file here: refusing")
        vfiles = {**vfiles, new: con.execute("select country_file from tags where tag=?", (old,)).fetchone()[0]}
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
        target = os.path.join(MOD, "gfx", "flags", f"{new}.tga")
        if os.path.exists(target):
            sys.exit(f"{new}.tga exists already: not overwriting a flag")
        os.rename(flag, target)  # the flag moves with its tag, unchanged
        print(f"  flag {old}.tga -> {new}.tga")
    hist = []
    if not custom:
        v = open(VALIDATE, encoding="utf-8").read()
        # append to the reuse list: the last string of the frozenset
        i = v.index("VANILLA_REUSE = frozenset(")
        j = v.index('.split()', i)
        k = v.rindex('"', i, j)
        v = v[:k] + f" {new}" + v[k:]
        open(VALIDATE, "w", encoding="utf-8", newline="").write(v)
        # reused tags carry the base game's technology group
        hist = glob.glob(os.path.join(os.environ.get("EU4_GAME") or "", "history", "countries", f"{new} - *.txt"))
    if hist:
        m = re.search(r"(?m)^technology_group\s*=\s*(\w+)", open(hist[0], encoding="cp1252", errors="replace").read())
        if m:
            con.execute("update tags set technology_group=? where tag=?", (m.group(1), new))
    # the generated files of the old code are stale now (the build does not purge them)
    old_file = con.execute("select country_file from tags where tag=?", (old,)).fetchone()
    for f in glob.glob(os.path.join(MOD, "history", "countries", f"{old} - *.txt")):
        os.remove(f)
    print(f"  {old} -> {new} ({vfiles[new]})")
    sweep(old, new)


#: files that name tags by hand (docs, the flag tools); generated and vendored files are rebuilt, never swept
SWEEP = ["AGENTS.md", "README.md", "PLANNING.md", "tools/FLAG_NOTES.md", "tools/coaflags.py"]


def vanilla_codes():
    codes = set()
    for f in glob.glob(os.path.join(os.environ.get("EU4_GAME") or "", "common", "country_tags", "*.txt")):
        codes.update(re.findall(r"(?m)^\s*([A-Z][A-Z0-9]{2})\s*=", open(f, encoding="cp1252", errors="replace").read()))
    return codes


def sweep(old, new):
    """Swap the code in the hand-kept docs and flag tools, then list every other tracked text file that still names it."""
    pat = re.compile(rf"\b{old}\b")
    for rel in SWEEP:
        path = os.path.join(MOD, rel)
        if os.path.exists(path):
            text = open(path, encoding="utf-8").read()
            new_text, n = pat.subn(new, text)
            if n:
                open(path, "w", encoding="utf-8", newline="").write(new_text)
                print(f"  swept {n} mention(s) of {old} in {rel}")
    skip = ("history", os.path.join("common", "countries"), "replace", "tags.db", "cache", "__pycache__", ".git")
    left = []
    for root, dirs, files in os.walk(MOD):
        dirs[:] = [d for d in dirs if d not in skip]
        for fn in files:
            if fn.endswith((".txt", ".yml", ".md", ".py", ".json")):
                path = os.path.join(root, fn)
                if pat.search(open(path, encoding="cp1252", errors="replace").read()):
                    left.append(os.path.relpath(path, MOD))
    if left:
        print(f"  {old} is still named in (hand-check, or rebuild if generated): " + ", ".join(sorted(left)))


def suggest(min_seq):
    """(OLD, NEW) for tags from `min_seq` on whose name is a free base-game tag's name."""
    from steps.vanilla_countries import load_vanilla_countries

    vfiles = load_vanilla_countries()
    names = {}
    for f in glob.glob(os.path.join(os.environ["EU4_GAME"], "localisation", "*_l_english.yml")):
        for m in re.finditer(r'(?m)^ ([A-Z][A-Z0-9]{2}):\d* "([^"]+)"', open(f, encoding="utf-8-sig", errors="replace").read()):
            names.setdefault(m.group(2).lower(), m.group(1))
    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    used = {r[0] for r in con.execute("select tag from tags")}
    out = []
    import tagloc

    for tag, title, rank in con.execute("select tag, ck3_title, rank from tags where seq >= ? order by seq", (min_seq,)):
        got = tagloc.title_names(title, rank, tag)
        v = names.get(got[0].lower()) if got else None
        if v and v in vfiles and v not in used:
            out.append((tag, v))
            used.add(v)
    return out


if __name__ == "__main__":
    from steps.vanilla_countries import load_vanilla_countries

    args = sys.argv[1:]
    if args[:1] == ["suggest"]:
        print(" ".join(f"{o} {n}" for o, n in suggest(int(args[1]))))
        sys.exit(0)
    if not args or len(args) % 2:
        sys.exit(__doc__)
    vfiles = {t: fn for t, (fn, _x) in load_vanilla_countries().items()}
    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    for old, new in zip(args[::2], args[1::2]):
        retag(con, old, new, vfiles)
    con.commit()
