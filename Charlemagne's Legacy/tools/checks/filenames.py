#!/usr/bin/env python3
"""Generated file names match the base game's shapes."""

import os
import re
from checks.report import note
from checks.context import COUNTRY_OUT, PDIR, _REALMS


def generated_file_names_match_base_game_shapes() -> None:
    """Generated file names match base-game shapes."""
    print("\n== generated file names match base-game shapes ==")
    from steps.provdata import vanilla_prov_file

    # Vanilla replaces whole directories with nothing (replace_path),
    # but per-file it merges: history files that vanish from our tree
    # reappear in the vanilla copy, and same-content files union. A name
    # that drifts from the base game's exact filename therefore leaks
    # vanilla content back in - the check below has bitten twice (2018's
    # renaming races left stale display names behind, and a country file
    # registered under a hand-picked name for a vanilla-reused tag once
    # coexisted with the vanilla copy).
    prov_bad = []
    for fn in sorted(os.listdir(PDIR)):
        m = re.match(r"^(\d+)", fn)
        if not m:
            prov_bad.append(f"{fn}: not pid-prefixed")
            continue
        van = vanilla_prov_file(int(m.group(1)))
        if van is None:
            prov_bad.append(f"{fn}: no vanilla province with this pid")
        elif os.path.basename(van) != fn:
            prov_bad.append(f"{fn}: vanilla's file is '{os.path.basename(van)}'")
    note(
        not prov_bad,
        f"province files ride vanilla's names ({len(prov_bad)} off)",
    )
    for b in prov_bad[:8]:
        print("        " + b)

    # Generated country files follow eu4's rule: keep vanilla's exact
    # filename when the tag is a vanilla reuse (else the vanilla copy's
    # OTL history merges back), else '<TAG> - <country_file>.txt'. HLR
    # has no db row - it is formed in-game and its file is neutralized.
    from steps.countries import hist_name

    want = {t.tag: hist_name(t) for t in _REALMS}
    want["HLR"] = "HLR - Holy Roman Empire.txt"
    cdir = COUNTRY_OUT
    cfiles = [fn for fn in os.listdir(cdir) if fn.endswith(".txt")]
    cty_bad = []
    for fn in cfiles:
        tag = fn.split(" - ", 1)[0]
        if tag not in want:
            cty_bad.append(f"{fn}: {tag} is no tag here")
        elif fn != want[tag]:
            cty_bad.append(f"{fn}: should be '{want[tag]}'")
    note(
        not cty_bad,
        f"country files follow eu4's naming ({len(cty_bad)} off)",
    )
    for b in cty_bad[:8]:
        print("        " + b)
    missing = [want[t] for t in sorted(want) if want[t] not in cfiles]
    note(
        not missing,
        f"every tag has its country file ({len(missing)} missing)",
    )
    for b in missing[:8]:
        print("        " + b)


def run() -> None:
    generated_file_names_match_base_game_shapes()
