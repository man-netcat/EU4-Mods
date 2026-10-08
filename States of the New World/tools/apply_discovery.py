#!/usr/bin/env python3
"""Give every American province a discovery line.

Run AFTER gen_mod.py:
    python3 gen_mod.py && python3 apply_discovery.py && python3 verify_mod.py

The mod only controls the Americas, so every province file under OUT is
American.  This script makes high_american see every one of them at game
start, so both continents are mutually visible.

Pass 1 - mod-written files: insert "discovered_by = high_american" after the
"is_city = yes" line of every generated province file in OUT.

Pass 2 - restored vanilla provinces (design.RESTORED): copy the vanilla file
from the game into OUT and insert the discovery line BEFORE the first dated
history block (e.g. "1519.1.1 = { ... }"); if the file has no dated block,
append the line at the end.

Both passes are idempotent: files that already carry the discovery line are
skipped.  All I/O is byte-preserving (no encoding assumptions).
"""
import importlib.util
import os
import sys

import verify_common as vc

LINE = vc.DISC
ISCITY = b"is_city = yes\n"

OUT_PROV = f"{vc.OUT}/history/provinces"
if not os.path.isdir(OUT_PROV):
    print("OUT province dir missing. Run gen_mod.py first:", OUT_PROV)
    sys.exit(1)


def insert_into_mod_file(raw):
    """Return raw with LINE inserted after the is_city line."""
    assert ISCITY in raw, "mod-written province file has no is_city = yes"
    return raw.replace(ISCITY, ISCITY + LINE + b"\n", 1)


def load_design():
    spec = importlib.util.spec_from_file_location("design", f"{vc.BASE}/design.py")
    design = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(design)
    return design


def main():
    # pass 1: mod-written files (already in OUT before this script runs)
    mod_done = mod_skip = 0
    for f in sorted(os.listdir(OUT_PROV)):
        path = f"{OUT_PROV}/{f}"
        raw = open(path, "rb").read()
        if LINE in raw:
            mod_skip += 1
            continue
        open(path, "wb").write(insert_into_mod_file(raw))
        mod_done += 1

    # pass 2: restored vanilla provinces
    design = load_design()
    restored = getattr(design, "RESTORED", None) or {}
    rest_ids = sorted({str(p) for provs in restored.values() for p in provs})
    rest_done = rest_skip = 0
    for pid in rest_ids:
        files = vc.vanilla_prov_files(pid)
        assert files, f"no vanilla province file for restored id {pid}"
        fname = files[0]
        vraw = open(f"{vc.GAME_HIST_PROV}/{fname}", "rb").read()
        dst = f"{OUT_PROV}/{fname}"
        if os.path.exists(dst):
            if LINE in open(dst, "rb").read():
                rest_skip += 1
                continue
            raise SystemExit(f"{fname} exists in OUT without discovery line")
        if LINE in vraw:
            # vanilla file already names high_american (should not happen)
            open(dst, "wb").write(vraw)
            rest_skip += 1
            continue
        open(dst, "wb").write(vc.discovery_copy(vraw))
        rest_done += 1

    print(f"discovery pass 1: {mod_done} patched, {mod_skip} already had line")
    print(f"discovery pass 2: {rest_done} restored copies written, {rest_skip} skipped")


if __name__ == "__main__":
    main()