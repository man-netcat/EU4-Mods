#!/usr/bin/env python3

from __future__ import annotations

import sys, time

from tagdb import *  # noqa: F401,F403
from eu4 import *  # noqa: F401,F403
from ck3 import *  # noqa: F401,F403


def main() -> int:
    started = time.time()
    print(f"The Karolingians - full build\n{'=' * 60}")

    phases = [
        ("check the Tag database", selfcheck),
        ("generate province files", step_provinces, []),
        ("generate country files", step_countries),
        ("generate the empire decision", step_hre),
        ("generate the Magyars", step_custom),
        ("write name localisation", step_names),
        ("check CK3 rulers", step_ck3, []),
        ("check start-date ownership", step_start),
    ]

    def step(label, fn, *args):
        print(f"\n\033[1m==> {label}\033[0m", flush=True)
        try:
            return fn(*args) or 0
        except SystemExit as exc:
            return int(exc.code or 0)

    for phase in phases:
        label, fn, *rest = phase
        try:
            rc = step(label, fn, *rest)
        except Exception:
            import traceback

            traceback.print_exc()
            print(f"\n\033[31mBUILD FAILED\033[0m with an exception in {label}")
            return 1
        if rc:
            print(f"\n\033[31mBUILD FAILED\033[0m at {label}")
            return 1

    print(f"\n{'=' * 60}\n\033[32mBUILD OK\033[0m in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
