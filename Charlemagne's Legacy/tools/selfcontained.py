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


def main() -> int:
    keep = "--keep" in sys.argv
    scratch = tempfile.mkdtemp(prefix="cl_selfcontained_")
    mod = os.path.join(scratch, "mod")
    os.makedirs(mod)
    shutil.copytree(HERE, os.path.join(mod, "tools"),
                    ignore=shutil.ignore_patterns("__pycache__", "cache"))
    shutil.copy(os.path.join(MOD, "descriptor.mod"), mod)
    rc = 0
    for step in ("build.py", "validate.py"):
        print(f"== {step} in an empty mod folder ({mod})", flush=True)
        r = subprocess.run([sys.executable, os.path.join("tools", step)], cwd=mod)
        if r.returncode:
            print(f"FAILED: {step} needs files the script does not lift", file=sys.stderr)
            rc = r.returncode
            break
    else:
        print("SELF-CONTAINED: the mod rebuilds from tools/ alone")
    if keep:
        print(f"scratch kept at {scratch}")
    else:
        shutil.rmtree(scratch, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
