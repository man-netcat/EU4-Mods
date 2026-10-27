#!/usr/bin/env python3
"""Package the mod for upload with none of the base games' material in it.

    python3 tools/build.py --release [--out DIR] [--zip]
    python3 tools/release.py [--out DIR] [--zip]          (the same)

The package holds the script and the mod's own files only: tools/ (the build, its
tag database and notes), descriptor.mod, and every hand-authored file (events,
disasters, decisions, localisation, ...). Everything the build lifts from EU4 or
CK3 is left out: province and country history, country files, the vanilla events
and decisions the build copies, the cultures, religions and country-name files,
the interface sprites, and every image under gfx/ (flags, icon strips, rite icons).
Whoever installs the package runs `python3 tools/build.py` once with their own
EU4 and CK3 installed, and the build writes all of that into the mod folder.

Which files are "lifted" is not a list kept here: the build runs in an empty folder
and whatever it writes is generated. An authored file that is byte-identical to a
base-game file is left out as well.
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import selfcontained  # noqa: E402
from paths import EU4_GAME  # noqa: E402

MOD = os.path.dirname(HERE)
NAME = os.path.basename(MOD)

INSTALL = """# {name} - install

This package contains the build script and the mod's own files. It contains no
Europa Universalis IV or Crusader Kings III material: the province history, country
files, names, cultures, religions and flags are lifted from your own copies of the
games by the build.

## Needs

* Europa Universalis IV {version} and Crusader Kings III, installed.
* Python 3.10+ with `pip install -r tools/requirements.txt`.

## Steps

1. Put this folder in `Documents/Paradox Interactive/Europa Universalis IV/mod/`.
2. Point the build at the games (the defaults are the author's Steam paths):

       export EU4_GAME="/path/to/Europa Universalis IV"
       export CK3_GAME="/path/to/Crusader Kings III/game"

3. From this folder run `python3 tools/build.py`. It writes the rest of the mod
   here (a minute or so), then run `python3 tools/validate.py` to check it.
4. Enable the mod in the launcher (the `.mod` file next to this folder points at it).

## Not included

Images under `gfx/` (flags, religion and rite icons) are not part of the package, so
new realms show no flag and the religion strips are the base game's until you
add your own art (`python3 tools/faiths.py icons` lifts CK3's faith icons into them
when both games are installed).
"""


def vanilla_same(rel, path):
    v = os.path.join(str(EU4_GAME), rel)
    if not os.path.isfile(v):
        return False
    a = open(path, "rb").read().replace(b"\r\n", b"\n")
    b = open(v, "rb").read().replace(b"\r\n", b"\n")
    return a == b


def mostly_vanilla(rel, path):
    """True when more than half of a file's lines (comments and blanks aside) are the
    base game's own (substantial) lines at the same path: an edited copy, not a file of ours."""
    v = os.path.join(str(EU4_GAME), rel)
    if not os.path.isfile(v):
        return False

    def lines(p):
        out = []
        for ln in open(p, "rb").read().decode("latin-1").splitlines():
            ln = ln.split("#", 1)[0].strip()
            if len(ln) >= 25:  # shorter lines are shape (`skill = 2`, `}`), not text
                out.append(ln)
        return out

    mine, theirs = lines(path), set(lines(v))
    return bool(mine) and sum(1 for ln in mine if ln in theirs) * 2 > len(mine)


def copies_of_game_files(root):
    """Package files that are byte-identical (line endings aside) to any text file of either
    game, wherever it sits: a last guard against shipping the games' own material."""
    import hashlib

    from paths import CK3_GAME

    def digest(p):
        return hashlib.sha1(open(p, "rb").read().replace(b"\r\n", b"\n")).hexdigest()

    exts = (".txt", ".yml", ".gfx", ".lua", ".gui", ".inc", ".csv", ".mod")
    theirs = set()
    for base in (str(EU4_GAME), str(CK3_GAME)):
        for dp, _dn, fns in os.walk(base):
            for fn in fns:
                if fn.endswith(exts):
                    p = os.path.join(dp, fn)
                    if os.path.getsize(p) >= 200:
                        theirs.add(digest(p))
    hits = []
    for dp, _dn, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            if fn.endswith(exts) and os.path.getsize(p) >= 200 and digest(p) in theirs:
                hits.append(os.path.relpath(p, root))
    return hits


def descriptor_text(src):
    """descriptor.mod for a package: no machine path, no flag replacement (the flags
    are not shipped)."""
    out = []
    for ln in open(src, encoding="utf-8").read().splitlines():
        if ln.startswith("path=") or ln.strip() == 'replace_path="gfx/flags"':
            continue
        out.append(ln)
    return "\n".join(out) + "\n"


def launcher_text(desc):
    return desc.rstrip("\n") + f'\npath="mod/{NAME}"\n'


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = os.path.join(os.path.dirname(MOD), "dist", NAME)
    if "--out" in argv:
        out = os.path.abspath(argv[argv.index("--out") + 1])
    scratch, built, rc = selfcontained.scratch_build()
    if rc:
        print("release: the build failed, nothing packaged", file=sys.stderr)
        return rc
    generated = set()
    for dp, dn, fns in os.walk(built):
        dn[:] = [d for d in dn if d not in ("tools", "__pycache__")]
        for fn in fns:
            rel = os.path.relpath(os.path.join(dp, fn), built)
            if rel != "descriptor.mod":  # copied in, not written by the build
                generated.add(rel)

    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    shutil.copytree(HERE, os.path.join(out, "tools"),
                    ignore=shutil.ignore_patterns("__pycache__", "cache"))
    kept, lifted, images, same, modified = 0, 0, 0, [], []
    for dp, dn, fns in os.walk(MOD):
        dn[:] = [d for d in dn if d not in ("tools", "__pycache__", ".git")]
        for fn in fns:
            src = os.path.join(dp, fn)
            rel = os.path.relpath(src, MOD)
            if rel == "descriptor.mod":
                continue
            if rel in generated:
                lifted += 1
            elif rel.startswith("gfx" + os.sep):
                images += 1
            elif vanilla_same(rel, src):
                same.append(rel)
            elif mostly_vanilla(rel, src):
                modified.append(rel)  # an edited copy of a base-game file: it must be lifted
            else:
                dst = os.path.join(out, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                kept += 1
    desc = descriptor_text(os.path.join(MOD, "descriptor.mod"))
    open(os.path.join(out, "descriptor.mod"), "w", encoding="utf-8", newline="\n").write(desc)
    open(os.path.join(os.path.dirname(out), NAME + ".mod"), "w", encoding="utf-8",
         newline="\n").write(launcher_text(desc))
    version = re.search(r'supported_version="([^"]+)"', desc)
    open(os.path.join(out, "INSTALL.md"), "w", encoding="utf-8", newline="\n").write(
        INSTALL.format(name=NAME, version=version.group(1) if version else "1.37"))
    shutil.rmtree(scratch, ignore_errors=True)

    if modified:
        print("release: edited copies of base-game files are not generated by the build "
              "(add them to tools/vanillapatch.py):", modified, file=sys.stderr)
        return 1
    dup = copies_of_game_files(out)
    if dup:
        print("release: files identical to base-game files in the package:", dup, file=sys.stderr)
        return 1
    # nothing the build writes may be in the package
    leaked = [r for r in generated if os.path.exists(os.path.join(out, r))]
    if leaked:
        print("release: generated files leaked into the package:", leaked[:10], file=sys.stderr)
        return 1
    print(f"release: {out}")
    print(f"  shipped   {kept} hand-authored files + tools/ + descriptor.mod + INSTALL.md")
    print(f"  left out  {lifted} lifted by the build, {images} images under gfx/"
          + (f", {len(same)} identical to base-game files: {same}" if same else ""))
    if "--zip" in argv:
        z = shutil.make_archive(out, "zip", os.path.dirname(out), NAME)
        print(f"  archive   {z}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
