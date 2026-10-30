#!/usr/bin/env python3
"""Full build: run every generation step in order and stop at the first failure.

The steps live in their own modules (`steps/`, plus the tools that lift CK3 data); this file only orders them.

    python3 tools/build.py            # regenerate the mod
    python3 tools/build.py --release  # the upload package instead (see release.py)
"""
from __future__ import annotations

import sys
import time

import cultures  # noqa: E402  (the cultures file must exist before tagdb reads it)

cultures.ensure()
import religions  # noqa: E402

religions.ensure()

from ck3 import step_ck3  # noqa: E402
from culturetitles import step_government_names  # noqa: E402
from rites import step_rites  # noqa: E402
from steps import provdata  # noqa: E402
from steps.countries import step_countries  # noqa: E402
from steps.custom import step_custom  # noqa: E402
from steps.diplomacy import step_diplomacy, step_wars  # noqa: E402
from steps.empire import step_hre  # noqa: E402
from steps.formations import step_formation_triggers  # noqa: E402
from steps.provinces import step_provinces  # noqa: E402
from steps.releasables import step_releasables  # noqa: E402
from steps.start import step_start  # noqa: E402
from steps.vanilla_countries import step_restore_colours, step_vanilla_countries  # noqa: E402
from steps.vanilla_scripts import step_events, step_filter_decisions  # noqa: E402
from tagdb import selfcheck  # noqa: E402
from tagloc import step_tagloc  # noqa: E402
from vanillapatch import step_vanilla_patches  # noqa: E402

PHASES = [
    ("probe the base game's province history", provdata.ensure),
    ("patch base-game files", step_vanilla_patches),
    ("check the Tag database", selfcheck),
    ("write the Christian rite schools", step_rites),
    ("lift tag names from CK3", step_tagloc),
    ("lift government titles from CK3", step_government_names),
    ("generate province files", step_provinces),
    ("generate country files", step_countries),
    ("generate the empire decision", step_hre),
    ("write starting vassals", step_diplomacy),
    ("write preset wars", step_wars),
    ("generate the Magyars", step_custom),
    ("rewrite vanilla realm colours", step_vanilla_countries),
    ("generate the restore-colours decision", step_restore_colours),
    ("write formation triggers", step_formation_triggers),
    ("write the releasables' events", step_releasables),
    ("filter vanilla events", step_events),
    ("filter vanilla decisions", step_filter_decisions),
    ("check CK3 rulers", step_ck3, []),
    ("check start-date ownership", step_start),
]


def run_phase(label, fn, *args):
    print(f"\n\033[1m==> {label}\033[0m", flush=True)
    try:
        return fn(*args) or 0
    except SystemExit as exc:
        return int(exc.code or 0)


def main() -> int:
    if "--release" in sys.argv:
        import release

        return release.main([a for a in sys.argv[1:] if a != "--release"])
    started = time.time()
    print(f"Charlemagne's Legacy - full build\n{'=' * 60}")
    for label, fn, *rest in PHASES:
        try:
            rc = run_phase(label, fn, *rest)
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
