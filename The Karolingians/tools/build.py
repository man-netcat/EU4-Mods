#!/usr/bin/env python3
"""Build the entire mod. One command, from the base game, CK3 and the spec.

    python3 tools/build.py

Everything the mod ships is generated. This runs the whole chain in the only
order that works and then checks the result, so "the tooling is out of date" is
not a state the mod can be in.

Why one script
--------------
The steps used to be run by hand, in an order that had to be remembered:

    probe            vanilla province history -> cache/provdata.json
    gen_provinces    the allocation -> history/provinces/*.txt
    gen_countries    CK3 rulers    -> history/countries/*.txt
    gen_hre_decision the five-kingdom empire -> decisions/
    ck3ruler --fix    resync ruler name/dynasty from CK3
    check_start       replay province history to 1444.11.11
    validate          everything else

Two of those orders silently broke things. Running gen_countries before
ck3ruler used to revert all fifteen CK3-sourced rulers to their hand-written
pre-lift names, because the generator had its own stale copies of those strings.
Running gen_provinces after ck3ruler was fine but nobody did it, so the country
files and the province files drifted apart. Order is not a convention here, it
is the correctness argument.

Step order, and why
-------------------
1. probe      Only when cache/provdata.json is missing or older than the vanilla
              install. Everything downstream reads it.
2. provinces  Writes history/provinces. Must precede the checks, which read the
              files it writes rather than the allocation in memory.
3. countries  Writes history/countries, asking ck3ruler for every CK3-sourced
              ruler's name and dynasty instead of carrying its own copy.
4. hre        Writes decisions/KarolingianHRE.txt from the finished allocation,
              so the empire requirement cannot disagree with the partition.
5. ck3ruler   A verification pass, not a generator: countries already took their
              names from here. Its --fix is still available for a targeted
              repair, but a clean build must not need it.
6. checks     check_start replays dated history to the start date; validate
              asserts the rest. A build that does not pass both has not built.

Exit status is non-zero if any step fails, so this is usable as a pre-commit hook.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
PROVDATA = CACHE / "provdata.json"
VANILLA_HISTORY = Path(
    "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV/history")


def vanilla_is_newer() -> bool:
    """True if the vanilla install looks newer than our snapshot of it."""
    if not PROVDATA.exists():
        return True
    try:
        return max(p.stat().st_mtime for p in VANILLA_HISTORY.rglob("*.txt")) > \
            PROVDATA.stat().st_mtime
    except OSError:
        return False


def run(label: str, args: list, optional: bool = False) -> bool:
    print(f"\n\033[1m==> {label}\033[0m\n    {' '.join(args)}", flush=True)
    rc = subprocess.call([sys.executable] + args, cwd=str(HERE.parent))
    if rc == 0:
        return True
    if optional:
        print(f"    (skipped: {label} is optional and not available here)")
        return True
    print(f"\n\033[31mBUILD FAILED\033[0m at {label} (exit {rc})")
    return False


def main() -> int:
    started = time.time()
    print(f"The Karolingians - full build\n{'=' * 60}")

    if vanilla_is_newer():
        if not run("probe vanilla province history", ["tools/probe.py"]):
            return 1
    else:
        print("== probe: cache is current, skipping")

    steps = [
        ("generate province files", ["tools/gen_provinces.py"], False),
        ("generate country files", ["tools/gen_countries.py"], False),
        ("generate the empire decision", ["tools/gen_hre_decision.py"], False),
        ("check CK3 rulers", ["tools/ck3ruler.py"], False),
        ("check start-date ownership", ["tools/check_start.py"], False),
        ("validate", ["tools/validate.py"], False),
    ]
    for label, args, optional in steps:
        if not run(label, args, optional):
            return 1

    print(f"\n{'=' * 60}\n\033[32mBUILD OK\033[0m in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
