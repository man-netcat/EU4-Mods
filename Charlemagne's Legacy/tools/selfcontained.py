#!/usr/bin/env python3
"""Build the mod from nothing but tools/ (script + tags.db) and say what is missing.

The rule: the repository ships the script and CK3-independent data; everything
that comes from CK3 or EU4 is lifted by tools/build.py. This copies tools/ and
descriptor.mod into an empty folder, runs build + validate there and exits
non-zero while any generated file still depends on a hand-kept file in the mod.

    python3 tools/selfcontained.py           # report only
    python3 tools/selfcontained.py --keep    # leave the scratch folder in place
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)


def overlay_authored(mod):
    """Copy every file of the real mod the build did not write (hand-authored text such
    as events and loc, plus the images only a local run can make) into the scratch mod,
    so the validator can see them. Returns the number copied."""
    n = 0
    for dp, dn, fns in os.walk(MOD):
        dn[:] = [d for d in dn if d not in ("tools", "__pycache__", ".git")]
        for fn in fns:
            src = os.path.join(dp, fn)
            dst = os.path.join(mod, os.path.relpath(src, MOD))
            if not os.path.exists(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                n += 1
    return n


def differing(mod):
    """Generated files (written by the scratch build) whose bytes differ from the repo's."""
    bad = []
    for dp, dn, fns in os.walk(mod):
        dn[:] = [d for d in dn if d not in ("tools", "__pycache__")]
        for fn in fns:
            built = os.path.join(dp, fn)
            real = os.path.join(MOD, os.path.relpath(built, mod))
            rel = os.path.relpath(built, mod)
            if rel.startswith("gfx" + os.sep):
                continue  # images: placeholders here, CK3's art only after a local `faiths.py icons`
            if os.path.exists(real) and open(built, "rb").read() != open(real, "rb").read():
                bad.append(os.path.relpath(built, mod))
    return bad


def main() -> int:
    keep = "--keep" in sys.argv
    scratch = tempfile.mkdtemp(prefix="cl_selfcontained_")
    mod = os.path.join(scratch, "mod")
    os.makedirs(mod)
    shutil.copytree(HERE, os.path.join(mod, "tools"),
                    ignore=shutil.ignore_patterns("__pycache__", "cache"))
    shutil.copy(os.path.join(MOD, "descriptor.mod"), mod)
    launcher = os.path.join(os.path.dirname(MOD), os.path.basename(MOD) + ".mod")
    if os.path.exists(launcher):  # the .mod file sits next to the folder; validate checks it
        shutil.copy(launcher, scratch)
    os.environ["EU4_MODS_DIR"] = scratch
    print(f"== build.py in an empty mod folder ({mod})", flush=True)
    r = subprocess.run([sys.executable, os.path.join("tools", "build.py")], cwd=mod)
    if r.returncode:
        print("FAILED: build.py needs files the script does not lift", file=sys.stderr)
        return r.returncode
    bad = differing(mod)
    n = overlay_authored(mod)
    print(f"== validate.py with {n} hand-authored files laid over the build", flush=True)
    r = subprocess.run([sys.executable, os.path.join("tools", "validate.py")], cwd=mod)
    rc = r.returncode
    if rc:
        print("FAILED: validate.py", file=sys.stderr)
    if bad:
        print(f"{len(bad)} generated files differ from the repository's:", file=sys.stderr)
        for b in bad[:40]:
            print("  " + b, file=sys.stderr)
        rc = rc or 1
    if not rc:
        print("SELF-CONTAINED: the mod rebuilds from tools/ alone")
    if keep:
        print(f"scratch kept at {scratch}")
    else:
        shutil.rmtree(scratch, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
